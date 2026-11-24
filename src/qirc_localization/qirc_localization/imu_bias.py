"""
Remove the gyro bias from the front camera's IMU, measured while the robot is still.

A MEMS gyro reads a small rate even when it isn't turning (its bias); the
D435i's can be around 0.5 deg/s. The EKF integrates the gyro for the
heading, so an uncorrected bias turns the robot ~30 degrees a minute on the
map while it stands still. robot_localization can't estimate the bias
itself, so this node does: whenever the track odometry says the robot is
still, the gyro should read zero, and what it reads is the bias.

Subscribes:
    /front_camera/imu        sensor_msgs/Imu, from realsense2_camera or Gazebo
    /odom                    nav_msgs/Odometry, to tell when the robot is still
                             (the odom_topic parameter; /laser_odom when the
                             LiDAR stands in for the encoders)
Publishes:
    /front_camera/imu/unbiased   the same, minus the gyro bias, with the
                                 covariances the EKF needs

Node parameters:
    odom_topic: the odometry to tell stillness from (default /odom).
    still_speed (m/s), still_turn_rate (rad/s): the robot counts as still
        when the odometry is below both...
    settle_time (s): ...for this long (so it has stopped rocking).
    averaging_time (s): the bias is averaged over about this much still time,
        so it can follow slow changes with temperature.
    angular_velocity_stddev (rad/s), linear_acceleration_stddev (m/s^2):
        reported as the message covariances.
"""

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu


class GyroBias:
    """Running estimate of the gyro bias from samples taken while still."""

    def __init__(self, averaging_samples):
        self.averaging_samples = averaging_samples
        self.bias = np.zeros(3)
        self.samples = 0

    def add(self, rate):
        """Add a gyro reading (rad/s, 3 axes) taken while the robot is still."""
        self.samples += 1
        # A plain mean at first, then an exponential average over about
        # averaging_samples samples.
        weight = 1.0 / min(self.samples, self.averaging_samples)
        self.bias += weight * (np.asarray(rate, dtype=float) - self.bias)

    @property
    def known(self):
        return self.samples > 0


class ImuBias(Node):
    """Republish the IMU with the gyro bias removed."""

    def __init__(self):
        super().__init__('imu_bias')
        self.declare_parameter('odom_topic', '/odom')
        self.declare_parameter('still_speed', 0.01)
        self.declare_parameter('still_turn_rate', 0.01)
        self.declare_parameter('settle_time', 0.5)
        self.declare_parameter('averaging_time', 10.0)
        self.declare_parameter('imu_rate', 200.0)
        self.declare_parameter('angular_velocity_stddev', 0.005)
        self.declare_parameter('linear_acceleration_stddev', 0.05)

        averaging_samples = int(self.get_parameter('averaging_time').value
                                * self.get_parameter('imu_rate').value)
        self.bias = GyroBias(max(averaging_samples, 1))
        self.still_since = None     # time the robot stopped, None if moving
        self.announced = False

        gyro_var = self.get_parameter('angular_velocity_stddev').value ** 2
        accel_var = self.get_parameter('linear_acceleration_stddev').value ** 2
        self.gyro_cov = [gyro_var, 0.0, 0.0, 0.0, gyro_var, 0.0, 0.0, 0.0, gyro_var]
        self.accel_cov = [accel_var, 0.0, 0.0, 0.0, accel_var, 0.0, 0.0, 0.0, accel_var]

        self.pub = self.create_publisher(Imu, '/front_camera/imu/unbiased', 50)
        self.create_subscription(
            Imu, '/front_camera/imu', self.imu_callback, qos_profile_sensor_data)
        self.create_subscription(
            Odometry, self.get_parameter('odom_topic').value, self.odom_callback, 10)

    def odom_callback(self, msg):
        twist = msg.twist.twist
        still = (abs(twist.linear.x) < self.get_parameter('still_speed').value
                 and abs(twist.angular.z) < self.get_parameter('still_turn_rate').value)
        if not still:
            self.still_since = None
        elif self.still_since is None:
            self.still_since = self.get_clock().now()

    def _settled(self):
        if self.still_since is None:
            return False
        still_for = (self.get_clock().now() - self.still_since).nanoseconds * 1e-9
        return still_for >= self.get_parameter('settle_time').value

    def imu_callback(self, msg):
        w = msg.angular_velocity
        rate = (w.x, w.y, w.z)
        if self._settled():
            self.bias.add(rate)
            if not self.announced and self.bias.samples >= 200:
                self.announced = True
                self.get_logger().info(
                    'gyro bias (deg/s): '
                    + ', '.join(f'{b:+.3f}' for b in np.degrees(self.bias.bias)))

        out = Imu()
        out.header = msg.header
        out.angular_velocity.x, out.angular_velocity.y, out.angular_velocity.z = (
            float(v) for v in np.asarray(rate) - self.bias.bias)
        out.angular_velocity_covariance = self.gyro_cov
        out.linear_acceleration = msg.linear_acceleration
        out.linear_acceleration_covariance = self.accel_cov
        # Like realsense2_camera: no orientation.
        out.orientation_covariance[0] = -1.0
        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = ImuBias()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
