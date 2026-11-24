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


def _expand(sim):
    mappings = {'sim': 'true' if sim else 'false'}
    return ET.fromstring(xacro.process_file(str(URDF_FILE), mappings=mappings).toxml())


# Every general test runs on both the real model and the simulation model.
@pytest.fixture(scope='module', params=[False, True], ids=['real', 'sim'])
def robot(request):
    return _expand(request.param)


@pytest.fixture(scope='module')
def real_robot():
    return _expand(False)


@pytest.fixture(scope='module')
def sim_robot():
    return _expand(True)


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


def _is_frame(link):
    # A pure coordinate frame (e.g. a camera's optical frame): nothing to
    # simulate, so Gazebo merges it into its parent.
    return not any(link.find(tag) is not None for tag in ('visual', 'collision', 'inertial'))


def test_physical_links_have_valid_inertia(robot):
    # Gazebo needs a positive mass and a physically possible inertia on every body.
    for link in robot.findall('link'):
        if link.get('name') == 'base_link' or _is_frame(link):
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


# ===== Simulation (sim:=true) ================================================

def _wheel_joints(robot):
    return [j for j in robot.findall('joint') if j.get('type') == 'continuous']


def _plugin(robot, system):
    for plugin in robot.findall('gazebo/plugin'):
        if plugin.get('name') == f'ignition::gazebo::systems::{system}':
            return plugin
    raise AssertionError(f'no {system} plugin')


def test_real_model_has_no_gazebo_parts(real_robot):
    # The real robot's model and TF must not change because of the simulation.
    assert real_robot.find('gazebo') is None
    assert not _wheel_joints(real_robot)
    names = {link.get('name') for link in real_robot.findall('link')}
    assert names == EXPECTED_LINKS


def test_real_tracks_have_collisions(real_robot):
    for side in ('left', 'right'):
        track = next(link for link in real_robot.findall('link')
                     if link.get('name') == f'{side}_track_link')
        assert track.findall('collision')


def test_sim_tracks_have_no_collisions(sim_robot):
    # The road wheels touch the ground instead.
    for side in ('left', 'right'):
        track = next(link for link in sim_robot.findall('link')
                     if link.get('name') == f'{side}_track_link')
        assert not track.findall('collision')


def test_sim_wheels_touch_the_ground(sim_robot):
    wheels = _wheel_joints(sim_robot)
    assert len(wheels) >= 4
    for joint in wheels:
        track = joint.find('parent').get('link')
        assert track.endswith('_track_link')
        (_, _, track_z), _ = _joint_to(sim_robot, track)
        wheel_z = float(joint.find('origin').get('xyz').split()[2])
        link = next(link for link in sim_robot.findall('link')
                    if link.get('name') == joint.find('child').get('link'))
        radius = float(link.find('collision/geometry/cylinder').get('radius'))
        assert track_z + wheel_z - radius == pytest.approx(0.0), joint.get('name')
        assert joint.find('axis').get('xyz').split() == ['0', '1', '0']


def test_diff_drive_drives_every_wheel_on_the_right_side(sim_robot):
    plugin = _plugin(sim_robot, 'DiffDrive')
    for side in ('left', 'right'):
        listed = {e.text for e in plugin.findall(f'{side}_joint')}
        wheels = {j.get('name') for j in _wheel_joints(sim_robot)
                  if j.find('parent').get('link') == f'{side}_track_link'}
        assert listed == wheels, side


def test_diff_drive_geometry_matches_the_tracks(sim_robot):
    plugin = _plugin(sim_robot, 'DiffDrive')
    (_, left_y, track_z), _ = _joint_to(sim_robot, 'left_track_link')
    (_, right_y, _), _ = _joint_to(sim_robot, 'right_track_link')
    # Wider than the physical separation to account for skid, but not absurdly.
    ratio = float(plugin.findtext('wheel_separation')) / (left_y - right_y)
    assert 1.0 <= ratio <= 2.0
    assert float(plugin.findtext('wheel_radius')) == pytest.approx(track_z)


def test_diff_drive_topics(sim_robot):
    # Must match qirc_gazebo/config/bridge.yaml and REP 105.
    plugin = _plugin(sim_robot, 'DiffDrive')
    assert plugin.findtext('topic') == '/cmd_vel'
    # No drive encoders: DiffDrive's wheel odometry must not reach the stack.
    assert plugin.find('odom_topic') is None
    assert plugin.find('tf_topic') is None
    assert _plugin(sim_robot, 'JointStatePublisher').findtext('topic') == '/joint_states'


