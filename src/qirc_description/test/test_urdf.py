"""Check that the robot model expands with xacro and forms a valid URDF tree."""

import math
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
import xacro

URDF_FILE = Path(__file__).resolve().parents[1] / 'urdf' / 'qirc.urdf.xacro'

EXPECTED_LINKS = {
    'base_link', 'chassis_link', 'left_track_link', 'right_track_link',
    'front_camera_link', 'rear_camera_link', 'laser',
}


@pytest.fixture(scope='module')
def robot():
    return ET.fromstring(xacro.process_file(str(URDF_FILE)).toxml())


def test_expected_links_present(robot):
    names = {link.get('name') for link in robot.findall('link')}
    assert EXPECTED_LINKS <= names


def test_names_unique(robot):
    for tag in ('link', 'joint'):
        names = [e.get('name') for e in robot.findall(tag)]
        assert len(names) == len(set(names)), f'duplicate {tag} names'


def test_single_tree_rooted_at_base_link(robot):
    links = {link.get('name') for link in robot.findall('link')}
    children = {}
    parent_of = {}
    for joint in robot.findall('joint'):
        parent = joint.find('parent').get('link')
        child = joint.find('child').get('link')
        assert parent in links and child in links, f'{joint.get("name")}: unknown link'
        assert child not in parent_of, f'{child} has more than one parent'
        parent_of[child] = parent
        children.setdefault(parent, []).append(child)

    roots = links - set(parent_of)
    assert roots == {'base_link'}

    reached, todo = set(), ['base_link']
    while todo:
        link = todo.pop()
        reached.add(link)
        todo.extend(children.get(link, []))
    assert reached == links, f'unreachable links: {links - reached}'


def test_root_has_no_inertia(robot):
    # KDL (robot_state_publisher) ignores inertia on the root link and warns.
    base = next(link for link in robot.findall('link') if link.get('name') == 'base_link')
    assert base.find('inertial') is None


def test_physical_links_have_valid_inertia(robot):
    # Gazebo needs a positive mass and a physically possible inertia on every body.
    for link in robot.findall('link'):
        if link.get('name') == 'base_link':
            continue
        inertial = link.find('inertial')
        assert inertial is not None, f'{link.get("name")} has no inertial'
        assert float(inertial.find('mass').get('value')) > 0
        i = inertial.find('inertia')
        ixx, iyy, izz = (float(i.get(k)) for k in ('ixx', 'iyy', 'izz'))
        assert min(ixx, iyy, izz) > 0, f'{link.get("name")}: non-positive inertia'
        assert ixx + iyy >= izz and iyy + izz >= ixx and ixx + izz >= iyy, \
            f'{link.get("name")}: inertia breaks the triangle inequality'


def test_tracks_are_symmetric_and_on_the_ground(robot):
    origins = {}
    for joint in robot.findall('joint'):
        child = joint.find('child').get('link')
        if child.endswith('_track_link'):
            origins[child] = [float(v) for v in joint.find('origin').get('xyz').split()]
    left, right = origins['left_track_link'], origins['right_track_link']
    assert left[1] > 0 > right[1], 'left track must be at +y, right at -y'
    assert left[1] == pytest.approx(-right[1])
    assert left[0] == pytest.approx(right[0]) and left[2] == pytest.approx(right[2])

    track = next(link for link in robot.findall('link') if link.get('name') == 'left_track_link')
    radius = float(track.find('visual/geometry/cylinder').get('radius'))
    assert left[2] == pytest.approx(radius), 'track bottom must touch z = 0 (the ground)'


def _joint_to(robot, child):
    """Return (xyz, rpy) of the joint whose child is the given link."""
    joint = next(j for j in robot.findall('joint') if j.find('child').get('link') == child)
    origin = joint.find('origin')
    xyz = [float(v) for v in origin.get('xyz').split()]
    rpy = [float(v) for v in origin.get('rpy', '0 0 0').split()]
    return xyz, rpy


def _chassis_bounds(robot):
    """Return (front x, back x, top z) of the chassis in base_link."""
    chassis = next(link for link in robot.findall('link') if link.get('name') == 'chassis_link')
    length, _, height = (float(v) for v in chassis.find('visual/geometry/box').get('size').split())
    (x, _, z), _ = _joint_to(robot, 'chassis_link')
    return x + length / 2, x - length / 2, z + height / 2


def test_sensors_attached_to_base_link(robot):
    for sensor in ('front_camera_link', 'rear_camera_link', 'laser'):
        joint = next(j for j in robot.findall('joint') if j.find('child').get('link') == sensor)
        assert joint.find('parent').get('link') == 'base_link'
        assert joint.get('type') == 'fixed'


def test_front_camera_on_front_face_facing_forward(robot):
    front, _, top = _chassis_bounds(robot)
    (x, y, z), (_, _, yaw) = _joint_to(robot, 'front_camera_link')
    assert x > front, 'front camera must be at or ahead of the chassis front'
    assert y == pytest.approx(0.0)
    assert 0 < z <= top
    assert yaw == pytest.approx(0.0)


def test_rear_camera_on_back_face_facing_backward(robot):
    _, back, top = _chassis_bounds(robot)
    (x, y, z), (_, _, yaw) = _joint_to(robot, 'rear_camera_link')
    assert x < back, 'rear camera must be at or behind the chassis back'
    assert y == pytest.approx(0.0)
    assert 0 < z <= top
    assert abs(yaw) == pytest.approx(math.pi)


def test_laser_above_chassis(robot):
    # The scan plane must clear the chassis top for an unobstructed 360 degree view.
    _, _, top = _chassis_bounds(robot)
    (_, y, z), _ = _joint_to(robot, 'laser')
    assert z > top
    assert y == pytest.approx(0.0)
