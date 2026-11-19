"""
Launch the QIRC simulation in Gazebo Fortress.

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

    return LaunchDescription([
        DeclareLaunchArgument(
            'world', default_value='obstacles.sdf',
            description='World file in qirc_gazebo/worlds'),
        DeclareLaunchArgument(
            'headless', default_value='false',
            description='Run the Gazebo server only, without the GUI'),
        gazebo,
    ])
