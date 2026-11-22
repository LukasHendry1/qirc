"""
Build a map of the house with slam_toolbox (online async, mapping mode).

    # Simulation (with sim.launch.py from qirc_gazebo running):
    ros2 launch qirc_localization mapping.launch.py use_sim_time:=true rviz:=true

Save the map while this is running with `ros2 run qirc_localization save_map`
(see save_map.py), then localize in it with localization.launch.py.

Needs /scan and the odom -> base_link transform. Publishes /map and the
map -> odom transform. Parameters are in config/mapper_params.yaml.

Launch arguments:
    use_sim_time (default false): use the simulation clock (/clock).
    rviz (default false): also start RViz with rviz/slam.rviz
        (map, scan, robot model, fixed frame map).
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, UnsetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    package = FindPackageShare('qirc_localization')
    use_sim_time = ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool)

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time', default_value='false',
            description='Use the simulation clock (/clock)'),
        DeclareLaunchArgument(
            'rviz', default_value='false',
            description='Also start RViz showing the map'),
        # slam_toolbox puts $SNAP_COMMON in front of map paths when it is set,
        # assuming it runs as a snap. Terminals in snap apps (e.g. VS Code)
        # export it too, which breaks saving and loading maps.
        UnsetEnvironmentVariable('SNAP_COMMON'),
        Node(
            package='slam_toolbox',
            executable='async_slam_toolbox_node',
            name='slam_toolbox',
            parameters=[
                PathJoinSubstitution([package, 'config', 'mapper_params.yaml']),
                {'use_sim_time': use_sim_time},
            ],
            output='screen',
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', PathJoinSubstitution([package, 'rviz', 'slam.rviz'])],
            parameters=[{'use_sim_time': use_sim_time}],
            condition=IfCondition(LaunchConfiguration('rviz')),
            output='screen',
        ),
    ])
