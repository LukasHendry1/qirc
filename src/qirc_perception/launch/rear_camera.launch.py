"""
Launch the Luxonis depthai driver for the rear OAK-D Lite camera.

Topics are published under /rear_camera/, e.g.:
    /rear_camera/rgb/image_raw
    /rear_camera/rgb/camera_info
    /rear_camera/stereo/image_raw
    /rear_camera/nn/spatial_detections
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    driver_launch = os.path.join(
        get_package_share_directory('depthai_ros_driver'), 'launch', 'camera.launch.py')
    params_file = os.path.join(
        get_package_share_directory('qirc_perception'), 'config', 'rear_camera.yaml')

    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(driver_launch),
            launch_arguments={
                'name': 'rear_camera',
                'camera_model': 'OAK-D-LITE',
                'params_file': params_file,
                # TODO: once qirc_description has a URDF, set the camera's
                # mounting pose relative to base_link (cam_pos_*, cam_yaw=pi).
                'parent_frame': 'base_link',
            }.items(),
        ),
    ])
