"""Tracks the local planner trajectory (MPC) and commands the drive motors."""

import rclpy
from rclpy.node import Node


class ControlNode(Node):
    """
    Tracks the local planner trajectory (MPC) and commands the drive motors.

    Inputs:
        - Local trajectory
        - Robot pose

    Outputs:
        - Drive motor commands
    """

    def __init__(self):
        super().__init__('control')
        self.get_logger().info('control started')


def main(args=None):
    rclpy.init(args=args)
    node = ControlNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
