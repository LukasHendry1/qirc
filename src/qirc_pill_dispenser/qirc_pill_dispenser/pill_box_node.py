"""Controls how many pills are dispensed via the dispensing motors."""

import rclpy
from rclpy.node import Node


class PillBoxNode(Node):
    """
    Controls how many pills are dispensed via the dispensing motors.

    Inputs:
        - Dispense command from vehicle manager

    Outputs:
        - Dispensing motor commands
        - Dispense complete -> arm node
    """

    def __init__(self):
        super().__init__('pill_box')
        self.get_logger().info('pill_box started')


def main(args=None):
    rclpy.init(args=args)
    node = PillBoxNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
