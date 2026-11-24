"""Check the LiDAR odometry's scan matching and the odometry test's error maths."""

import math
from pathlib import Path

import numpy as np
import pytest
from qirc_localization.laser_odometry import (
    degenerate, Keyframe, match, pose_of, scan_points, se2)
from qirc_localization.odometry_test import errors, relative_pose
import yaml

PACKAGE_DIR = Path(__file__).resolve().parents[1]

ROOM = [((-3, -2), (4, -2)), ((4, -2), (4, 3)), ((4, 3), (-3, 3)), ((-3, 3), (-3, -2)),
        # a box in the room
        ((1, 0.5), (1.5, 0.5)), ((1.5, 0.5), (1.5, 1.2)),
        ((1.5, 1.2), (1, 1.2)), ((1, 1.2), (1, 0.5))]
CORRIDOR = [((-30, -1), (30, -1)), ((-30, 1), (30, 1))]


def simulate_scan(walls, x, y, theta, samples=800, noise=0.01, seed=0):
    """Raycast a 360 degree scan from pose (x, y, theta) against wall segments."""
    rng = np.random.default_rng(seed)
    angles = -math.pi + 2 * math.pi * np.arange(samples) / samples
    ranges = np.full(samples, np.inf)
    for i, angle in enumerate(angles):
        dx, dy = math.cos(angle + theta), math.sin(angle + theta)
        for (x1, y1), (x2, y2) in walls:
            ex, ey = x2 - x1, y2 - y1
            den = -dx * ey + dy * ex
            if abs(den) < 1e-12:
                continue
            t = (-(x1 - x) * ey + (y1 - y) * ex) / den
            u = (dx * (y1 - y) - dy * (x1 - x)) / den
            if t > 0 and 0 <= u <= 1:
                ranges[i] = min(ranges[i], t)
    ranges += rng.normal(0, noise, samples)
    return scan_points(ranges, angles[0], angles[1] - angles[0], 0.15, 12.0)


def test_scan_points_drops_invalid_ranges():
    points = scan_points([1.0, np.inf, 0.05, 20.0, np.nan, 2.0], 0.0, math.pi / 2, 0.15, 12.0)
    np.testing.assert_allclose(points, [[1.0, 0.0], [0.0, 2.0]], atol=1e-12)


@pytest.mark.parametrize('motion', [(0.1, 0.02, 0.05), (0.3, -0.1, 0.2), (0.0, 0.0, 0.0)])
def test_match_recovers_motion_in_a_room(motion):
    keyframe = Keyframe(simulate_scan(ROOM, 0, 0, 0))
    result = match(simulate_scan(ROOM, *motion, seed=1), keyframe, np.eye(3))
    assert result is not None
    transform, information, inliers = result
    x, y, theta = pose_of(transform)
    assert x == pytest.approx(motion[0], abs=0.01)
    assert y == pytest.approx(motion[1], abs=0.01)
    assert theta == pytest.approx(motion[2], abs=0.005)
    assert inliers > 0.9
    assert not degenerate(information)


def test_match_flags_a_bare_corridor():
    # Moving along parallel walls looks the same: the match can't tell how
    # far, and must say so.
    keyframe = Keyframe(simulate_scan(CORRIDOR, 0, 0, 0))
    result = match(simulate_scan(CORRIDOR, 0.2, 0, 0, seed=1), keyframe, np.eye(3))
    assert result is not None
    assert degenerate(result[1])


def test_se2_round_trip():
    assert pose_of(se2(1.0, -2.0, 0.5)) == pytest.approx((1.0, -2.0, 0.5))
    composed = se2(1, 0, math.pi / 2) @ se2(1, 0, 0)
    assert pose_of(composed) == pytest.approx((1.0, 1.0, math.pi / 2))


def test_relative_pose_and_errors():
    start = (1.0, 1.0, math.pi / 2)
    # One metre ahead of the start, in the start's frame.
    assert relative_pose(start, (1.0, 2.0, math.pi / 2)) == pytest.approx((1.0, 0.0, 0.0))
    position, heading = errors([[0, 0, math.pi - 0.05]], [[3, 4, -math.pi + 0.05]])
    assert position[0] == pytest.approx(5.0)
    assert heading[0] == pytest.approx(0.1)   # wraps across +-180 degrees


def test_ekf_laser_overrides():
    config = yaml.safe_load((PACKAGE_DIR / 'config' / 'ekf_laser_odometry.yaml').read_text())
    params = config['ekf_filter_node']['ros__parameters']
    assert params['odom0'] == '/laser_odom'
    # Speeds (vx, vy) and turn rate (vyaw) only: never its pose, which drifts.
    used = [i for i, on in enumerate(params['odom0_config']) if on]
    assert used == [6, 7, 11]
