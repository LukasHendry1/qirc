"""
Detect people and objects with YOLO on the front RealSense D435i.

Runs an Ultralytics YOLO model on each colour image, takes each detection's
distance from the aligned depth image, and publishes 3D detections.

Subscribes:
    /front_camera/color/image_raw                   sensor_msgs/Image
    /front_camera/aligned_depth_to_color/image_raw  sensor_msgs/Image
    /front_camera/color/camera_info                 sensor_msgs/CameraInfo

Publishes:
    /detections   vision_msgs/Detection3DArray, in the colour camera's optical
                  frame. Labels: 'person' or 'object'.
    /front_detection/image   sensor_msgs/Image (bgr8), for debugging: the colour
                  image with every YOLO box, its label, score and distance
                  (grey: dropped for lack of depth or beyond max_depth). Only
                  drawn while something subscribes to it.

Parameters (config/front_detection.yaml):
    model                 YOLO weights; a model name (e.g. yolo11n.pt) is
                          downloaded on first use to the path given
    confidence_threshold  drop detections below this score (0-1)
    image_size            inference size in pixels
    device                '' = GPU if available, else CPU; or 'cpu', 'cuda:0'
    max_depth             drop detections further than this (m)

Needs Ultralytics: pip install ultralytics "numpy<2" (see the package README).
"""

import os

import message_filters
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image
from vision_msgs.msg import Detection3DArray

from qirc_perception.detection_utils import (
    box_depth, depth_to_metres, draw_detections, image_to_numpy, make_detection,
    numpy_to_image, to_qirc_label)


class FrontDetectionNode(Node):
    """YOLO detection on the front camera, published as 3D detections."""

    def __init__(self):
        super().__init__('front_detection')
        self.declare_parameter('model', '~/.cache/qirc/yolo11n.pt')
        self.declare_parameter('confidence_threshold', 0.5)
        self.declare_parameter('image_size', 640)
        self.declare_parameter('device', '')
        self.declare_parameter('max_depth', 6.0)

        self.model = self._load_model(self.get_parameter('model').value)
        self.camera_matrix = None

        self.detection_pub = self.create_publisher(Detection3DArray, 'detections', 10)
        self.image_pub = self.create_publisher(Image, '~/image', qos_profile_sensor_data)
        self.create_subscription(
            CameraInfo, 'front_camera/color/camera_info', self._camera_info_callback,
            qos_profile_sensor_data)

        # Pair each colour image with the depth image taken at the same time.
        color_sub = message_filters.Subscriber(
            self, Image, 'front_camera/color/image_raw', qos_profile=qos_profile_sensor_data)
        depth_sub = message_filters.Subscriber(
            self, Image, 'front_camera/aligned_depth_to_color/image_raw',
            qos_profile=qos_profile_sensor_data)
        self.sync = message_filters.ApproximateTimeSynchronizer(
            [color_sub, depth_sub], queue_size=5, slop=0.05)
        self.sync.registerCallback(self._images_callback)

        self.get_logger().info('front_detection started')

    def _load_model(self, model_path):
        try:
            from ultralytics import YOLO
        except ImportError as error:
            raise RuntimeError(
                'Ultralytics is not installed. Run: pip install ultralytics "numpy<2" '
                '(see src/qirc_perception/README.md)') from error

        path = os.path.expanduser(model_path)
        if os.path.dirname(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
        self.get_logger().info(f'loading YOLO model {path}')
        return YOLO(path)

    def _camera_info_callback(self, msg):
        self.camera_matrix = list(msg.k)

    def _images_callback(self, color_msg, depth_msg):
        if self.camera_matrix is None:
            self.get_logger().warn(
                'waiting for front_camera/color/camera_info', throttle_duration_sec=5.0)
            return

        color = image_to_numpy(color_msg)
        depth_m = depth_to_metres(image_to_numpy(depth_msg), depth_msg.encoding)
        if depth_m.shape != color.shape[:2]:
            self.get_logger().error(
                f'depth {depth_m.shape} and colour {color.shape[:2]} sizes differ; '
                'is align_depth enabled?', throttle_duration_sec=5.0)
            return

        result = self.model.predict(
            color,
            conf=self.get_parameter('confidence_threshold').value,
            imgsz=self.get_parameter('image_size').value,
            device=self.get_parameter('device').value or None,
            verbose=False,
        )[0]

        max_depth = self.get_parameter('max_depth').value
        detections = Detection3DArray()
        detections.header = color_msg.header
        drawn = []
        for box, score, class_index in zip(
                result.boxes.xyxy.tolist(), result.boxes.conf.tolist(),
                result.boxes.cls.tolist()):
            label = to_qirc_label(result.names[int(class_index)])
            depth = box_depth(depth_m, box)
            if depth is None or depth > max_depth:
                drawn.append((*box, label, score, None))
                continue
            drawn.append((*box, label, score, depth))
            detections.detections.append(make_detection(
                color_msg.header, label, score, box, depth, self.camera_matrix))

        self.detection_pub.publish(detections)
        if self.image_pub.get_subscription_count() > 0:
            self.image_pub.publish(
                numpy_to_image(draw_detections(color, drawn), color_msg.header))


def main(args=None):
    rclpy.init(args=args)
    node = FrontDetectionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
