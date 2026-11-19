"""
Republish the rear OAK-D Lite's on-camera detections on /detections.

The OAK runs its neural network on the camera itself and the depthai driver
publishes the results with 3D positions. This node relabels them to the
shared /detections classes and filters them; it doesn't run a model.

Subscribes:
    /rear_camera/nn/spatial_detections   vision_msgs/Detection3DArray

Publishes:
    /detections   vision_msgs/Detection3DArray, in the rear camera's frame
                  (unchanged from the driver). Labels: 'person' or 'object'.

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
from vision_msgs.msg import Detection3DArray

from qirc_perception.detection_utils import load_label_names, relabel_detection


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

        self.detection_pub = self.create_publisher(Detection3DArray, 'detections', 10)
        self.create_subscription(
            Detection3DArray, 'rear_camera/nn/spatial_detections', self._detections_callback, 10)
        self.get_logger().info('rear_detection started')

    def _detections_callback(self, msg):
        min_confidence = self.get_parameter('min_confidence').value
        out = Detection3DArray()
        out.header = msg.header
        for detection in msg.detections:
            relabelled = relabel_detection(detection, self.label_names, min_confidence)
            if relabelled is not None:
                out.detections.append(relabelled)
        self.detection_pub.publish(out)


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
