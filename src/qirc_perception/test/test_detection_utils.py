"""Unit tests for qirc_perception.detection_utils (no camera or model needed)."""

import math

import numpy as np
import pytest
from qirc_perception.detection_utils import (
    box_depth, deproject, depth_to_metres, image_to_numpy, make_detection, OBJECT,
    PERSON, to_qirc_label)
from sensor_msgs.msg import Image
from std_msgs.msg import Header

# A 640x480 camera with the principal point at the image centre.
K = [600.0, 0.0, 320.0, 0.0, 600.0, 240.0, 0.0, 0.0, 1.0]


def _image(array, encoding, step=None):
    msg = Image()
    msg.height, msg.width = array.shape[:2]
    msg.encoding = encoding
    msg.is_bigendian = False
    row = array.reshape(msg.height, -1).view(np.uint8)
    if step is not None:  # add padding at the end of each row
        row = np.hstack([row, np.zeros((msg.height, step - row.shape[1]), np.uint8)])
    msg.step = row.shape[1]
    msg.data = row.tobytes()
    return msg


def test_labels():
    assert to_qirc_label('person') == PERSON
    assert to_qirc_label('Person ') == PERSON
    for name in ('chair', 'dog', 'bottle', 'tvmonitor'):
        assert to_qirc_label(name) == OBJECT


def test_rgb8_becomes_bgr():
    rgb = np.zeros((2, 3, 3), np.uint8)
    rgb[..., 0] = 255  # pure red
    bgr = image_to_numpy(_image(rgb, 'rgb8'))
    assert bgr.shape == (2, 3, 3)
    assert (bgr[..., 2] == 255).all() and (bgr[..., 0] == 0).all()


def test_bgr8_unchanged():
    bgr = np.random.default_rng(0).integers(0, 255, (4, 5, 3), dtype=np.uint8)
    assert np.array_equal(image_to_numpy(_image(bgr, 'bgr8')), bgr)


def test_depth_16uc1_with_row_padding():
    depth = np.arange(12, dtype=np.uint16).reshape(3, 4) * 100
    out = image_to_numpy(_image(depth, '16UC1', step=12))  # 8 bytes of data + 4 padding
    assert out.dtype == np.uint16
    assert np.array_equal(out, depth)


def test_unsupported_encoding():
    with pytest.raises(ValueError):
        image_to_numpy(_image(np.zeros((2, 2), np.uint8), 'mono8'))


def test_depth_to_metres():
    mm = np.array([[0, 1000], [2500, 65535]], np.uint16)
    m = depth_to_metres(mm, '16UC1')
    assert math.isnan(m[0, 0])
    assert m[0, 1] == pytest.approx(1.0) and m[1, 0] == pytest.approx(2.5)

    f = np.array([[0.0, np.inf], [1.5, -1.0]], np.float32)
    m = depth_to_metres(f, '32FC1')
    assert np.isnan(m[0, 0]) and np.isnan(m[0, 1]) and np.isnan(m[1, 1])
    assert m[1, 0] == pytest.approx(1.5)


def test_box_depth_ignores_background_and_holes():
    depth = np.full((480, 640), 4.0, np.float32)  # background wall at 4 m
    depth[100:300, 200:300] = 1.5                 # object at 1.5 m
    depth[190:210, 240:260] = np.nan              # hole in the depth image
    # Box slightly larger than the object, so its edges include background.
    assert box_depth(depth, (190, 90, 310, 310)) == pytest.approx(1.5)


def test_box_depth_none_without_readings():
    depth = np.full((480, 640), np.nan, np.float32)
    assert box_depth(depth, (100, 100, 200, 200)) is None


def test_box_depth_box_at_image_edge():
    depth = np.full((480, 640), 2.0, np.float32)
    assert box_depth(depth, (-20, -20, 10, 10)) == pytest.approx(2.0)
    assert box_depth(depth, (630, 470, 700, 500)) == pytest.approx(2.0)


def test_deproject():
    assert deproject(320, 240, 2.0, K) == pytest.approx((0.0, 0.0, 2.0))
    # 300 px right of centre at 2 m with fx = 600: 1 m right.
    assert deproject(620, 240, 2.0, K) == pytest.approx((1.0, 0.0, 2.0))
    # Optical frame: y is down, so above the centre is negative y.
    assert deproject(320, 0, 3.0, K) == pytest.approx((0.0, -1.2, 3.0))


