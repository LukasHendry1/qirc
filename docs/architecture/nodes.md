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
| `qirc_pico_bridge` | `qirc_pico_bridge` | planned (#7) | `/cmd_vel`, `/lights`, `/dispenser/command`, `/arm/command` | `/estop`, `/battery`, `/dispenser/state`, `/arm/joint_states` |

The only node that talks to the Pico (one serial port, one owner). It relays commands and state and contains no multi-step logic. The drive motors have no encoders, so it publishes no odometry: that comes from the LiDAR (`laser_odometry`).

## Simulation (`qirc_gazebo`)

Replaces the sensor drivers and the hardware bridge when running in Gazebo Fortress (`ros2 launch qirc_gazebo sim.launch.py`, or the whole stack with `ros2 launch qirc_bringup qirc.launch.py use_sim:=true`). The topics and frames are the same as on the real robot.

| Node | Package | Status | Subscribes | Publishes |
|---|---|---|---|---|
| `ign gazebo` | Gazebo Fortress, via `ros_gz_sim` | integrated | – | (Gazebo topics, bridged below) |
| `gz_bridge` | `ros_gz_bridge` | integrated | `/cmd_vel` | `/clock`, `/ground_truth`, `/joint_states`, `/scan`, `/front_camera/color/*`, `/front_camera/aligned_depth_to_color/*`, `/front_camera/imu` |
`sim.launch.py` also starts the EKF (`laser_odometry`, `imu_bias` and `ekf` below), which publishes `odom → base_link`. DiffDrive's wheel odometry isn't bridged, because the real robot has no drive encoders. `/ground_truth` is the robot's true pose, for measuring localization error (`odometry_test`).

## Infrastructure

Standard packages, configured in this repo.

| Node | Package (configured in) | Status | Subscribes | Publishes |
|---|---|---|---|---|
| `robot_state_publisher` | `robot_state_publisher` (`qirc_description`) | integrated | URDF | `/robot_description`, TF: `base_link` → sensor and track frames |
| `laser_odometry` | `qirc_localization` | integrated, in simulation | `/scan` | `/laser_odom` |
| `imu_bias` | `qirc_localization` | integrated, in simulation (#54) | `/front_camera/imu`, `/laser_odom` | `/front_camera/imu/unbiased` |
| `ekf` | `robot_localization` (`qirc_localization`) | integrated, in simulation (#54) | `/laser_odom`, `/front_camera/imu/unbiased` | `/odometry/filtered`, TF: `odom → base_link` |
| `twist_mux` | `twist_mux` (`qirc_control`) | planned (#16) | `/cmd_vel_nav`, `/cmd_vel_teleop`, `/cmd_vel_web`, `/estop` (lock) | `/cmd_vel` |
| `teleop` | `teleop_twist_keyboard` / `teleop_twist_joy` | planned (#16) | – | `/cmd_vel_teleop` |
| `foxglove_bridge` | `foxglove_bridge` (`qirc_bringup`) | planned (#15) | any topic (development visualization) | – |

The robot has no drive encoders, so `laser_odometry` provides its odometry: it matches each LiDAR scan to an earlier one (point-to-line ICP) and publishes the motion on `/laser_odom`. The EKF (`qirc_localization/launch/ekf.launch.py`, config in `config/ekf.yaml`) fuses its speeds and turn rate with the D435i's gyro. `imu_bias` first removes the gyro's bias, which it measures whenever the LiDAR odometry says the robot is still; robot_localization can't estimate it. On the real robot this needs the D435i's frames under `front_camera_link` (#22) and the LiDAR's `laser` frame in the URDF.

## Perception (`qirc_perception`)

| Node | Status | Subscribes | Publishes |
|---|---|---|---|
| `front_detection` | integrated (#67) | `/front_camera/color/image_raw`, `/front_camera/aligned_depth_to_color/image_raw`, `/front_camera/color/camera_info` | `/detections` |
| `rear_detection` | integrated (#69) | `/rear_camera/nn/spatial_detections` | `/detections` |
| `user_detection` | planned (#70) | `/detections` | `/user_info` |

`front_detection` runs YOLO11n on the front camera (#67; TensorRT on the Orin in #68). `rear_detection` republishes the rear OAK's on-camera detections (#69). Both publish on `/detections`, each in its own camera's optical frame, with the label `person` or `object` (`stairwell` comes with #71). Setup and details: [qirc_perception/README.md](../../src/qirc_perception/README.md).

## Localization (`qirc_localization`)

| Node | Package | Status | Subscribes | Publishes |
|---|---|---|---|---|
| `slam_toolbox` | `slam_toolbox` | integrated, mapping and localization modes, in simulation (#55, #56) | `/scan`, TF `odom → base_link`, `/initialpose` | `/map`, TF: `map → odom` |

`slam_toolbox` runs in one of two modes, both configured in `qirc_localization` (there are no custom mapping or localization nodes):

- **Mapping** builds the house map (`mapping.launch.py`, parameters in `config/mapper_params.yaml`). `ros2 run qirc_localization save_map [path]` saves it, by default to `~/qirc_maps/house`: the pose graph (`.posegraph`, `.data`) for localization, and an occupancy grid (`.pgm`, `.yaml`) for Nav2's `map_server`.
- **Localization** loads the saved map and tracks the robot in it without changing the map (`localization.launch.py map:=<path>`, with `config/localization_params.yaml` on top). The robot is expected to start where mapping started (the map origin). If it doesn't, give its pose on `/initialpose` (RViz's 2D Pose Estimate); slam_toolbox can't find the robot on the map by itself.

## Planning and control (`qirc_planning`, `qirc_control`)

| Node | Package | Status | Subscribes | Publishes | Serves / calls |
|---|---|---|---|---|---|
| `vehicle_manager` | `qirc_planning` | stub | `/user_info`, `/estop`, `/battery` | `/robot_state`, `/lights` | Serves: schedule and mission services. Calls: `SearchForUser`, `NavigateToPose`, `DispensePills`, `MoveArm` |
| `global_planner` | `qirc_planning` | stub | `/map`, `/user_info` | `/plan` | Serves: `SearchForUser` (#62), `NavigateToPose` |
| `local_planner` (MPC) | `qirc_planning` | stub | `/plan`, `/scan`, `/detections`, `/odometry/filtered`, TF `map → base_link` | `/cmd_vel_nav`, `/local_plan` (visualization) | – |

**Local planning is one layer.** `local_planner` follows the global path, avoids obstacles and drives the robot, all in one MPC (#63). It is sampling-based, in the style of Nav2's MPPI controller: it rolls out many candidate command sequences through a skid-steer model of the tracks (#64), scores each on following `/plan`, clearance from `/scan` and `/detections` (with a larger margin around people), and smoothness, and sends the best first command on `/cmd_vel_nav`. This is the classic ROS meaning of a local planner (as in ROS 1's `move_base`; Nav2 calls it the controller), so there is no separate path-tracking controller, and the benchmark (#66) compares it directly with Nav2's controller. `/local_plan` is the predicted path of the chosen rollout, for RViz only.

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

In simulation, until the EKF (#54) exists, Gazebo's DiffDrive publishes `odom → base_link`, and `robot_state_publisher` also publishes the road wheel frames under each track.
