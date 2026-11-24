"""
Launch the QIRC simulation in Gazebo Fortress.

Starts Gazebo with a world, publishes the robot model (with its Gazebo parts,
sim:=true) from robot_state_publisher on simulation time, spawns the robot
from /robot_description, and bridges the topics in config/ between Gazebo
and ROS.

Also starts qirc_localization's EKF (ekf.launch.py): LiDAR odometry and the
simulated D435i's gyro, which publishes odom -> base_link. As on the real
robot, there are no drive encoders: DiffDrive only moves the robot, and its
wheel odometry isn't bridged.

Also publishes the robot's true pose (/ground_truth, nav_msgs/Odometry in
the world frame) for measuring localization error.

Arguments:
    world (default obstacles.sdf): world file in qirc_gazebo/worlds.
        obstacles.sdf has a few walls and boxes for the LiDAR to see;
        empty.sdf is just the ground.
    headless (default false): run the Gazebo server only, without the GUI.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
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

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='gz_bridge',
        parameters=[{
            'config_file': PathJoinSubstitution([
                FindPackageShare('qirc_gazebo'), 'config', 'bridge.yaml']),
            'use_sim_time': True,
        }],
        output='screen',
    )
    # The only source of odom -> base_link.
    ekf = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('qirc_localization'), 'launch', 'ekf.launch.py',
        ])),
        launch_arguments={'use_sim_time': 'true'}.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'world', default_value='obstacles.sdf',
            description='World file in qirc_gazebo/worlds'),
        DeclareLaunchArgument(
            'headless', default_value='false',
            description='Run the Gazebo server only, without the GUI'),
        gazebo,
        robot_description,
        spawn,
        bridge,
        ekf,
    ])
