"""Global planner: chooses points to check and generates trajectories."""

import rclpy
from rclpy.node import Node


class GlobalPlannerNode(Node):
    """
    Plan a global trajectory through the house.

    Generates candidate points around the home to check, chooses a point
    to traverse to, and generates a trajectory to follow.

    Inputs:
        - Commands from vehicle manager
        - House map
        - Robot pose
        - Detections

    Outputs:
        - Global trajectory -> local planner
    """

    def __init__(self):
        super().__init__('global_planner')
        self.get_logger().info('global_planner started')


def main(args=None):
    rclpy.init(args=args)
    node = GlobalPlannerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
