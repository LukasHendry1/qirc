"""Check which parts of the stack qirc.launch.py starts, on hardware and in simulation."""

import importlib.util
from pathlib import Path

from launch import LaunchContext, LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch_ros.actions import Node
import pytest

LAUNCH_FILE = Path(__file__).resolve().parents[1] / 'launch' / 'qirc.launch.py'
DRIVERS = {'front_camera.launch.py', 'rear_camera.launch.py', 'lidar.launch.py'}


@pytest.fixture(scope='module')
def entities():
    spec = importlib.util.spec_from_file_location('qirc_launch', LAUNCH_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    description = module.generate_launch_description()
    assert isinstance(description, LaunchDescription)
    return description.entities


def _started(entities, **arguments):
    """Return the launch files and executables started with these arguments."""
    context = LaunchContext()
    for entity in entities:
        if isinstance(entity, DeclareLaunchArgument):
            context.launch_configurations[entity.name] = entity.default_value[0].text
    context.launch_configurations.update(arguments)
    started = set()
    for entity in entities:
        if isinstance(entity, DeclareLaunchArgument):
            continue
        if entity.condition is not None and not entity.condition.evaluate(context):
            continue
        if isinstance(entity, IncludeLaunchDescription):
            location = entity.launch_description_source.location
            started.add(next(name for name in location.split("'") if name.endswith('.py')))
        elif isinstance(entity, Node):
            started.add(entity.node_executable)
    return started


def test_default_is_the_real_robot(entities):
    started = _started(entities)
    assert 'description.launch.py' in started
    assert DRIVERS <= started
    assert 'rear_detection_node' in started
    assert 'sim.launch.py' not in started


def test_use_sim_swaps_hardware_for_simulation(entities):
    started = _started(entities, use_sim='true')
    assert 'sim.launch.py' in started
    # The simulation publishes the robot model and replaces every driver.
    assert 'description.launch.py' not in started
    assert not DRIVERS & started
    # No simulated rear camera.
    assert 'rear_detection_node' not in started


def test_use_sim_ignores_the_driver_flags(entities):
    started = _started(entities, use_sim='true', use_front_camera='true',
                       use_rear_camera='true', use_lidar='true')
    assert not DRIVERS & started


@pytest.mark.parametrize('flag, driver', [
    ('use_front_camera', 'front_camera.launch.py'),
    ('use_rear_camera', 'rear_camera.launch.py'),
    ('use_lidar', 'lidar.launch.py'),
])
def test_each_driver_can_be_turned_off(entities, flag, driver):
    assert driver not in _started(entities, **{flag: 'false'})
    assert driver in _started(entities, **{flag: 'true'})


@pytest.mark.parametrize('use_sim', ['false', 'true'])
def test_rest_of_stack_runs_on_both(entities, use_sim):
    started = _started(entities, use_sim=use_sim)
    assert {'front_detection_node', 'vehicle_manager_node', 'global_planner_node',
            'local_planner_node', 'pill_box_node', 'arm_node'} <= started


def test_simulation_arguments_are_passed_on(entities):
    simulation = next(e for e in entities if isinstance(e, IncludeLaunchDescription)
                      and 'sim.launch.py' in e.launch_description_source.location)
    names = {name[0].text if isinstance(name, list) else name
             for name, _ in simulation.launch_arguments}
    assert names == {'world', 'headless'}
