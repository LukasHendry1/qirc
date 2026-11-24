"""
Odometry from the LiDAR alone, by matching each scan to a recent one (ICP).

The robot has no drive motor encoders, so this is its odometry: the EKF
(ekf.launch.py) fuses its speeds with the gyro.

Each scan is matched to a keyframe, an earlier scan, with point-to-line ICP:
the scan's points are moved until they lie on the lines (walls, furniture
edges) through the keyframe's points. Matching to a keyframe rather than to
the previous scan keeps the small per-match errors from adding up while the
robot is still or moving slowly. When the robot has moved far enough from
the keyframe, the current scan becomes the new keyframe.

Weak spots: where the walls are all parallel (a long bare hallway), the scan
looks the same as the robot moves along them and the match can't tell how
far it went. The match reports this, and the speed it publishes then gets a
large covariance, so the EKF trusts it less.

Subscribes:
    /scan            sensor_msgs/LaserScan
Publishes:
    /laser_odom      nav_msgs/Odometry: pose in odom, speed in base_link.
                     No TF: the EKF publishes odom -> base_link.

Node parameters:
    max_match_distance (m): points further than this from the keyframe's
        nearest point are ignored (not seen in both scans).
    keyframe_distance (m), keyframe_angle (rad): start a new keyframe when
        the robot is this far from the current one.
    twist_window (scans): the speed is measured over this many scans, which
        averages out the scan-to-scan jitter.
    speed_stddev (m/s), turn_rate_stddev (rad/s): reported covariances of a
        good match.
"""

import math

import numpy as np
import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from scipy.spatial import cKDTree
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from tf2_ros import Buffer, TransformException, TransformListener

MIN_POINTS = 30           # fewer matched points than this: no match
# A match is degenerate (e.g. a bare hallway) when its weakest direction is
# this much weaker than its strongest.
DEGENERATE_RATIO = 0.1


def se2(x, y, theta):
    """Return the 3x3 homogeneous transform for a 2D pose."""
    c, s = math.cos(theta), math.sin(theta)
    return np.array([[c, -s, x], [s, c, y], [0.0, 0.0, 1.0]])


def pose_of(transform):
    """Return (x, y, theta) of a 3x3 homogeneous transform."""
    return (transform[0, 2], transform[1, 2],
            math.atan2(transform[1, 0], transform[0, 0]))


def apply(transform, points):
    """Transform (N, 2) points by a 3x3 homogeneous transform."""
    return points @ transform[:2, :2].T + transform[:2, 2]


def scan_points(ranges, angle_min, angle_increment, range_min, range_max):
    """Convert scan ranges to (N, 2) points in the scan's frame, dropping invalid ones."""
    ranges = np.asarray(ranges, dtype=float)
    angles = angle_min + angle_increment * np.arange(len(ranges))
    valid = np.isfinite(ranges) & (ranges > range_min) & (ranges < range_max)
    r, a = ranges[valid], angles[valid]
    return np.column_stack([r * np.cos(a), r * np.sin(a)])


def line_normals(points, tree, neighbours=6, max_spread=0.3):
    """
    Return each point's normal to the line through its neighbours.

    Also returns a mask of the points that lie on a clear line: ones in a
    corner, on a curve or isolated have no reliable normal.
    """
    distances, index = tree.query(points, k=neighbours)
    near = points[index] - points[index].mean(axis=1, keepdims=True)
    covariance = np.einsum('nki,nkj->nij', near, near)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)   # ascending
    normals = eigenvectors[:, :, 0]
    on_line = ((eigenvalues[:, 0] < 0.05 * eigenvalues[:, 1])
               & (distances[:, -1] < max_spread))
    return normals, on_line


class Keyframe:
    """A scan to match others to, with its search tree and line normals."""

    def __init__(self, points):
        self.tree = cKDTree(points)
        normals, on_line = line_normals(points, self.tree)
        self.points = points[on_line]
        self.normals = normals[on_line]
        self.tree = cKDTree(self.points)


def match(points, keyframe, guess, max_distance=0.5, iterations=30):
    """
    Find the pose of a scan relative to a keyframe (point-to-line ICP).

    points: (N, 2) scan points in the robot's frame. guess: 3x3 starting
    estimate. Returns (transform, information, inlier fraction), where
    information is the 3x3 matrix of the final least-squares problem (x, y,
    theta): its eigenvalues show how well each direction was pinned down.
    Returns None if too few points matched.
    """
    if len(keyframe.points) < MIN_POINTS:
        return None
    transform = guess.copy()
    information = np.zeros((3, 3))
    inliers = 0
    for i in range(iterations):
        # Start wide, to catch a poor guess, then tighten to drop outliers.
        limit = max(0.15, max_distance * 0.7 ** i)
        moved = apply(transform, points)
        distance, index = keyframe.tree.query(moved, distance_upper_bound=limit)
        found = np.isfinite(distance)
        inliers = int(found.sum())
        if inliers < MIN_POINTS:
            return None
        p = moved[found]
        q = keyframe.points[index[found]]
        n = keyframe.normals[index[found]]
        residual = np.sum(n * (q - p), axis=1)
        # Small rotation theta about the origin moves p by theta * (-py, px).
        a = np.column_stack([n[:, 0], n[:, 1], n[:, 1] * p[:, 0] - n[:, 0] * p[:, 1]])
        weight = 1.0 / (1.0 + (residual / 0.03) ** 2)       # Cauchy: tolerate outliers
        information = a.T @ (a * weight[:, None])
        try:
            step = np.linalg.solve(information, a.T @ (weight * residual))
        except np.linalg.LinAlgError:
            return None
        transform = se2(*step) @ transform
        if np.hypot(step[0], step[1]) < 1e-5 and abs(step[2]) < 1e-5:
            break
    return transform, information, inliers / len(points)


