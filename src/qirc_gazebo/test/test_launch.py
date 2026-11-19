"""Check that the simulation launch file loads and the worlds are valid."""

import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
import pytest

PACKAGE_DIR = Path(__file__).resolve().parents[1]
WORLDS = sorted((PACKAGE_DIR / 'worlds').glob('*.sdf'))


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
    for system in ('Physics', 'UserCommands', 'SceneBroadcaster', 'Sensors'):
        assert f'ignition::gazebo::systems::{system}' in plugins, f'{world.name}: no {system}'
    sensors = next(p for p in root.findall('world/plugin') if p.get('name').endswith('Sensors'))
    # The GPU LiDAR only works with ogre2.
    assert sensors.findtext('render_engine') == 'ogre2'
    models = {m.get('name') for m in root.findall('world/model')}
    assert 'ground_plane' in models