def test_make_detection():
    header = Header(frame_id='front_camera_color_optical_frame')
    # A person 1.8 m tall standing 3 m away, centred: 360 px tall at fy = 600.
    detection = make_detection(header, PERSON, 0.9, (290, 60, 350, 420), 3.0, K)
    assert detection.header.frame_id == 'front_camera_color_optical_frame'
    assert detection.bbox.center.position.z == pytest.approx(3.0)
    assert detection.bbox.center.position.x == pytest.approx(0.0)
    assert detection.bbox.size.y == pytest.approx(1.8)
    assert detection.bbox.size.x == pytest.approx(0.3)
    (result,) = detection.results
    assert result.hypothesis.class_id == PERSON
    assert result.hypothesis.score == pytest.approx(0.9)
    assert result.pose.pose.position.z == pytest.approx(3.0)


# ----- Rear camera boxes and debug images --------------------------------------

def _oak_detection(center_px, size_px, position):
    """Build an OAK detection as the driver sends it: pixel bbox, 3D position in the pose."""
    from vision_msgs.msg import Detection3D, ObjectHypothesisWithPose
    detection = Detection3D()
    detection.bbox.center.position.x, detection.bbox.center.position.y = center_px
    detection.bbox.size.x, detection.bbox.size.y = size_px
    detection.bbox.size.z = 0.01
    result = ObjectHypothesisWithPose()
    result.hypothesis.class_id = PERSON
    result.hypothesis.score = 0.9
    result.pose.pose.position.x, result.pose.pose.position.y, result.pose.pose.position.z = (
        position)
    detection.results.append(result)
    return detection


def test_pixel_box():
    from qirc_perception.detection_utils import pixel_box
    detection = _oak_detection((161.0, 177.0), (278.0, 246.0), (-0.44, 0.17, 0.92))
    assert pixel_box(detection) == pytest.approx((22.0, 54.0, 300.0, 300.0))


def test_bbox_to_metres_uses_the_3d_position_and_camera_matrix():
    from qirc_perception.detection_utils import bbox_to_metres
    # 300 x 300 passthrough image with fx = fy = 200 px.
    k = [200.0, 0.0, 150.0, 0.0, 200.0, 150.0, 0.0, 0.0, 1.0]
    detection = _oak_detection((150.0, 150.0), (100.0, 50.0), (0.1, -0.2, 2.0))
    bbox_to_metres(detection, k)
    center = detection.bbox.center.position
    assert (center.x, center.y, center.z) == pytest.approx((0.1, -0.2, 2.0))
    assert detection.bbox.center.orientation.w == 1.0
    # 100 px wide at 2 m with fx = 200 px is 1 m; 50 px high is 0.5 m.
    assert detection.bbox.size.x == pytest.approx(1.0)
    assert detection.bbox.size.y == pytest.approx(0.5)
    assert detection.bbox.size.z == 0.0


def test_bbox_to_metres_without_camera_matrix_has_no_size():
    from qirc_perception.detection_utils import bbox_to_metres
    detection = _oak_detection((161.0, 177.0), (278.0, 246.0), (-0.44, 0.17, 0.92))
    bbox_to_metres(detection, None)
    assert detection.bbox.center.position.z == pytest.approx(0.92)
    assert (detection.bbox.size.x, detection.bbox.size.y, detection.bbox.size.z) == (0, 0, 0)


def test_numpy_to_image_round_trip():
    from qirc_perception.detection_utils import numpy_to_image
    bgr = np.random.default_rng(0).integers(0, 255, (4, 5, 3), dtype=np.uint8)
    msg = numpy_to_image(bgr, Header(frame_id='cam'))
    assert (msg.encoding, msg.width, msg.height, msg.step) == ('bgr8', 5, 4, 15)
    assert msg.header.frame_id == 'cam'
    assert np.array_equal(image_to_numpy(msg), bgr)


def test_draw_detections_draws_on_a_copy():
    from qirc_perception.detection_utils import draw_detections
    image = np.zeros((240, 320, 3), np.uint8)
    out = draw_detections(image, [
        (20, 30, 120, 200, PERSON, 0.9, 1.5),
        (150, 40, 300, 100, OBJECT, 0.6, None),
    ])
    assert out.shape == image.shape
    assert not image.any()                      # input unchanged
    assert out[100, 20].any()                   # left edge of the first box
    assert out[70, 150].any()                   # left edge of the second box
    assert not out[150, 70].any()               # inside the first box: untouched
    assert np.array_equal(draw_detections(image, []), image)