D435I_FRAMES = {
    'front_camera_color_frame', 'front_camera_color_optical_frame',
    'front_camera_imu_frame', 'front_camera_imu_optical_frame',
}


def _front_camera_sensor(sim_robot, kind):
    gazebo = next(g for g in sim_robot.findall('gazebo')
                  if g.get('reference') == 'front_camera_link')
    return next(s for s in gazebo.findall('sensor') if s.get('type') == kind)


def test_sim_has_the_d435i_frames(sim_robot):
    # realsense2_camera publishes these on the real robot; the simulation's
    # model has them instead. Both hang off front_camera_link.
    names = {link.get('name') for link in sim_robot.findall('link')}
    assert D435I_FRAMES <= names
    for optical in ('front_camera_color_optical_frame', 'front_camera_imu_optical_frame'):
        _, rpy = _joint_to(sim_robot, optical)
        assert rpy == pytest.approx([-math.pi / 2, 0, -math.pi / 2]), 'z forward, x right, y down'


def test_sim_camera_matches_the_d435i(sim_robot):
    # Same images and frame as realsense2_camera with front_camera.yaml.
    sensor = _front_camera_sensor(sim_robot, 'rgbd_camera')
    assert sensor.findtext('topic') == '/front_camera'
    assert sensor.findtext('ignition_frame_id') == 'front_camera_color_optical_frame'
    assert float(sensor.findtext('update_rate')) == pytest.approx(30)
    image = sensor.find('camera/image')
    width, height = int(image.findtext('width')), int(image.findtext('height'))
    assert (width, height) == (848, 480)
    hfov = float(sensor.findtext('camera/horizontal_fov'))
    vfov = 2 * math.atan(math.tan(hfov / 2) * height / width)
    assert math.degrees(hfov) == pytest.approx(69, abs=1)
    assert math.degrees(vfov) == pytest.approx(42, abs=1.5)
    assert float(sensor.findtext('camera/depth_camera/clip/near')) == pytest.approx(0.195)
    # At the colour camera, which is 15 mm along y from the depth origin.
    pose = [float(v) for v in sensor.findtext('pose').split()]
    assert pose[1] == pytest.approx(0.015)


def test_sim_imu_matches_the_d435i(sim_robot):
    sensor = _front_camera_sensor(sim_robot, 'imu')
    assert sensor.findtext('topic') == '/front_camera/imu'
    assert sensor.findtext('ignition_frame_id') == 'front_camera_imu_optical_frame'
    assert float(sensor.findtext('update_rate')) == pytest.approx(200)
    # Rotated like the optical frame, so readings are in the real IMU's axes.
    pose = [float(v) for v in sensor.findtext('pose').split()]
    xyz, _ = _joint_to(sim_robot, 'front_camera_imu_frame')
    assert pose[:3] == pytest.approx(xyz)
    assert pose[3:] == pytest.approx([-math.pi / 2, 0, -math.pi / 2])
    assert sensor.findtext('imu/enable_orientation') == 'false'
    # A gyro bias, so the EKF's bias removal is tested in simulation.
    bias = sensor.find('imu/angular_velocity/z/noise/bias_stddev')
    assert float(bias.text) > 0


def test_sim_lidar_matches_the_real_one(sim_robot):
    # Same topic, frame and specs as rplidar_ros with the A2M8, so slam_toolbox
    # can't tell the difference.
    gazebo = next(g for g in sim_robot.findall('gazebo') if g.get('reference') == 'laser')
    sensor = gazebo.find('sensor')
    assert sensor.get('type') == 'gpu_lidar'
    assert sensor.findtext('topic') == '/scan'
    assert sensor.findtext('ignition_frame_id') == 'laser'
    assert float(sensor.findtext('update_rate')) == pytest.approx(10)
    horizontal = sensor.find('lidar/scan/horizontal')
    samples = int(horizontal.findtext('samples'))
    span = float(horizontal.findtext('max_angle')) - float(horizontal.findtext('min_angle'))
    assert span + 2 * math.pi / samples == pytest.approx(2 * math.pi), 'must cover 360 degrees'
    assert float(sensor.findtext('lidar/range/min')) == pytest.approx(0.15)
    assert float(sensor.findtext('lidar/range/max')) == pytest.approx(12.0)
