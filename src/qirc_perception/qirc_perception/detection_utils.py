"""
Helpers shared by the detection nodes.

Pure functions (numpy, OpenCV and ROS messages only, no ML libraries), so
they can be unit-tested without a camera or a model.

Every detection on /detections has its bounding box in metres, in the camera's
optical frame: centred on the 3D position, x and y size the box's width and
height at that distance, z size 0 (unknown).
"""

import json
import math

import cv2
from geometry_msgs.msg import Point
import numpy as np
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection3D, ObjectHypothesisWithPose

# Class labels on /detections (docs/architecture/messages.md).
PERSON = 'person'
OBJECT = 'object'


def to_qirc_label(class_name):
    """Map a model's class name to a /detections label: 'person' or 'object'."""
    return PERSON if class_name.strip().lower() == PERSON else OBJECT


def image_to_numpy(msg):
    """
    Convert a sensor_msgs/Image to a numpy array, without cv_bridge.

    Colour images (rgb8, bgr8) come back as H x W x 3 uint8 in BGR order, which
    is what OpenCV and Ultralytics expect. Depth images come back as H x W:
    16UC1 as uint16 (millimetres), 32FC1 as float32 (metres).
    """
    encodings = {
        'rgb8': (np.uint8, 3),
        'bgr8': (np.uint8, 3),
        '16UC1': (np.uint16, 1),
        'mono16': (np.uint16, 1),
        '32FC1': (np.float32, 1),
    }
    if msg.encoding not in encodings:
        raise ValueError(f'unsupported image encoding: {msg.encoding}')
    dtype, channels = encodings[msg.encoding]
    dtype = np.dtype(dtype).newbyteorder('>' if msg.is_bigendian else '<')

    # Rows can be padded: msg.step is the row length in bytes.
    row_items = msg.step // dtype.itemsize
    data = np.frombuffer(bytes(msg.data), dtype=dtype).reshape(msg.height, row_items)
    image = data[:, :msg.width * channels]
    if channels == 3:
        image = image.reshape(msg.height, msg.width, 3)
        if msg.encoding == 'rgb8':
            image = image[:, :, ::-1]
    return np.ascontiguousarray(image.astype(dtype.newbyteorder('=')))


def numpy_to_image(image, header):
    """Convert an H x W x 3 uint8 BGR array to a bgr8 sensor_msgs/Image."""
    msg = Image()
    msg.header = header
    msg.height, msg.width = image.shape[:2]
    msg.encoding = 'bgr8'
    msg.is_bigendian = False
    msg.step = msg.width * 3
    msg.data = np.ascontiguousarray(image, dtype=np.uint8).tobytes()
    return msg


def depth_to_metres(depth, encoding):
    """Convert a depth image to float32 metres; missing readings become NaN."""
    if encoding in ('16UC1', 'mono16'):
        metres = depth.astype(np.float32) / 1000.0
        metres[depth == 0] = np.nan
        return metres
    if encoding == '32FC1':
        metres = depth.astype(np.float32)
        metres[~np.isfinite(metres) | (metres <= 0)] = np.nan
        return metres
    raise ValueError(f'unsupported depth encoding: {encoding}')


def box_depth(depth_m, box, core_fraction=0.5, min_valid_fraction=0.1):
    """
    Return the distance (m) to the object in a bounding box, or None.

    Takes the median depth of the central core_fraction of the box, so the
    background around the object's edges and missing readings (NaN) don't
    affect it. Returns None if fewer than min_valid_fraction of the core pixels
    have a depth reading.

    box is (x1, y1, x2, y2) in pixels.
    """
    height, width = depth_m.shape
    x1, y1, x2, y2 = box
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    half_w, half_h = (x2 - x1) * core_fraction / 2, (y2 - y1) * core_fraction / 2
    left = int(np.clip(math.floor(cx - half_w), 0, width - 1))
    right = int(np.clip(math.ceil(cx + half_w), left + 1, width))
    top = int(np.clip(math.floor(cy - half_h), 0, height - 1))
    bottom = int(np.clip(math.ceil(cy + half_h), top + 1, height))

    core = depth_m[top:bottom, left:right]
    valid = core[np.isfinite(core)]
    if valid.size == 0 or valid.size < min_valid_fraction * core.size:
        return None
    return float(np.median(valid))


def deproject(u, v, depth, k):
    """
    Return the 3D point (x, y, z) in metres for pixel (u, v) at a given depth.

    Uses the pinhole model with the camera matrix k (sensor_msgs/CameraInfo.k,
    9 values, row-major). The point is in the camera's optical frame: x right,
    y down, z forward. Lens distortion is ignored (it is small on the D435i
    colour camera).
    """
    fx, cx, fy, cy = k[0], k[2], k[4], k[5]
    return ((u - cx) * depth / fx, (v - cy) * depth / fy, depth)


