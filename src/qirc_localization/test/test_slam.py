"""Check the slam_toolbox configuration, launch files, RViz config and save_map."""

import importlib.util
import os
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, UnsetEnvironmentVariable
from launch_ros.actions import Node
import pytest
from qirc_localization.save_map import DEFAULT_MAP, map_path
import yaml

PACKAGE_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def params():
    config = yaml.safe_load((PACKAGE_DIR / 'config' / 'mapper_params.yaml').read_text())
    # The launch file names the node slam_toolbox, so the file must use that name.
    return config['slam_toolbox']['ros__parameters']


@pytest.fixture(scope='module')
def localization_params():
    config = yaml.safe_load(
        (PACKAGE_DIR / 'config' / 'localization_params.yaml').read_text())
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


def test_laser_range_matches_a2m8(params):
    # The A2M8 (and the simulated one) reads 0.15-12 m. min_laser_range must
    # be above 0.15 or slam_toolbox warns on every start.
    assert 0.15 < params['min_laser_range'] <= 0.3
    assert params['max_laser_range'] == 12.0


def test_launch_starts_slam_toolbox_and_optional_rviz():
    entities = _load('mapping.launch.py')
    nodes = {e.node_executable: e for e in entities if isinstance(e, Node)}
    assert set(nodes) == {'async_slam_toolbox_node', 'rviz2'}
    assert nodes['async_slam_toolbox_node'].condition is None
    assert nodes['rviz2'].condition is not None
    arguments = {e.name: e.default_value[0].text for e in entities
                 if isinstance(e, DeclareLaunchArgument)}
    assert arguments == {'use_sim_time': 'false', 'rviz': 'false'}


@pytest.mark.parametrize('name', ['mapping.launch.py', 'localization.launch.py'])
def test_launch_unsets_snap_common(name):
    # Otherwise slam_toolbox saves and loads maps under $SNAP_COMMON.
    entities = _load(name)
    unset = [e for e in entities if isinstance(e, UnsetEnvironmentVariable)]
    assert [e.name[0].text for e in unset] == ['SNAP_COMMON']
    first_node = next(i for i, e in enumerate(entities) if isinstance(e, Node))
    assert entities.index(unset[0]) < first_node


def test_localization_params(localization_params):
    assert localization_params['mode'] == 'localization'
    # Start at the map origin, where mapping started. (Localization mode
    # ignores map_start_at_dock.)
    assert localization_params['map_start_pose'] == [0.0, 0.0, 0.0]
    assert 'map_start_at_dock' not in localization_params
    # The launch file sets the map; a fixed one here would hide its argument.
    assert 'map_file_name' not in localization_params


def test_localization_launch_loads_saved_map():
    entities = _load('localization.launch.py')
    nodes = {e.node_executable: e for e in entities if isinstance(e, Node)}
    assert set(nodes) == {'localization_slam_toolbox_node', 'rviz2'}
    assert nodes['rviz2'].condition is not None
    arguments = {e.name: e.default_value[0].text for e in entities
                 if isinstance(e, DeclareLaunchArgument)}
    assert arguments == {
        'map': os.path.expanduser(DEFAULT_MAP),
        'use_sim_time': 'false',
        'rviz': 'false',
    }


def test_map_path_is_absolute_without_extension(tmp_path, monkeypatch):
    # slam_toolbox runs in another directory, so the path must be absolute.
    monkeypatch.chdir(tmp_path)
    assert map_path('lab') == tmp_path.resolve() / 'lab'
    assert map_path('lab.posegraph') == tmp_path.resolve() / 'lab'
    home = Path(os.path.expanduser('~')).resolve()
    assert map_path('~/qirc_maps/house') == home / 'qirc_maps' / 'house'


def test_rviz_config_shows_map_in_map_frame():
    config = yaml.safe_load((PACKAGE_DIR / 'rviz' / 'slam.rviz').read_text())
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
    # "2D Pose Estimate", to tell localization mode where the robot is.
    tools = {t['Class'] for t in config['Visualization Manager']['Tools']}
    assert 'rviz_default_plugins/SetInitialPose' in tools
