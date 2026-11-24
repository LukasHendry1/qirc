"""
Simulation test: drive a fixed loop and measure the localization error.

Drives the robot around a loop of waypoints, steering by its true pose from
Gazebo (/ground_truth), and records where the stack thinks it is:
    odometry   odom -> base_link (the EKF): drifts, never corrected
    SLAM       map -> base_link (slam_toolbox on top of the EKF)
Both are compared with the true pose, taken relative to where the robot
started, because odom and map both start at the robot's starting pose.

    ros2 launch qirc_gazebo sim.launch.py headless:=true odometry:=lidar
    ros2 launch qirc_localization mapping.launch.py use_sim_time:=true
    ros2 run qirc_localization odometry_test --ros-args
        -p use_sim_time:=true -p output:=~/qirc_tests/lidar      (one line)

Writes <output>.csv (one row per sample) and <output>.png (paths and errors)
and prints a summary. The default loop suits obstacles.sdf: about 12 m with
four 90 degree turns on the spot, which is where odometry matters most.

Node parameters:
    output: path prefix for the results (default ~/qirc_tests/odometry_test).
    laps (default 2), speed (m/s, default 0.3), turn_rate (rad/s, default 0.6).
    waypoints: flat list x1, y1, x2, y2, ... in the world frame (m).
"""

import csv
import math
from pathlib import Path

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from tf2_ros import Buffer, TransformException, TransformListener

# Around the boxes in obstacles.sdf, back to the start (0, 0). Keeps at
# least ~0.2 m between the robot (about 0.5 m square) and the boxes.
DEFAULT_WAYPOINTS = [3.3, 0.0, 3.3, 2.0, -1.0, 2.0, -1.0, 0.0, 0.0, 0.0]
ARRIVED = 0.1            # m
FACING = 0.05            # rad: turn on the spot until within this
SAMPLE_PERIOD = 0.1      # s
STUCK_TIME = 15.0        # s: give up if the robot hasn't moved for this long


def yaw_of(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y ** 2 + q.z ** 2))


def wrap(angle):
    return (angle + math.pi) % (2 * math.pi) - math.pi


def relative_pose(start, pose):
    """Return pose (x, y, yaw) expressed in the frame of start (x, y, yaw)."""
    dx, dy = pose[0] - start[0], pose[1] - start[1]
    c, s = math.cos(start[2]), math.sin(start[2])
    return (c * dx + s * dy, -s * dx + c * dy, wrap(pose[2] - start[2]))


def errors(truth, estimate):
    """Position (m) and heading (rad) errors of an estimate (N, 3) against truth (N, 3)."""
    truth, estimate = np.asarray(truth, dtype=float), np.asarray(estimate, dtype=float)
    position = np.hypot(*(estimate[:, :2] - truth[:, :2]).T)
    heading = np.abs((estimate[:, 2] - truth[:, 2] + np.pi) % (2 * np.pi) - np.pi)
    return position, heading


def summary(truth, estimate):
    """Return final, max and RMS position error (m) and max heading error (deg)."""
    position, heading = errors(truth, estimate)
    return {
        'final_m': float(position[-1]),
        'max_m': float(position.max()),
        'rms_m': float(np.sqrt(np.mean(position ** 2))),
        'max_heading_deg': float(np.degrees(heading.max())),
    }


