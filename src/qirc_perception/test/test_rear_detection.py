"""Unit tests for relabelling the rear OAK's detections (no camera needed)."""

import os

import pytest
from qirc_perception.detection_utils import (
    load_label_names, OBJECT, PERSON, relabel_detection)
from qirc_perception.rear_detection_node import resolve_nn_config
from vision_msgs.msg import Detection3D, ObjectHypothesisWithPose

VOC = ['background', 'aeroplane', 'bicycle', 'bird', 'boat', 'bottle', 'bus', 'car', 'cat',
       'chair', 'cow', 'diningtable', 'dog', 'horse', 'motorbike', 'person', 'pottedplant',
       'sheep', 'sofa', 'train', 'tvmonitor']


def _detection(*results, x=1.0):
    """Build a Detection3D with (class_id, score) results at position x."""
    detection = Detection3D()
    detection.bbox.center.position.x = x
    for class_id, score in results:
        hypothesis = ObjectHypothesisWithPose()
        hypothesis.hypothesis.class_id = class_id
        hypothesis.hypothesis.score = score
        detection.results.append(hypothesis)
    return detection


def test_person_class_number_becomes_person():
    out = relabel_detection(_detection(('15', 0.9)), VOC, 0.5)
    assert out.results[0].hypothesis.class_id == PERSON


def test_other_class_numbers_become_object():
    for number in ('5', '9', '12', '20'):  # bottle, chair, dog, tvmonitor
        out = relabel_detection(_detection((number, 0.9)), VOC, 0.5)
        assert out.results[0].hypothesis.class_id == OBJECT


def test_position_and_score_kept():
    out = relabel_detection(_detection(('15', 0.8), x=2.5), VOC, 0.5)
    assert out.bbox.center.position.x == pytest.approx(2.5)
    assert out.results[0].hypothesis.score == pytest.approx(0.8)


def test_low_confidence_dropped():
    assert relabel_detection(_detection(('15', 0.4)), VOC, 0.5) is None


def test_background_and_unknown_numbers_dropped():
    assert relabel_detection(_detection(('0', 0.9)), VOC, 0.5) is None
    assert relabel_detection(_detection(('99', 0.9)), VOC, 0.5) is None
    assert relabel_detection(_detection(), VOC, 0.5) is None


def test_class_names_accepted():
    # If a driver version sends names instead of numbers, still map them.
    out = relabel_detection(_detection(('person', 0.9)), VOC, 0.5)
    assert out.results[0].hypothesis.class_id == PERSON


def test_most_confident_result_kept():
    out = relabel_detection(_detection(('9', 0.6), ('15', 0.9)), VOC, 0.5)
    assert len(out.results) == 1
    assert out.results[0].hypothesis.class_id == PERSON


def test_load_label_names():
    assert load_label_names('{"mappings": {"labels": ["a", "person"]}}') == ['a', 'person']


def test_driver_mobilenet_config_has_person_at_15():
    # The config the rear camera actually loads (rear_camera.yaml).
    path = resolve_nn_config('depthai_ros_driver/mobilenet')
    assert os.path.isfile(path)
    with open(path) as config_file:
        labels = load_label_names(config_file.read())
    assert labels[15] == 'person'
    assert labels[0] == 'background'


def test_resolve_json_path_unchanged():
    assert resolve_nn_config('/tmp/model.json') == '/tmp/model.json'
