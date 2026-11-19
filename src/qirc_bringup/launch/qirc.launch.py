"""
Launch the full QIRC software stack.

Always starts robot_state_publisher (the robot model and its static TF, from
qirc_description), so every sensor frame connects to base_link.

Arguments:
    use_front_camera (default true): start the front RealSense driver.
        Set to false when developing without the camera plugged in.
    use_rear_camera (default true): start the rear OAK-D Lite driver.
        Set to false when developing without the camera plugged in.
    use_lidar (default true): start the RPLidar driver.
        Set to false when developing without the LiDAR plugged in.
    use_front_detection (default true): run YOLO on the front camera.
        Needs Ultralytics (src/qirc_perception/README.md); set to false if
        it isn't installed.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

NODES = [
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
    robot_description = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('qirc_description'), 'launch', 'description.launch.py',
        ])),
    )
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
    lidar = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('qirc_localization'), 'launch', 'lidar.launch.py',
        ])),
        condition=IfCondition(LaunchConfiguration('use_lidar')),
    )
    front_detection = Node(
        package='qirc_perception',
        executable='front_detection_node',
        parameters=[PathJoinSubstitution([
            FindPackageShare('qirc_perception'), 'config', 'front_detection.yaml',
        ])],
        output='screen',
        condition=IfCondition(LaunchConfiguration('use_front_detection')),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_front_camera', default_value='true',
            description='Start the front RealSense driver (false if no camera attached)'),
        DeclareLaunchArgument(
            'use_rear_camera', default_value='true',
            description='Start the rear OAK-D Lite driver (false if no camera attached)'),
        DeclareLaunchArgument(
            'use_lidar', default_value='true',
            description='Start the RPLidar driver (false if no LiDAR attached)'),
        DeclareLaunchArgument(
            'use_front_detection', default_value='true',
            description='Run YOLO on the front camera (needs Ultralytics installed)'),
        robot_description,
        front_camera,
        rear_camera,
        lidar,
        front_detection,
        *[Node(package=pkg, executable=exe, output='screen') for pkg, exe in NODES],
    ])