class OdometryTest(Node):
    """Drive the loop and record true and estimated poses."""

    def __init__(self):
        super().__init__('odometry_test')
        self.declare_parameter('output', '~/qirc_tests/odometry_test')
        self.declare_parameter('laps', 2)
        self.declare_parameter('speed', 0.3)
        self.declare_parameter('turn_rate', 0.6)
        self.declare_parameter('waypoints', DEFAULT_WAYPOINTS)

        flat = list(self.get_parameter('waypoints').value)
        loop = list(zip(flat[0::2], flat[1::2]))
        self.route = loop * int(self.get_parameter('laps').value)
        self.speed = self.get_parameter('speed').value
        self.turn_rate = self.get_parameter('turn_rate').value

        self.truth = None          # latest true pose (x, y, yaw) in world
        self.start = None
        self.rows = []
        self.done = False
        self.stuck = False
        self.last_progress = None   # (time, true pose) when it last moved

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.create_subscription(Odometry, '/ground_truth', self.truth_callback, 10)
        self.create_timer(SAMPLE_PERIOD, self.tick)

    def truth_callback(self, msg):
        p = msg.pose.pose
        self.truth = (p.position.x, p.position.y, yaw_of(p.orientation))

    def _lookup(self, parent):
        try:
            t = self.tf_buffer.lookup_transform(parent, 'base_link', Time())
        except TransformException:
            return None
        return (t.transform.translation.x, t.transform.translation.y,
                yaw_of(t.transform.rotation))

    def tick(self):
        if self.done or self.truth is None:
            return
        odom, slam = self._lookup('odom'), self._lookup('map')
        if odom is None:
            self.get_logger().info('waiting for odom -> base_link', throttle_duration_sec=5.0)
            return
        if self.start is None:
            self.start = self.truth
            self.get_logger().info(
                f'driving {len(self.route)} waypoints'
                + ('' if slam else ' (no map -> base_link: SLAM not running?)'))
        truth = relative_pose(self.start, self.truth)
        now = self.get_clock().now().nanoseconds * 1e-9
        if self._stuck(now):
            self.get_logger().error(
                f'robot hasn\'t moved for {STUCK_TIME:.0f} s (hit something?); stopping')
            self.stuck = True
            self._finish()
            return
        self.rows.append((now, *truth, *odom, *(slam if slam else (math.nan,) * 3)))
        self.cmd_pub.publish(self._steer())

    def _stuck(self, now):
        if self.last_progress is None:
            self.last_progress = (now, self.truth)
            return False
        then, pose = self.last_progress
        if (math.hypot(self.truth[0] - pose[0], self.truth[1] - pose[1]) > 0.05
                or abs(wrap(self.truth[2] - pose[2])) > 0.1):
            self.last_progress = (now, self.truth)
            return False
        return now - then > STUCK_TIME

    def _steer(self):
        cmd = Twist()
        if not self.route:
            self._finish()
            return cmd
        x, y, yaw = self.truth
        gx, gy = self.route[0]
        distance = math.hypot(gx - x, gy - y)
        if distance < ARRIVED:
            self.route.pop(0)
            return cmd
        error = wrap(math.atan2(gy - y, gx - x) - yaw)
        if abs(error) > FACING and distance > 0.3:
            # Turn on the spot to face the next waypoint.
            cmd.angular.z = math.copysign(min(self.turn_rate, 2.0 * abs(error)), error)
        else:
            cmd.linear.x = min(self.speed, distance) if abs(error) < 0.5 else 0.0
            cmd.angular.z = max(-self.turn_rate, min(self.turn_rate, 2.0 * error))
        return cmd

    def _finish(self):
        self.done = True
        self.cmd_pub.publish(Twist())
        output = Path(self.get_parameter('output').value).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        data = np.array(self.rows, dtype=float)
        with open(output.with_suffix('.csv'), 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['t', 'true_x', 'true_y', 'true_yaw', 'odom_x', 'odom_y', 'odom_yaw',
                             'slam_x', 'slam_y', 'slam_yaw'])
            writer.writerows(data)

        truth, odom, slam = data[:, 1:4], data[:, 4:7], data[:, 7:10]
        lines = [f'{len(data)} samples over {data[-1, 0] - data[0, 0]:.0f} s (sim time)'
                 + (' -- STOPPED EARLY: robot stuck' if self.stuck else '')]
        results = {'odometry': summary(truth, odom)}
        has_slam = np.isfinite(slam).all(axis=1)
        if has_slam.any():
            results['SLAM'] = summary(truth[has_slam], slam[has_slam])
        for name, r in results.items():
            lines.append(f"{name:9s} position error: final {r['final_m']:.3f} m, "
                         f"max {r['max_m']:.3f} m, RMS {r['rms_m']:.3f} m; "
                         f"heading max {r['max_heading_deg']:.1f} deg")
        for line in lines:
            self.get_logger().info(line)
        output.with_suffix('.txt').write_text('\n'.join(lines) + '\n')
        self._plot(data, has_slam, output.with_suffix('.png'))
        self.get_logger().info(f'results written to {output}.csv/.txt/.png')
        raise SystemExit

    @staticmethod
    def _plot(data, has_slam, path):
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        t = data[:, 0] - data[0, 0]
        truth, odom, slam = data[:, 1:4], data[:, 4:7], data[:, 7:10]
        fig, (ax_path, ax_err) = plt.subplots(1, 2, figsize=(12, 5))
        ax_path.plot(truth[:, 0], truth[:, 1], 'k-', label='true')
        ax_path.plot(odom[:, 0], odom[:, 1], '-', color='tab:orange', label='odometry (EKF)')
        if has_slam.any():
            ax_path.plot(slam[has_slam, 0], slam[has_slam, 1], '-', color='tab:blue', label='SLAM')
        ax_path.set_aspect('equal')
        ax_path.set_xlabel('x (m)')
        ax_path.set_ylabel('y (m)')
        ax_path.set_title('Path (relative to the start)')
        ax_path.legend()

        odom_err, _ = errors(truth, odom)
        ax_err.plot(t, odom_err, color='tab:orange', label='odometry (EKF)')
        if has_slam.any():
            slam_err, _ = errors(truth[has_slam], slam[has_slam])
            ax_err.plot(t[has_slam], slam_err, color='tab:blue', label='SLAM')
        ax_err.set_xlabel('time (s, sim)')
        ax_err.set_ylabel('position error (m)')
        ax_err.set_title('Position error')
        ax_err.grid(True)
        ax_err.legend()
        fig.tight_layout()
        fig.savefig(path, dpi=120)
        plt.close(fig)


def main(args=None):
    rclpy.init(args=args)
    node = OdometryTest()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
