"""Unit tests for qirc_perception.detection_utils (no camera or model needed)."""

import math

import numpy as np
import pytest
from qirc_perception.detection_utils import (
    box_depth, deproject, depth_to_metres, image_to_numpy, make_detection, OBJECT,
    PERSON, to_qirc_label)
from sensor_msgs.msg import Image
from std_msgs.msg import Header

# A 640x480 camera with the principal point at the image centre.
K = [600.0, 0.0, 320.0, 0.0, 600.0, 240.0, 0.0, 0.0, 1.0]


def _image(array, encoding, step=None):
    msg = Image()
    msg.height, msg.width = array.shape[:2]
    msg.encoding = encoding
    msg.is_bigendian = False
    row = array.reshape(msg.height, -1).view(np.uint8)
    if step is not None:  # add padding at the end of each row
        row = np.hstack([row, np.zeros((msg.height, step - row.shape[1]), np.uint8)])
    msg.step = row.shape[1]
    msg.data = row.tobytes()
    return msg


def test_labels():
    assert to_qirc_label('person') == PERSON
    assert to_qirc_label('Person ') == PERSON
    for name in ('chair', 'dog', 'bottle', 'tvmonitor'):
        assert to_qirc_label(name) == OBJECT


def test_rgb8_becomes_bgr():
    rgb = np.zeros((2, 3, 3), np.uint8)
    rgb[..., 0] = 255  # pure red
    bgr = image_to_numpy(_image(rgb, 'rgb8'))
    assert bgr.shape == (2, 3, 3)
    assert (bgr[..., 2] == 255).all() and (bgr[..., 0] == 0).all()


def test_bgr8_unchanged():
    bgr = np.random.default_rng(0).integers(0, 255, (4, 5, 3), dtype=np.uint8)
    assert np.array_equal(image_to_numpy(_image(bgr, 'bgr8')), bgr)


def test_depth_16uc1_with_row_padding():
    depth = np.arange(12, dtype=np.uint16).reshape(3, 4) * 100
    out = image_to_numpy(_image(depth, '16UC1', step=12))  # 8 bytes of data + 4 padding
    assert out.dtype == np.uint16
    assert np.array_equal(out, depth)


def test_unsupported_encoding():
    with pytest.raises(ValueError):
        image_to_numpy(_image(np.zeros((2, 2), np.uint8), 'mono8'))


def test_depth_to_metres():
    mm = np.array([[0, 1000], [2500, 65535]], np.uint16)
    m = depth_to_metres(mm, '16UC1')
    assert math.isnan(m[0, 0])
    assert m[0, 1] == pytest.approx(1.0) and m[1, 0] == pytest.approx(2.5)

    f = np.array([[0.0, np.inf], [1.5, -1.0]], np.float32)
    m = depth_to_metres(f, '32FC1')
    assert np.isnan(m[0, 0]) and np.isnan(m[0, 1]) and np.isnan(m[1, 1])
    assert m[1, 0] == pytest.approx(1.5)


def test_box_depth_ignores_background_and_holes():
    depth = np.full((480, 640), 4.0, np.float32)  # background wall at 4 m
    depth[100:300, 200:300] = 1.5                 # object at 1.5 m
    depth[190:210, 240:260] = np.nan              # hole in the depth image
    # Box slightly larger than the object, so its edges include background.
    assert box_depth(depth, (190, 90, 310, 310)) == pytest.approx(1.5)


def test_box_depth_none_without_readings():
    depth = np.full((480, 640), np.nan, np.float32)
    assert box_depth(depth, (100, 100, 200, 200)) is None


def test_box_depth_box_at_image_edge():
    depth = np.full((480, 640), 2.0, np.float32)
    assert box_depth(depth, (-20, -20, 10, 10)) == pytest.approx(2.0)
    assert box_depth(depth, (630, 470, 700, 500)) == pytest.approx(2.0)


def test_deproject():
    assert deproject(320, 240, 2.0, K) == pytest.approx((0.0, 0.0, 2.0))
    # 300 px right of centre at 2 m with fx = 600: 1 m right.
    assert deproject(620, 240, 2.0, K) == pytest.approx((1.0, 0.0, 2.0))
    # Optical frame: y is down, so above the centre is negative y.
    assert deproject(320, 0, 3.0, K) == pytest.approx((0.0, -1.2, 3.0))


def test_make_detection():
    header = Header(frame_id='front_camera_color_optical_frame')
    # A person 1.8 m tall standing 3 m away, centred: 360 px tall at fy = 600.
    detection = make_detection(header, PERSON, 0.9, (290, 60, 350, 420), 3.0, K)
    assert detection.header.frame_id == 'front_camera_color_optical_frame'
    assert detection.bbox.center.position.z == pytest.approx(3.0)
    assert detection.bbox.center.position.x == pytest.approx(0.0)
    assert detection.bbox.size.y == pytest.approx(1.8)
    assert detection.bbox.size.x == pytest.approx(0.3)
    (result,) = detection.results
    assert result.hypothesis.class_id == PERSON
    assert result.hypothesis.score == pytest.approx(0.9)
    assert result.pose.pose.position.z == pytest.approx(3.0)
