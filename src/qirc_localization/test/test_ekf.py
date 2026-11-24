"""Check the EKF configuration and launch file, and the gyro bias estimate."""

import importlib.util
from pathlib import Path

from launch import LaunchDescription
from launch_ros.actions import Node
import numpy as np
import pytest
from qirc_localization.imu_bias import GyroBias
import yaml

PACKAGE_DIR = Path(__file__).resolve().parents[1]

# Index of each variable in a robot_localization *_config list.
STATE = ['x', 'y', 'z', 'roll', 'pitch', 'yaw',
         'vx', 'vy', 'vz', 'vroll', 'vpitch', 'vyaw',
         'ax', 'ay', 'az']


@pytest.fixture(scope='module')
def ekf():
    config = yaml.safe_load((PACKAGE_DIR / 'config' / 'ekf.yaml').read_text())
    return config['ekf_filter_node']['ros__parameters']


def _fused(config):
    assert len(config) == len(STATE)
    return {name for name, used in zip(STATE, config) if used}


def test_ekf_frames(ekf):
    # REP 105: the EKF publishes odom -> base_link; slam_toolbox map -> odom.
    assert ekf['world_frame'] == ekf['odom_frame'] == 'odom'
    assert ekf['base_link_frame'] == 'base_link'
    assert ekf['map_frame'] == 'map'
    assert ekf['publish_tf'] is True
    assert ekf['two_d_mode'] is True


def test_ekf_takes_speed_from_odometry_and_turns_from_gyro(ekf):
    # Track odometry's turn rate is wrong when the tracks skid, so turns come
    # from the gyro only; odometry gives forward (and zero sideways) speed.
    assert ekf['odom0'] == '/odom'
    assert _fused(ekf['odom0_config']) == {'vx', 'vy'}
    # The gyro after imu_bias has removed its bias. The config is in the
    # IMU's optical frame, so all three rates: the EKF rotates them into
    # base_link and keeps only the yaw rate in 2D mode.
    assert ekf['imu0'] == '/front_camera/imu/unbiased'
    assert _fused(ekf['imu0_config']) == {'vroll', 'vpitch', 'vyaw'}


def test_launch_starts_imu_bias_and_ekf():
    path = PACKAGE_DIR / 'launch' / 'ekf.launch.py'
    spec = importlib.util.spec_from_file_location('ekf_launch', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    description = module.generate_launch_description()
    assert isinstance(description, LaunchDescription)
    nodes = {e.node_executable for e in description.entities if isinstance(e, Node)}
    # laser_odometry only runs with odometry:=lidar (a launch condition).
    assert nodes == {'imu_bias', 'ekf_node', 'laser_odometry'}


def test_gyro_bias_starts_unknown_at_zero():
    bias = GyroBias(averaging_samples=100)
    assert not bias.known
    assert np.allclose(bias.bias, 0.0)


def test_gyro_bias_is_the_mean_of_still_readings():
    rng = np.random.default_rng(0)
    true_bias = np.array([0.002, -0.009, 0.004])
    bias = GyroBias(averaging_samples=2000)
    for _ in range(1000):
        bias.add(true_bias + rng.normal(0.0, 0.0024, 3))
    assert bias.known
    # 1000 samples of 0.0024 rad/s noise: within ~4 standard errors.
    assert np.allclose(bias.bias, true_bias, atol=4 * 0.0024 / np.sqrt(1000))


def test_gyro_bias_follows_a_change():
    # An exponential average after averaging_samples, so a bias that drifts
    # (with temperature) is followed.
    bias = GyroBias(averaging_samples=100)
    for _ in range(100):
        bias.add([0.0, 0.0, 0.01])
    for _ in range(500):
        bias.add([0.0, 0.0, 0.02])
    assert bias.bias[2] == pytest.approx(0.02, abs=1e-4)
