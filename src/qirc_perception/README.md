# qirc_perception

Camera drivers and detection for the QIRC. Detections from both cameras are published on `/detections` (`vision_msgs/Detection3DArray`), with the label `person` or `object`.

| Node | Camera | Status |
|---|---|---|
| `front_detection` | RealSense D435i (front) | YOLO11n on the colour image; distance from the aligned depth image |
| `rear_detection` | OAK-D Lite (back) | Republishes the OAK's on-camera detections (stock MobileNet-SSD), relabelled |

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

## Viewing the detections

Each detection node publishes a debug image: the camera image with every box, its label, score and distance drawn on it.

| Topic | Image |
|---|---|
| `/front_detection/image` | Front colour image with the YOLO boxes. Grey boxes were dropped: no depth, or beyond `max_depth`. |
| `/rear_detection/image` | The 300 × 300 image the OAK's network ran on, with its boxes |

They're only drawn while something subscribes, so they cost nothing otherwise. View them with any image viewer:

```bash
ros2 run rqt_image_view rqt_image_view /front_detection/image
```

You can also use an Image display in RViz, or an Image panel in Foxglove.

## Rear camera detections

The OAK-D Lite runs MobileNet-SSD on the camera itself, and the depthai driver publishes `/rear_camera/nn/spatial_detections` with 3D positions already in place. The driver labels each detection with a class number (VOC classes, where 15 is person). `rear_detection` turns these into `person` / `object`, using the class names from the same model config the driver loads (`nn_config`, which must match `i_nn_config_path` in `rear_camera.yaml`). It drops results below `min_confidence`, and leaves positions unchanged. It needs no extra installs.

The driver gives each bounding box in **pixels** of the image the network ran on (its "passthrough" image, 300 × 300). `rear_detection` converts it to metres, the same as the front camera's:
- the box is centred on the 3D position
- its width and height are scaled with the passthrough image's camera matrix

That's why `rear_camera.yaml` sets `i_enable_passthrough: true`. Until the passthrough `camera_info` arrives, the box size is 0.

## How the 3D position is found (front camera)

For each YOLO box, `front_detection`:
1. Takes the median depth of the central half of the box. This ignores the background around the object's edges, and pixels with no depth reading.
2. Turns the box centre and that depth into a 3D point, using the camera intrinsics from `/front_camera/color/camera_info`.

Detections are in the colour camera's optical frame (x right, y down, z forward). Each one's bounding box size is the box's width and height at that depth; its size along the camera axis is unknown, and set to 0. Boxes without enough depth readings, or further than `max_depth`, are dropped.

The maths is in `qirc_perception/detection_utils.py` and is unit-tested in `test/test_detection_utils.py`, with no camera or model needed.
