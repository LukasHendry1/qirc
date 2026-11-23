"""
Republish the rear OAK-D Lite's on-camera detections on /detections.

The OAK runs its neural network on the camera itself and the depthai driver
publishes the results with 3D positions. This node relabels them to the
shared /detections classes and filters them; it doesn't run a model.

The driver gives each bounding box in pixels of the image the network ran on
(the "passthrough" image, 300 x 300 for MobileNet-SSD). This node converts it
to metres like the front camera's: centred on the 3D position, sized with the
passthrough image's camera matrix. Until that arrives the size is 0.

Subscribes:
    /rear_camera/nn/spatial_detections         vision_msgs/Detection3DArray
    /rear_camera/nn/passthrough/camera_info    sensor_msgs/CameraInfo
    /rear_camera/nn/passthrough/image_raw      sensor_msgs/Image (for the
                                               debug image only)

Publishes:
    /detections   vision_msgs/Detection3DArray, in the rear camera's frame
                  (unchanged from the driver). Labels: 'person' or 'object'.
    /rear_detection/image   sensor_msgs/Image (bgr8), for debugging: the
                  passthrough image with each detection's box, label, score
                  and distance. Only drawn while something subscribes to it.

The passthrough topics need i_enable_passthrough in rear_camera.yaml.

Parameters (config/rear_detection.yaml):
    nn_config       the driver's model config, same value as i_nn_config_path
                    in rear_camera.yaml (e.g. depthai_ros_driver/mobilenet);
                    class names are read from it
    min_confidence  drop detections below this score (0-1)
"""

import os

from ament_index_python.packages import get_package_share_directory
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image
from vision_msgs.msg import Detection3DArray

from qirc_perception.detection_utils import (
    bbox_to_metres, draw_detections, image_to_numpy, load_label_names, numpy_to_image,
    pixel_box, relabel_detection)


def resolve_nn_config(nn_config):
    """
    Return the path of a depthai model config.

    Accepts the driver's 'package/name' form (resolved to
    <package share>/config/nn/<name>.json) or a path to a .json file.
    """
    if nn_config.endswith('.json'):
        return os.path.expanduser(nn_config)
    package, name = nn_config.split('/', 1)
    return os.path.join(get_package_share_directory(package), 'config', 'nn', name + '.json')


class RearDetectionNode(Node):
    """Relabel and filter the OAK's spatial detections onto /detections."""

    def __init__(self):
        super().__init__('rear_detection')
        self.declare_parameter('nn_config', 'depthai_ros_driver/mobilenet')
        self.declare_parameter('min_confidence', 0.5)

        path = resolve_nn_config(self.get_parameter('nn_config').value)
        with open(path) as config_file:
            self.label_names = load_label_names(config_file.read())
        self.get_logger().info(f'{len(self.label_names)} class names from {path}')

        self.camera_matrix = None
        self.latest_boxes = []      # pixel boxes of the last detections, to draw

        self.detection_pub = self.create_publisher(Detection3DArray, 'detections', 10)
        self.image_pub = self.create_publisher(Image, '~/image', qos_profile_sensor_data)
        self.create_subscription(
            Detection3DArray, 'rear_camera/nn/spatial_detections', self._detections_callback, 10)
        self.create_subscription(
            CameraInfo, 'rear_camera/nn/passthrough/camera_info', self._camera_info_callback,
            qos_profile_sensor_data)
        self.create_subscription(
            Image, 'rear_camera/nn/passthrough/image_raw', self._image_callback,
            qos_profile_sensor_data)
        self.get_logger().info('rear_detection started')

    def _camera_info_callback(self, msg):
        self.camera_matrix = list(msg.k)

    def _detections_callback(self, msg):
        if self.camera_matrix is None:
            self.get_logger().warn(
                'no rear_camera/nn/passthrough/camera_info yet: publishing detections '
                'with bounding box size 0 (is i_enable_passthrough set?)',
                throttle_duration_sec=10.0)
        min_confidence = self.get_parameter('min_confidence').value
        out = Detection3DArray()
        out.header = msg.header
        boxes = []
        for detection in msg.detections:
            relabelled = relabel_detection(detection, self.label_names, min_confidence)
            if relabelled is None:
                continue
            result = relabelled.results[0]
            boxes.append((*pixel_box(relabelled), result.hypothesis.class_id,
                          result.hypothesis.score, result.pose.pose.position.z))
            out.detections.append(bbox_to_metres(relabelled, self.camera_matrix))
        self.latest_boxes = boxes
        self.detection_pub.publish(out)

    def _image_callback(self, msg):
        if self.image_pub.get_subscription_count() == 0:
            return
        image = draw_detections(image_to_numpy(msg), self.latest_boxes)
        self.image_pub.publish(numpy_to_image(image, msg.header))


def main(args=None):
    rclpy.init(args=args)
    node = RearDetectionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
