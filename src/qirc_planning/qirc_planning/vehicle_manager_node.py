"""Top-level state machine."""

import rclpy
from rclpy.node import Node


class VehicleManagerNode(Node):
    """
    Top-level state machine for the robot.

    Decides when to wake up, initializes the global planner, and triggers
    going up stairs, dispensing pills and moving the arm.

    Inputs:
        - Detections
        - Robot pose

    Outputs:
        - Goals -> global planner
        - Dispense / arm commands -> pill dispenser
    """

    def __init__(self):
        super().__init__('vehicle_manager')
        self.get_logger().info('vehicle_manager started')


def main(args=None):
    rclpy.init(args=args)
    node = VehicleManagerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
