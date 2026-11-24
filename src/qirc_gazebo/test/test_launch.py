"""Check the simulation launch file, worlds and bridge configuration."""

import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch_ros.actions import Node
import pytest
import xacro
import yaml

PACKAGE_DIR = Path(__file__).resolve().parents[1]
WORLDS = sorted((PACKAGE_DIR / 'worlds').glob('*.sdf'))
BRIDGE_FILES = ('bridge.yaml',)


def _load(name):
    path = PACKAGE_DIR / 'launch' / name
    spec = importlib.util.spec_from_file_location(path.stem.replace('.', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    description = module.generate_launch_description()
    assert isinstance(description, LaunchDescription)
    return description.entities


def test_sim_launch_loads_and_includes_gazebo():
    entities = _load('sim.launch.py')
    assert any(isinstance(e, IncludeLaunchDescription) for e in entities)


def test_default_world_exists():
    entities = _load('sim.launch.py')
    world = next(e for e in entities
                 if isinstance(e, DeclareLaunchArgument) and e.name == 'world')
    assert (PACKAGE_DIR / 'worlds' / world.default_value[0].text).is_file()


@pytest.mark.parametrize('world', WORLDS, ids=lambda p: p.name)
def test_world_has_required_systems(world):
    root = ET.parse(world).getroot()
    plugins = {p.get('name') for p in root.findall('world/plugin')}
    # Imu: the D435i's IMU publishes nothing without it.
    for system in ('Physics', 'UserCommands', 'SceneBroadcaster', 'Sensors', 'Imu'):
        assert f'ignition::gazebo::systems::{system}' in plugins, f'{world.name}: no {system}'
    sensors = next(p for p in root.findall('world/plugin') if p.get('name').endswith('Sensors'))
    # The GPU LiDAR only works with ogre2.
    assert sensors.findtext('render_engine') == 'ogre2'
    models = {m.get('name') for m in root.findall('world/model')}
    assert 'ground_plane' in models


def _bridge(name):
    return yaml.safe_load((PACKAGE_DIR / 'config' / name).read_text())


def test_launch_starts_one_bridge():
    bridges = [e for e in _load('sim.launch.py')
               if isinstance(e, Node) and e.node_executable == 'parameter_bridge']
    assert len(bridges) == len(BRIDGE_FILES)
    assert all(b.condition is None for b in bridges)


def test_ekf_always_publishes_odom_tf():
    # No drive encoders, so no wheel-odometry fallback: the EKF (on LiDAR
    # odometry) always runs and is the only source of odom -> base_link.
    entities = _load('sim.launch.py')
    arguments = {e.name for e in entities if isinstance(e, DeclareLaunchArgument)}
    assert arguments == {'world', 'headless'}
    ekf = [e for e in entities if isinstance(e, IncludeLaunchDescription)
           and 'ekf.launch.py' in e.launch_description_source.location]
    assert len(ekf) == 1 and ekf[0].condition is None


@pytest.mark.parametrize('name', BRIDGE_FILES)
def test_bridge_entries_are_complete(name):
    for entry in _bridge(name):
        assert {'ros_topic_name', 'gz_topic_name', 'ros_type_name',
                'gz_type_name', 'direction'} <= set(entry), entry
        assert entry['direction'] in ('GZ_TO_ROS', 'ROS_TO_GZ', 'BIDIRECTIONAL')
        assert entry['gz_type_name'].startswith('ignition.msgs.')


def test_bridged_ros_topics():
    topics = {e['ros_topic_name']: e['direction']
              for name in BRIDGE_FILES for e in _bridge(name)}
    assert topics == {
        '/clock': 'GZ_TO_ROS',
        '/cmd_vel': 'ROS_TO_GZ',
        '/joint_states': 'GZ_TO_ROS',
        '/scan': 'GZ_TO_ROS',
        # The D435i, under realsense2_camera's names.
        '/front_camera/color/image_raw': 'GZ_TO_ROS',
        '/front_camera/color/camera_info': 'GZ_TO_ROS',
        '/front_camera/aligned_depth_to_color/image_raw': 'GZ_TO_ROS',
        '/front_camera/aligned_depth_to_color/camera_info': 'GZ_TO_ROS',
        '/front_camera/imu': 'GZ_TO_ROS',
        # The true pose, for measuring localization error.
        '/ground_truth': 'GZ_TO_ROS',
    }


def test_no_wheel_odometry_bridged():
    topics = {e['ros_topic_name'] for e in _bridge('bridge.yaml')}
    assert '/odom' not in topics and '/tf' not in topics


def test_every_robot_gazebo_topic_is_bridged():
    # The Gazebo topics set in the robot's plugins and sensors must match
    # the bridge, or the topic silently never reaches ROS.
    urdf = Path(get_package_share_directory('qirc_description')) / 'urdf' / 'qirc.urdf.xacro'
    robot = ET.fromstring(
        xacro.process_file(str(urdf), mappings={'sim': 'true'}).toxml())
    robot_topics = set()
    for plugin in robot.iter('plugin'):
        for tag in ('topic', 'odom_topic', 'tf_topic'):
            if plugin.findtext(tag):
                robot_topics.add(plugin.findtext(tag))
    for sensor in robot.iter('sensor'):
        topic = sensor.findtext('topic')
        if sensor.get('type') == 'rgbd_camera':
            # An RGB-D camera publishes several topics under its own.
            robot_topics |= {f'{topic}/image', f'{topic}/depth_image', f'{topic}/camera_info'}
        else:
            robot_topics.add(topic)
    bridged = {e['gz_topic_name'] for name in BRIDGE_FILES for e in _bridge(name)}
    assert robot_topics <= bridged
