"""
Launch the Slamtec RPLidar driver.

Publishes sensor_msgs/LaserScan on /scan (frame: laser).

Launch arguments:
    serial_port (default /dev/rplidar): needs udev/99-rplidar.rules installed;
        otherwise use e.g. serial_port:=/dev/ttyUSB0.
    serial_baudrate (default 115200): depends on the RPLidar model:
        A1, A2M8 ................ 115200
        A2M7, A2M12, A3, S1 ..... 256000
        C1 ...................... 460800
        S2, S3 .................. 1000000
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    params_file = os.path.join(
        get_package_share_directory('qirc_localization'), 'config', 'lidar.yaml')

    return LaunchDescription([
        DeclareLaunchArgument(
            'serial_port', default_value='/dev/rplidar',
            description='Serial port of the RPLidar'),
        DeclareLaunchArgument(
            'serial_baudrate', default_value='115200',
            description='RPLidar baud rate (model dependent, see file docstring)'),
        Node(
            package='rplidar_ros',
            executable='rplidar_node',
            name='rplidar',
            parameters=[
                params_file,
                {
                    'serial_port': LaunchConfiguration('serial_port'),
                    'serial_baudrate': ParameterValue(
                        LaunchConfiguration('serial_baudrate'), value_type=int),
                },
            ],
            output='screen',
        ),
    ])
