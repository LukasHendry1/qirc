"""
Fuse the track odometry and the front camera's gyro (robot_localization EKF).

    # Simulation: sim.launch.py (qirc_gazebo) starts this itself.
    ros2 launch qirc_localization ekf.launch.py
    ros2 launch qirc_localization ekf.launch.py odometry:=lidar

Starts:
    imu_bias          removes the gyro bias, measured while the robot is
                      still: /front_camera/imu -> /front_camera/imu/unbiased
    ekf_filter_node   odometry + /front_camera/imu/unbiased -> /odometry/filtered
                      and the odom -> base_link transform
    laser_odometry    (odometry:=lidar only) scan matching: /scan -> /laser_odom

Nothing else may publish odom -> base_link: in simulation, sim.launch.py
stops DiffDrive's transform when it starts this. Parameters are in
config/ekf.yaml, and config/ekf_laser_odometry.yaml with odometry:=lidar.

Launch arguments:
    use_sim_time (default false): use the simulation clock (/clock).
    odometry (default encoders): where the EKF gets the robot's speed.
        encoders: the track odometry (/odom) from the drive motor encoders.
        lidar: LiDAR odometry (laser_odometry) instead, for running without
        encoders. /odom is then not used at all.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_sim_time = ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool)
    odometry = LaunchConfiguration('odometry')
    use_lidar = PythonExpression(["'", odometry, "' == 'lidar'"])
    config = PathJoinSubstitution([FindPackageShare('qirc_localization'), 'config'])
    # With odometry:=lidar, the overrides are loaded after ekf.yaml; otherwise
    # ekf.yaml is loaded twice, which changes nothing.
    ekf_overrides = PathJoinSubstitution([config, PythonExpression([
        "'ekf_laser_odometry.yaml' if '", odometry, "' == 'lidar' else 'ekf.yaml'",
    ])])
    odom_topic = PythonExpression([
        "'/laser_odom' if '", odometry, "' == 'lidar' else '/odom'",
    ])

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time', default_value='false',
            description='Use the simulation clock (/clock)'),
        DeclareLaunchArgument(
            'odometry', default_value='encoders', choices=['encoders', 'lidar'],
            description='Speed source: track odometry (encoders) or LiDAR odometry (lidar)'),
        Node(
            package='qirc_localization',
            executable='laser_odometry',
            name='laser_odometry',
            parameters=[{'use_sim_time': use_sim_time}],
            condition=IfCondition(use_lidar),
            output='screen',
        ),
        Node(
            package='qirc_localization',
            executable='imu_bias',
            name='imu_bias',
            parameters=[{'use_sim_time': use_sim_time, 'odom_topic': odom_topic}],
            output='screen',
        ),
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node',
            parameters=[
                PathJoinSubstitution([config, 'ekf.yaml']),
                ekf_overrides,
                {'use_sim_time': use_sim_time},
            ],
            output='screen',
        ),
    ])
