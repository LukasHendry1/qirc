"""Check that the launch files load and the RViz config is valid."""

import importlib.util
from pathlib import Path

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch_ros.actions import Node
import yaml

PACKAGE_DIR = Path(__file__).resolve().parents[1]


def _load(name):
    path = PACKAGE_DIR / 'launch' / name
    spec = importlib.util.spec_from_file_location(path.stem.replace('.', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    description = module.generate_launch_description()
    assert isinstance(description, LaunchDescription)
    return description.entities


def _node_executables(entities):
    return {e.node_executable for e in entities if isinstance(e, Node)}


def test_description_launch_starts_robot_state_publisher():
    assert _node_executables(_load('description.launch.py')) == {'robot_state_publisher'}


def test_display_launch_starts_rviz_and_includes_description():
    entities = _load('display.launch.py')
    assert _node_executables(entities) == {'rviz2'}
    assert any(isinstance(e, IncludeLaunchDescription) for e in entities)


def test_rviz_config_shows_robot_model_in_base_link():
    config = yaml.safe_load((PACKAGE_DIR / 'rviz' / 'display.rviz').read_text())
    manager = config['Visualization Manager']
    assert manager['Global Options']['Fixed Frame'] == 'base_link'
    displays = {d['Class']: d for d in manager['Displays']}
    model = displays['rviz_default_plugins/RobotModel']
    assert model['Description Topic']['Value'] == '/robot_description'
    # robot_state_publisher publishes /robot_description as transient local;
    # RViz must match or it never receives the model.
    assert model['Description Topic']['Durability Policy'] == 'Transient Local'
    assert 'rviz_default_plugins/TF' in displays
