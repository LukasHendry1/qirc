"""
Localize in a saved map with slam_toolbox (localization mode).

    # Simulation (with sim.launch.py from qirc_gazebo running):
    ros2 launch qirc_localization localization.launch.py use_sim_time:=true rviz:=true

The map is saved while mapping with `ros2 run qirc_localization save_map`.
The robot is expected to start where mapping started; if it is somewhere
else, set its pose with RViz's "2D Pose Estimate" tool (/initialpose).

Needs /scan and the odom -> base_link transform. Publishes /map (the saved
map) and the map -> odom transform. Parameters are config/mapper_params.yaml
with config/localization_params.yaml on top.

Launch arguments:
    map (default ~/qirc_maps/house): the saved map, without an extension
        (the path given to save_map).
    use_sim_time (default false): use the simulation clock (/clock).
    rviz (default false): also start RViz with rviz/slam.rviz.
"""

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, UnsetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

# Also qirc_localization.save_map.DEFAULT_MAP.
DEFAULT_MAP = os.path.expanduser('~/qirc_maps/house')


def generate_launch_description():
    package = FindPackageShare('qirc_localization')
    use_sim_time = ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool)

    return LaunchDescription([
        DeclareLaunchArgument(
            'map', default_value=DEFAULT_MAP,
            description='Saved map to localize in, without an extension'),
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
            executable='localization_slam_toolbox_node',
            name='slam_toolbox',
            parameters=[
                PathJoinSubstitution([package, 'config', 'mapper_params.yaml']),
                PathJoinSubstitution([package, 'config', 'localization_params.yaml']),
                {
                    'map_file_name': LaunchConfiguration('map'),
                    'use_sim_time': use_sim_time,
                },
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
