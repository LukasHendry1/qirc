"""Moves the arm to the user height when appropriate."""

import rclpy
from rclpy.node import Node


class ArmNode(Node):
    """
    Moves the arm to the user height when appropriate.

    Inputs:
        - Arm command from vehicle manager
        - Dispense complete

    Outputs:
        - Arm motor commands
    """

    def __init__(self):
        super().__init__('arm')
        self.get_logger().info('arm started')


def main(args=None):
    rclpy.init(args=args)
    node = ArmNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
