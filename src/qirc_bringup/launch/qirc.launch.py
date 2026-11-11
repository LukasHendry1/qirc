"""
Launch the full QIRC software stack.

Arguments:
    use_front_camera (default true): start the front RealSense driver.
        Set to false when developing without the camera plugged in.
    use_rear_camera (default true): start the rear OAK-D Lite driver.
        Set to false when developing without the camera plugged in.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

NODES = [
    ('qirc_perception', 'object_detection_node'),
    ('qirc_localization', 'mapping_node'),
    ('qirc_localization', 'localization_node'),
    ('qirc_planning', 'vehicle_manager_node'),
    ('qirc_planning', 'global_planner_node'),
    ('qirc_planning', 'local_planner_node'),
    ('qirc_control', 'control_node'),
    ('qirc_pill_dispenser', 'pill_box_node'),
    ('qirc_pill_dispenser', 'arm_node'),
]


def generate_launch_description():
    front_camera = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('qirc_perception'), 'launch', 'front_camera.launch.py',
        ])),
        condition=IfCondition(LaunchConfiguration('use_front_camera')),
    )
    rear_camera = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('qirc_perception'), 'launch', 'rear_camera.launch.py',
        ])),
        condition=IfCondition(LaunchConfiguration('use_rear_camera')),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_front_camera', default_value='true',
            description='Start the front RealSense driver (false if no camera attached)'),
        DeclareLaunchArgument(
            'use_rear_camera', default_value='true',
            description='Start the rear OAK-D Lite driver (false if no camera attached)'),
        front_camera,
        rear_camera,
        *[Node(package=pkg, executable=exe, output='screen') for pkg, exe in NODES],
    ])
