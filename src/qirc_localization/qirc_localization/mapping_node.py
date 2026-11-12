"""Builds the house map from LiDAR scans."""

import math

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


class MappingNode(Node):
    """
    Builds the house map from LiDAR scans.

    Inputs:
        - LiDAR scan: /scan

    Outputs:
        - House map -> localization node, global planner
    """

    def __init__(self):
        super().__init__('mapping')
        self.scan_sub = self.create_subscription(
            LaserScan, 'scan', self.scan_callback, qos_profile_sensor_data)
        self.get_logger().info('mapping started')

    def scan_callback(self, msg):
        valid = [
            r for r in msg.ranges
            if math.isfinite(r) and msg.range_min <= r <= msg.range_max
        ]
        closest = f'{min(valid):.2f} m' if valid else 'n/a'
        self.get_logger().info(
            f'scan: {len(valid)}/{len(msg.ranges)} valid points, closest {closest}',
            throttle_duration_sec=2.0,
        )


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
