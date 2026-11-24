"""
Launch the QIRC simulation in Gazebo Fortress.

Starts Gazebo with a world, publishes the robot model (with its Gazebo parts,
sim:=true) from robot_state_publisher on simulation time, spawns the robot
from /robot_description, and bridges the topics in config/ between Gazebo
and ROS.

Arguments:
    world (default obstacles.sdf): world file in qirc_gazebo/worlds.
        obstacles.sdf has a few walls and boxes for the LiDAR to see;
        empty.sdf is just the ground.
    headless (default false): run the Gazebo server only, without the GUI.
    ekf (default true): fuse the odometry and the simulated D435i's gyro
        with qirc_localization's EKF (ekf.launch.py), which then publishes
        odom -> base_link. With ekf:=false, DiffDrive's odometry publishes
        it instead.
    odometry (default encoders): the EKF's speed source (ekf.launch.py).
        encoders: DiffDrive's /odom, standing in for the drive motor
        encoders. lidar: LiDAR odometry instead, to see how the robot does
        without encoders.

Also publishes the robot's true pose (/ground_truth, nav_msgs/Odometry in
the world frame) for measuring localization error.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    world = PathJoinSubstitution([
        FindPackageShare('qirc_gazebo'), 'worlds', LaunchConfiguration('world'),
    ])
    # -r: start running straight away. -s: server only (no GUI).
    server_only = PythonExpression([
        "' -s' if '", LaunchConfiguration('headless'), "' == 'true' else ''",
    ])
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py',
        ])),
        launch_arguments={
            'gz_args': [world, ' -r', server_only],
            'on_exit_shutdown': 'true',
        }.items(),
    )

    robot_description = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('qirc_description'), 'launch', 'description.launch.py',
        ])),
        launch_arguments={'sim': 'true', 'use_sim_time': 'true'}.items(),
    )
    # Spawned slightly above the ground so the wheels don't start inside it.
    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-topic', 'robot_description', '-name', 'qirc', '-z', '0.02'],
        output='screen',
    )

    config = PathJoinSubstitution([FindPackageShare('qirc_gazebo'), 'config'])
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='gz_bridge',
        parameters=[{
            'config_file': PathJoinSubstitution([config, 'bridge.yaml']),
            'use_sim_time': True,
        }],
        output='screen',
    )
    # Exactly one of these publishes odom -> base_link.
    ekf = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('qirc_localization'), 'launch', 'ekf.launch.py',
        ])),
        launch_arguments={
            'use_sim_time': 'true',
            'odometry': LaunchConfiguration('odometry'),
        }.items(),
        condition=IfCondition(LaunchConfiguration('ekf')),
    )
    odom_tf_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='gz_odom_tf_bridge',
        parameters=[{
            'config_file': PathJoinSubstitution([config, 'bridge_odom_tf.yaml']),
            'use_sim_time': True,
        }],
        condition=UnlessCondition(LaunchConfiguration('ekf')),
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'world', default_value='obstacles.sdf',
            description='World file in qirc_gazebo/worlds'),
        DeclareLaunchArgument(
            'headless', default_value='false',
            description='Run the Gazebo server only, without the GUI'),
        DeclareLaunchArgument(
            'ekf', default_value='true',
            description='Run the EKF (odometry + gyro); false: use the raw odometry'),
        DeclareLaunchArgument(
            'odometry', default_value='encoders', choices=['encoders', 'lidar'],
            description="The EKF's speed source: encoders (DiffDrive) or lidar"),
        gazebo,
        robot_description,
        spawn,
        bridge,
        ekf,
        odom_tf_bridge,
    ])
