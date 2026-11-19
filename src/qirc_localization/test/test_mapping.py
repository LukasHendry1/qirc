"""Check the slam_toolbox mapping configuration, launch file and RViz config."""

import importlib.util
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node
import pytest
import yaml

PACKAGE_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def params():
    config = yaml.safe_load((PACKAGE_DIR / 'config' / 'mapper_params.yaml').read_text())
    # The launch file names the node slam_toolbox, so the file must use that name.
    return config['slam_toolbox']['ros__parameters']


def _load(name):
    path = PACKAGE_DIR / 'launch' / name
    spec = importlib.util.spec_from_file_location(path.stem.replace('.', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    description = module.generate_launch_description()
    assert isinstance(description, LaunchDescription)
    return description.entities


def test_frames_and_topics(params):
    # REP 105 frame names, as used by the URDF, the EKF and Gazebo's DiffDrive.
    assert params['mode'] == 'mapping'
    assert params['map_frame'] == 'map'
    assert params['odom_frame'] == 'odom'
    assert params['base_frame'] == 'base_link'
    assert params['scan_topic'] == '/scan'


def test_laser_range_within_a2m8(params):
    # The A2M8 (and the simulated one) reads up to 12 m.
    assert 0 < params['max_laser_range'] <= 12.0


def test_turn_threshold_within_scan_matcher_search(params):
    # Track odometry overestimates turns by about 1.4x. The heading error
    # between two scans must stay inside the scan matcher's angular search
    # window, or the match fails.
    window = params.get('coarse_search_angle_offset', 0.349)
    assert 0.4 * params['minimum_travel_heading'] < window


def test_launch_starts_slam_toolbox_and_optional_rviz():
    entities = _load('mapping.launch.py')
    nodes = {e.node_executable: e for e in entities if isinstance(e, Node)}
    assert set(nodes) == {'async_slam_toolbox_node', 'rviz2'}
    assert nodes['async_slam_toolbox_node'].condition is None
    assert nodes['rviz2'].condition is not None
    arguments = {e.name: e.default_value[0].text for e in entities
                 if isinstance(e, DeclareLaunchArgument)}
    assert arguments == {'use_sim_time': 'false', 'rviz': 'false'}


def test_rviz_config_shows_map_in_map_frame():
    config = yaml.safe_load((PACKAGE_DIR / 'rviz' / 'mapping.rviz').read_text())
    manager = config['Visualization Manager']
    assert manager['Global Options']['Fixed Frame'] == 'map'
    displays = {d['Class']: d for d in manager['Displays']}
    # slam_toolbox publishes /map as transient local; RViz must match or it
    # only sees the map after the next update.
    topic = displays['rviz_default_plugins/Map']['Topic']
    assert topic['Value'] == '/map'
    assert topic['Durability Policy'] == 'Transient Local'
    # rplidar_ros publishes /scan best effort (sensor data QoS); a best effort
    # subscriber receives it, and the Gazebo bridge's reliable /scan too.
    scan = displays['rviz_default_plugins/LaserScan']['Topic']
    assert scan['Value'] == '/scan'
    assert scan['Reliability Policy'] == 'Best Effort'
    assert 'rviz_default_plugins/RobotModel' in displays
