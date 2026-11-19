"""
Publish the robot model: robot_state_publisher with the QIRC URDF.

Publishes /robot_description and the static TF from base_link to the chassis,
track and sensor frames. Included by qirc_bringup's qirc.launch.py and by
display.launch.py.

Arguments:
    use_sim_time (default false): use the simulation clock (/clock).
    sim (default false): build the model with its Gazebo parts (road wheels,
        DiffDrive, LiDAR sensor); see urdf/gazebo.urdf.xacro.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    urdf_file = PathJoinSubstitution([
        FindPackageShare('qirc_description'), 'urdf', 'qirc.urdf.xacro',
    ])
    robot_description = ParameterValue(
        Command(['xacro ', urdf_file, ' sim:=', LaunchConfiguration('sim')]),
        value_type=str)

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time', default_value='false',
            description='Use the simulation clock (/clock)'),
        DeclareLaunchArgument(
            'sim', default_value='false',
            description='Include the Gazebo parts of the model'),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            parameters=[{
                'robot_description': robot_description,
                'use_sim_time': ParameterValue(
                    LaunchConfiguration('use_sim_time'), value_type=bool),
            }],
            output='screen',
        ),
    ])
