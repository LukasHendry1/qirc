"""Local planner: handles detours and obstacle avoidance during traversal."""

import rclpy
from rclpy.node import Node


class LocalPlannerNode(Node):
    """
    Adjust the trajectory locally during traversal.

    Handles small trajectory changes and detours (obstacle avoidance).

    Inputs:
        - Global trajectory
        - Robot pose
        - Detections

    Outputs:
        - Local trajectory / reference -> controls
    """

    def __init__(self):
        super().__init__('local_planner')
        self.get_logger().info('local_planner started')


def main(args=None):
    rclpy.init(args=args)
    node = LocalPlannerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
