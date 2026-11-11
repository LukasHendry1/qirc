"""Builds the house map from LiDAR scans."""

import rclpy
from rclpy.node import Node


class MappingNode(Node):
    """
    Builds the house map from LiDAR scans.

    Inputs:
        - LiDAR scan

    Outputs:
        - House map -> localization node, global planner
    """

    def __init__(self):
        super().__init__('mapping')
        self.get_logger().info('mapping started')


def main(args=None):
    rclpy.init(args=args)
    node = MappingNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