def degenerate(information):
    """Return True if a match left a direction (x or y) poorly constrained."""
    eigenvalues = np.linalg.eigvalsh(information[:2, :2])
    return eigenvalues[0] < DEGENERATE_RATIO * eigenvalues[1]


class LaserOdometry(Node):
    """Publish odometry from scan matching."""

    def __init__(self):
        super().__init__('laser_odometry')
        self.declare_parameter('max_match_distance', 0.5)
        self.declare_parameter('keyframe_distance', 0.25)
        self.declare_parameter('keyframe_angle', 0.25)
        self.declare_parameter('twist_window', 3)
        self.declare_parameter('speed_stddev', 0.02)
        self.declare_parameter('turn_rate_stddev', 0.02)
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_link')

        self.odom_frame = self.get_parameter('odom_frame').value
        self.base_frame = self.get_parameter('base_frame').value
        self.laser_to_base = None    # 3x3, from TF (static: the URDF)
        self.keyframe = None
        self.keyframe_pose = np.eye(3)   # keyframe in odom
        self.relative = np.eye(3)        # robot relative to the keyframe
        self.step = np.eye(3)            # motion over the last scan, for the guess
        self.history = []                # recent (stamp, pose in odom)
        self.warned_degenerate = False

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.pub = self.create_publisher(Odometry, '/laser_odom', 10)
        self.create_subscription(LaserScan, '/scan', self.scan_callback, qos_profile_sensor_data)

    def _laser_to_base(self, frame):
        if self.laser_to_base is None:
            try:
                t = self.tf_buffer.lookup_transform(
                    self.base_frame, frame, Time(), timeout=Duration(seconds=0.0))
            except TransformException as error:
                self.get_logger().warn(
                    f'waiting for {self.base_frame} -> {frame}: {error}',
                    throttle_duration_sec=5.0)
                return None
            q = t.transform.rotation
            yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y ** 2 + q.z ** 2))
            self.laser_to_base = se2(t.transform.translation.x, t.transform.translation.y, yaw)
        return self.laser_to_base

    def scan_callback(self, scan):
        laser_to_base = self._laser_to_base(scan.header.frame_id)
        if laser_to_base is None:
            return
        points = apply(laser_to_base, scan_points(
            scan.ranges, scan.angle_min, scan.angle_increment, scan.range_min, scan.range_max))
        if len(points) < MIN_POINTS:
            return
        stamp = Time.from_msg(scan.header.stamp)

        if self.keyframe is None:
            self.keyframe = Keyframe(points)
            self._publish(stamp, good=True)
            return

        result = match(points, self.keyframe, self.relative @ self.step,
                       self.get_parameter('max_match_distance').value)
        good = result is not None and not degenerate(result[1])
        if result is None:
            # Lost (e.g. the view changed completely): keep the motion
            # guess and start again from this scan.
            self.get_logger().warn('scan match failed; restarting from this scan',
                                   throttle_duration_sec=2.0)
            new_relative = self.relative @ self.step
        else:
            new_relative = result[0]
            if not good and not self.warned_degenerate:
                self.warned_degenerate = True
                self.get_logger().warn(
                    'scan match poorly constrained (parallel walls?); '
                    'reporting a large speed covariance')
        self.step = np.linalg.inv(self.relative) @ new_relative
        self.relative = new_relative

        x, y, theta = pose_of(self.relative)
        if (result is None
                or math.hypot(x, y) > self.get_parameter('keyframe_distance').value
                or abs(theta) > self.get_parameter('keyframe_angle').value):
            self.keyframe_pose = self.keyframe_pose @ self.relative
            self.relative = np.eye(3)
            self.keyframe = Keyframe(points)
        self._publish(stamp, good)

    def _publish(self, stamp, good):
        pose = self.keyframe_pose @ self.relative
        self.history.append((stamp, pose))
        window = max(1, int(self.get_parameter('twist_window').value))
        self.history = self.history[-(window + 1):]

        msg = Odometry()
        msg.header.stamp = stamp.to_msg()
        msg.header.frame_id = self.odom_frame
        msg.child_frame_id = self.base_frame
        x, y, theta = pose_of(pose)
        msg.pose.pose.position.x, msg.pose.pose.position.y = float(x), float(y)
        msg.pose.pose.orientation.z = math.sin(theta / 2)
        msg.pose.pose.orientation.w = math.cos(theta / 2)

        old_stamp, old_pose = self.history[0]
        dt = (stamp - old_stamp).nanoseconds * 1e-9
        if dt > 0:
            # Speed over the window, in the robot's current frame.
            dx, dy, dtheta = pose_of(np.linalg.inv(old_pose) @ pose)
            c, s = math.cos(dtheta), math.sin(dtheta)
            msg.twist.twist.linear.x = float((c * dx + s * dy) / dt)
            msg.twist.twist.linear.y = float((-s * dx + c * dy) / dt)
            msg.twist.twist.angular.z = float(dtheta / dt)

        speed_var = self.get_parameter('speed_stddev').value ** 2
        turn_var = self.get_parameter('turn_rate_stddev').value ** 2
        if not good:
            speed_var = turn_var = 1.0     # barely trusted
        cov = [0.0] * 36
        cov[0] = cov[7] = speed_var
        cov[14] = cov[21] = cov[28] = 1e-3
        cov[35] = turn_var
        msg.twist.covariance = cov
        pose_cov = [0.0] * 36
        pose_cov[0] = pose_cov[7] = pose_cov[35] = 1e-2
        pose_cov[14] = pose_cov[21] = pose_cov[28] = 1e-3
        msg.pose.covariance = pose_cov
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = LaserOdometry()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
