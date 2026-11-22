"""
Fuse the track odometry and the front camera's gyro (robot_localization EKF).

    # Simulation: sim.launch.py (qirc_gazebo) starts this itself.
    ros2 launch qirc_localization ekf.launch.py

Starts:
    imu_bias          removes the gyro bias, measured while the robot is
                      still: /front_camera/imu -> /front_camera/imu/unbiased
    ekf_filter_node   /odom + /front_camera/imu/unbiased -> /odometry/filtered
                      and the odom -> base_link transform

Nothing else may publish odom -> base_link: in simulation, sim.launch.py
stops DiffDrive's transform when it starts this. Parameters are in
config/ekf.yaml.

Launch arguments:
    use_sim_time (default false): use the simulation clock (/clock).
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_sim_time = ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool)

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time', default_value='false',
            description='Use the simulation clock (/clock)'),
        Node(
            package='qirc_localization',
            executable='imu_bias',
            name='imu_bias',
            parameters=[{'use_sim_time': use_sim_time}],
            output='screen',
        ),
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node',
            parameters=[
                PathJoinSubstitution([
                    FindPackageShare('qirc_localization'), 'config', 'ekf.yaml']),
                {'use_sim_time': use_sim_time},
            ],
            output='screen',
        ),
    ])