def make_detection(header, label, score, box, depth, k):
    """
    Build a vision_msgs/Detection3D for a 2D box with a known depth.

    The bounding box is centred on the deprojected box centre. Its x and y
    size are the box width and height at that depth; its z size (along the
    optical axis) is unknown and left at 0.
    """
    x1, y1, x2, y2 = box
    x, y, z = deproject((x1 + x2) / 2, (y1 + y2) / 2, depth, k)
    fx, fy = k[0], k[4]

    detection = Detection3D()
    detection.header = header
    detection.bbox.center.position = Point(x=x, y=y, z=z)
    detection.bbox.center.orientation.w = 1.0
    detection.bbox.size.x = (x2 - x1) * depth / fx
    detection.bbox.size.y = (y2 - y1) * depth / fy
    detection.bbox.size.z = 0.0

    hypothesis = ObjectHypothesisWithPose()
    hypothesis.hypothesis.class_id = label
    hypothesis.hypothesis.score = float(score)
    hypothesis.pose.pose.position = Point(x=x, y=y, z=z)
    hypothesis.pose.pose.orientation.w = 1.0
    detection.results.append(hypothesis)
    return detection


def load_label_names(nn_config_text):
    """
    Return the class names from a depthai neural network config (JSON text).

    The names are in mappings.labels, indexed by the model's class number.
    """
    return list(json.loads(nn_config_text)['mappings']['labels'])


def relabel_detection(detection, label_names, min_confidence):
    """
    Relabel a detection from the OAK camera for /detections, or return None.

    The depthai driver sets class_id to the model's class number as a string
    (e.g. '15' is person in the VOC classes). This keeps the most confident
    result, maps its class to 'person' or 'object', and drops the detection if
    it is below min_confidence or is the 'background' class. The position and
    bounding box are kept unchanged.
    """
    if not detection.results:
        return None
    best = max(detection.results, key=lambda r: r.hypothesis.score)
    if best.hypothesis.score < min_confidence:
        return None

    class_id = best.hypothesis.class_id.strip()
    if class_id.isdigit():
        index = int(class_id)
        if index >= len(label_names):
            return None
        class_name = label_names[index]
    else:
        class_name = class_id  # already a name
    if class_name.lower() == 'background':
        return None

    best.hypothesis.class_id = to_qirc_label(class_name)
    detection.results = [best]
    return detection


def pixel_box(detection):
    """Return an OAK detection's bounding box as (x1, y1, x2, y2) pixels."""
    center, size = detection.bbox.center.position, detection.bbox.size
    return (center.x - size.x / 2, center.y - size.y / 2,
            center.x + size.x / 2, center.y + size.y / 2)


def bbox_to_metres(detection, k=None):
    """
    Convert an OAK detection's bounding box from pixels to metres, in place.

    The depthai driver gives the 3D position in the result's pose, but the
    bounding box in pixels of the image the network ran on. This centres the
    box on the 3D position and scales its width and height to metres at that
    distance, using that image's camera matrix k (CameraInfo.k), like
    make_detection does for the front camera. Without k the size is unknown
    and set to 0. Returns the detection.
    """
    position = detection.results[0].pose.pose.position
    width_px, height_px = detection.bbox.size.x, detection.bbox.size.y

    detection.bbox.center.position = Point(x=position.x, y=position.y, z=position.z)
    detection.bbox.center.orientation.x = 0.0
    detection.bbox.center.orientation.y = 0.0
    detection.bbox.center.orientation.z = 0.0
    detection.bbox.center.orientation.w = 1.0
    if k is None or k[0] <= 0 or k[4] <= 0:
        detection.bbox.size.x = detection.bbox.size.y = 0.0
    else:
        detection.bbox.size.x = width_px * position.z / k[0]
        detection.bbox.size.y = height_px * position.z / k[4]
    detection.bbox.size.z = 0.0
    return detection


# Debug image colours (BGR).
_PERSON_COLOUR = (60, 200, 60)
_OBJECT_COLOUR = (255, 170, 40)
_NO_DEPTH_COLOUR = (150, 150, 150)


def draw_detections(image, boxes):
    """
    Return a copy of a BGR image with detection boxes and labels drawn on it.

    boxes is an iterable of (x1, y1, x2, y2, label, score, distance): pixels,
    the /detections label, the score (0-1) and the distance in metres, or None
    if the detection was dropped for lack of depth (drawn in grey).
    """
    out = np.ascontiguousarray(image).copy()
    height, width = out.shape[:2]
    thickness = max(1, round(min(height, width) / 240))
    scale = max(0.35, min(height, width) / 900)
    for x1, y1, x2, y2, label, score, distance in boxes:
        if distance is None:
            colour, text = _NO_DEPTH_COLOUR, f'{label} {score:.2f} no depth'
        else:
            colour = _PERSON_COLOUR if label == PERSON else _OBJECT_COLOUR
            text = f'{label} {score:.2f} {distance:.2f} m'
        top_left = (int(round(x1)), int(round(y1)))
        cv2.rectangle(out, top_left, (int(round(x2)), int(round(y2))), colour, thickness)

        (text_w, text_h), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
        label_bottom = max(top_left[1], text_h + baseline + 2)
        cv2.rectangle(out, (top_left[0], label_bottom - text_h - baseline - 2),
                      (top_left[0] + text_w + 4, label_bottom), colour, -1)
        cv2.putText(out, text, (top_left[0] + 2, label_bottom - baseline - 1),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 1, cv2.LINE_AA)
    return out
