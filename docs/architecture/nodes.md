# ROS 2 Nodes

Every node in the QIRC stack: which package it lives in, what it does, and what it connects to. See [node_graph.md](node_graph.md) for the diagram and [messages.md](messages.md) for the message types.

**Status:**
- **integrated**: running code exists
- **stub**: placeholder node exists, no logic yet
- **planned**: not created yet (linked issue)

## Sensor drivers

Vendor packages, configured and launched from this repo.

| Node | Package (launched from) | Status | Subscribes | Publishes |
|---|---|---|---|---|
| `front_camera` | `realsense2_camera` (`qirc_perception`) | integrated | – | `/front_camera/color/image_raw`, `/front_camera/aligned_depth_to_color/image_raw`, `/front_camera/imu` |
| `rear_camera` | `depthai_ros_driver` (`qirc_perception`) | integrated | – | `/rear_camera/rgb/image_raw`, `/rear_camera/nn/spatial_detections` |
| `rplidar` | `rplidar_ros` (`qirc_localization`) | integrated | – | `/scan` |

## Hardware bridge

| Node | Package | Status | Subscribes | Publishes |
|---|---|---|---|---|
| `qirc_pico_bridge` | `qirc_pico_bridge` | planned (#7) | `/cmd_vel`, `/lights`, `/dispenser/command`, `/arm/command` | `/odom`, `/estop`, `/battery`, `/dispenser/state`, `/arm/joint_states` |

The only node that talks to the Pico (one serial port, one owner). It relays commands and state and contains no multi-step logic. It publishes `/odom` but **not** the `odom → base_link` transform; the EKF publishes that.

## Infrastructure

Standard packages, configured in this repo.

| Node | Package (configured in) | Status | Subscribes | Publishes |
|---|---|---|---|---|
| `robot_state_publisher` | `robot_state_publisher` (`qirc_description`) | planned (#21) | URDF | TF: `base_link` → sensor and track frames |
| `ekf` | `robot_localization` (`qirc_localization`) | planned (#54) | `/odom`, `/front_camera/imu` | `/odometry/filtered`, TF: `odom → base_link` |
| `twist_mux` | `twist_mux` (`qirc_control`) | planned (#16) | `/cmd_vel_nav`, `/cmd_vel_teleop`, `/cmd_vel_web`, `/estop` (lock) | `/cmd_vel` |
| `teleop` | `teleop_twist_keyboard` / `teleop_twist_joy` | planned (#16) | – | `/cmd_vel_teleop` |
| `foxglove_bridge` | `foxglove_bridge` (`qirc_bringup`) | planned (#15) | any topic (development visualization) | – |

## Perception (`qirc_perception`)

| Node | Status | Subscribes | Publishes |
|---|---|---|---|
| `object_detection` | stub | `/front_camera/color/image_raw`, `/front_camera/aligned_depth_to_color/image_raw`, `/rear_camera/nn/spatial_detections` | `/detections` |
| `user_detection` | planned (#70) | `/detections` | `/user_info` |

`object_detection` runs YOLO on the front camera (#67, #68) and republishes the rear OAK's on-camera detections (#69). Both go out on `/detections`. Classes: person, object, stairwell.

## Localization (`qirc_localization`)

| Node | Package | Status | Subscribes | Publishes |
|---|---|---|---|---|
| `slam_toolbox` | `slam_toolbox` | planned (#55) | `/scan`, TF `odom → base_link` | `/map`, TF: `map → odom` |

Mapping mode builds and saves the house map; localization mode loads it on later runs (#56). The current `mapping_node` and `localization_node` stubs will be replaced by, or become wrappers around, `slam_toolbox`.

## Planning and control (`qirc_planning`, `qirc_control`)

| Node | Package | Status | Subscribes | Publishes | Serves / calls |
|---|---|---|---|---|---|
| `vehicle_manager` | `qirc_planning` | stub | `/user_info`, `/estop`, `/battery` | `/robot_state`, `/lights` | Serves: schedule and mission services. Calls: `SearchForUser`, `NavigateToPose`, `DispensePills`, `MoveArm` |
| `global_planner` | `qirc_planning` | stub | `/map`, `/user_info` | `/plan` | Serves: `SearchForUser` (#62), `NavigateToPose` |
| `local_planner` | `qirc_planning` | stub | `/plan`, `/scan`, `/detections` | `/local_plan` | – |
| `control` (MPC) | `qirc_control` | stub | `/local_plan`, `/odometry/filtered` | `/cmd_vel_nav` | – |

`vehicle_manager` is the state machine (#72): sleep → wake on schedule → search for user → approach → dispense → raise arm → return home, plus an error / E-stop state.

## Pill dispensing (`qirc_pill_dispenser`)

| Node | Status | Subscribes | Publishes | Serves |
|---|---|---|---|---|
| `pill_dispenser` | stub (currently split into `pill_box_node` and `arm_node`) | `/dispenser/state`, `/arm/joint_states`, `/user_info` | `/dispenser/command`, `/arm/command` | `DispensePills` (#79), `MoveArm` (#81) |

## Web app (`qirc_web`)

| Node | Package | Status | Subscribes | Publishes |
|---|---|---|---|---|
| `rosbridge_server` | `rosbridge_server` | planned (#86) | `/robot_state`, `/battery` | `/cmd_vel_web`; calls schedule and mission services |
| `web_video_server` | `web_video_server` | planned (#88) | camera image topics | MJPEG streams over HTTP |

## TF tree

```
map ──(slam_toolbox)──► odom ──(ekf)──► base_link ──(robot_state_publisher)──► front_camera_link, rear_camera_link, laser, tracks
```
