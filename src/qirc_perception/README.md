# qirc_perception

Camera drivers and detection for the QIRC. Detections from both cameras are published on `/detections` (`vision_msgs/Detection3DArray`), with the label `person` or `object`.

| Node | Camera | Status |
|---|---|---|
| `front_detection` | RealSense D435i (front) | YOLO11n on the colour image; distance from the aligned depth image |
| `rear_detection` | OAK-D Lite (back) | Planned (#69): republishes the OAK's on-camera detections |

## Setup: Ultralytics (YOLO)

`front_detection` needs [Ultralytics](https://docs.ultralytics.com), which isn't available through rosdep, so install it with pip:

```bash
pip install ultralytics "numpy<2"
```

Keep **`numpy<2`**. ROS 2 Humble's OpenCV and `cv_bridge` are built against numpy 1.x, and numpy 2 breaks them with `numpy.core.multiarray failed to import`. If you already have numpy 2 installed in `~/.local`, this command downgrades it.

The model weights (`yolo11n.pt`, about 6 MB) download automatically on first run to `~/.cache/qirc/`. Use the `model` parameter in `config/front_detection.yaml` to change the model or the path.

Ultralytics is AGPL-3.0 licensed.

On the Jetson, PyTorch must be NVIDIA's Jetson build rather than the pip default. That, and the TensorRT model, are covered in #68.

## Running

```bash
# Front camera + detection
ros2 launch qirc_bringup qirc.launch.py use_rear_camera:=false use_lidar:=false
ros2 topic echo /detections

# Without Ultralytics installed, turn detection off
ros2 launch qirc_bringup qirc.launch.py use_front_detection:=false
```

To view the detections, add a `Detection3DArray` display for `/detections` in Foxglove.

## How the 3D position is found

For each YOLO box, `front_detection`:
1. Takes the median depth of the central half of the box. This ignores the background around the object's edges, and pixels with no depth reading.
2. Turns the box centre and that depth into a 3D point, using the camera intrinsics from `/front_camera/color/camera_info`.

Detections are in the colour camera's optical frame (x right, y down, z forward). Each one's bounding box size is the box's width and height at that depth; its size along the camera axis is unknown, and set to 0. Boxes without enough depth readings, or further than `max_depth`, are dropped.

The maths is in `qirc_perception/detection_utils.py` and is unit-tested in `test/test_detection_utils.py`, with no camera or model needed.
