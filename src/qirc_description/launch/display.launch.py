"""
View the robot model in RViz.

    ros2 launch qirc_description display.launch.py

Starts robot_state_publisher (description.launch.py) and RViz with
rviz/display.rviz (robot model + TF frames, fixed frame base_link).
No hardware or simulation needed.
"""

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    package = FindPackageShare('qirc_description')

    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([package, 'launch', 'description.launch.py'])),
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', PathJoinSubstitution([package, 'rviz', 'display.rviz'])],
            output='screen',
        ),
    ])
