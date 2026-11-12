"""
Launch the Intel RealSense driver for the front D435i camera.

Topics are published under /front_camera/, e.g.:
    /front_camera/color/image_raw
    /front_camera/color/camera_info
    /front_camera/depth/image_rect_raw
    /front_camera/aligned_depth_to_color/image_raw
    /front_camera/imu                 (gyro + accel, sensor_msgs/Imu)

The driver node is started directly (rather than through realsense2_camera's
rs_launch.py) so it does not warn about our own launch arguments.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    params_file = os.path.join(
        get_package_share_directory('qirc_perception'), 'config', 'front_camera.yaml')

    return LaunchDescription([
        Node(
            package='realsense2_camera',
            executable='realsense2_camera_node',
            name='front_camera',
            namespace='',
            parameters=[params_file],
            output='screen',
            emulate_tty=True,
            # TODO: once qirc_description has a URDF, attach front_camera_link
            # to base_link at the camera's mounting pose.
        ),
    ])
