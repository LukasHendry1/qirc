"""Local planner: follows the global path and avoids obstacles, as one MPC."""

import rclpy
from rclpy.node import Node


class LocalPlannerNode(Node):
    """
    Follow the global path while avoiding obstacles, and drive the robot.

    A sampling-based MPC (like Nav2's MPPI controller): rolls out candidate
    command sequences through a skid-steer model of the tracks (#64), scores
    them on path following, clearance and smoothness, and sends the best
    first command (#63). It is the only layer between the global planner and
    the motors; there is no separate path-tracking controller.

    Inputs:
        - Global path: /plan
        - Obstacles: /scan, /detections (larger margin around people)
        - Robot velocity: /odometry/filtered; pose: TF map -> base_link

    Outputs:
        - Velocity command: /cmd_vel_nav -> twist_mux
        - Predicted path of the chosen rollout: /local_plan (RViz only)
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
