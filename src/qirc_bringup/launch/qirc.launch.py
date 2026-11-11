"""Launch the full QIRC software stack."""

from launch import LaunchDescription
from launch_ros.actions import Node

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
    return LaunchDescription([
        Node(package=pkg, executable=exe, output='screen')
        for pkg, exe in NODES
    ])
