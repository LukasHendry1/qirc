"""Detects objects and the user from the front and back camera images."""

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


class ObjectDetectionNode(Node):
    """
    Detects objects and the user from the front and back camera images.

    Inputs:
        - Front camera image (RealSense D435i): /front_camera/color/image_raw
        - Rear camera image (OAK-D Lite): /rear_camera/rgb/image_raw

    Outputs:
        - Detections (objects / user / stairwell) -> planning stack
    """

    def __init__(self):
        super().__init__('object_detection')
        self.front_image_sub = self.create_subscription(
            Image,
            'front_camera/color/image_raw',
            self.front_image_callback,
            qos_profile_sensor_data,
        )
        self.rear_image_sub = self.create_subscription(
            Image,
            'rear_camera/rgb/image_raw',
            self.rear_image_callback,
            qos_profile_sensor_data,
        )
        self.get_logger().info('object_detection started')

    def front_image_callback(self, msg):
        self.get_logger().info(
            f'front camera frame: {msg.width}x{msg.height} ({msg.encoding})',
            throttle_duration_sec=2.0,
        )

    def rear_image_callback(self, msg):
        self.get_logger().info(
            f'rear camera frame: {msg.width}x{msg.height} ({msg.encoding})',
            throttle_duration_sec=2.0,
        )


def main(args=None):
    rclpy.init(args=args)
    node = ObjectDetectionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
