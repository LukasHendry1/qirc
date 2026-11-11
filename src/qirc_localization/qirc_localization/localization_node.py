"""Estimates the robot pose within the house map."""

import rclpy
from rclpy.node import Node


class LocalizationNode(Node):
    """
    Estimates the robot pose within the house map.

    Inputs:
        - LiDAR scan
        - House map

    Outputs:
        - Robot pose -> planning stack
    """

    def __init__(self):
        super().__init__('localization')
        self.get_logger().info('localization started')


def main(args=None):
    rclpy.init(args=args)
    node = LocalizationNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
