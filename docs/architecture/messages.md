# ROS 2 Messages

The message types used between QIRC nodes. See [nodes.md](nodes.md) for which node publishes and subscribes to each topic.

**Approach:** standard ROS messages wherever one fits, so existing tools (RViz, Foxglove, Nav2, rosbag) understand the data. Custom definitions live in `qirc_interfaces`.

## Topics using standard messages

| Topic | Type | From → To |
|---|---|---|
| `/front_camera/color/image_raw` | `sensor_msgs/Image` | front_camera → front_detection, web_video_server |
| `/front_camera/aligned_depth_to_color/image_raw` | `sensor_msgs/Image` | front_camera → front_detection |
| `/front_camera/color/camera_info` | `sensor_msgs/CameraInfo` | front_camera → front_detection (intrinsics for 3D positions) |
| `/front_camera/imu` | `sensor_msgs/Imu` | front_camera → ekf |
| `/rear_camera/rgb/image_raw` | `sensor_msgs/Image` | rear_camera → web_video_server |
| `/rear_camera/nn/spatial_detections` | `vision_msgs/Detection3DArray` | rear_camera → rear_detection |
| `/scan` | `sensor_msgs/LaserScan` | rplidar → slam_toolbox, local_planner |
| `/odom` | `nav_msgs/Odometry` | qirc_pico_bridge → ekf (raw track odometry) |
| `/odometry/filtered` | `nav_msgs/Odometry` | ekf → control |
| `/map` | `nav_msgs/OccupancyGrid` | slam_toolbox → global_planner |
| `/detections` | `vision_msgs/Detection3DArray` | front_detection, rear_detection → user_detection, local_planner |
| `/plan` | `nav_msgs/Path` | global_planner → local_planner |
| `/local_plan` | `nav_msgs/Path` | local_planner → control |
| `/cmd_vel_nav` | `geometry_msgs/Twist` | control → twist_mux |
| `/cmd_vel_teleop` | `geometry_msgs/Twist` | teleop → twist_mux |
| `/cmd_vel_web` | `geometry_msgs/Twist` | rosbridge_server (web app) → twist_mux |
| `/cmd_vel` | `geometry_msgs/Twist` | twist_mux → qirc_pico_bridge |
| `/estop` | `std_msgs/Bool` | qirc_pico_bridge → twist_mux (lock), vehicle_manager |
| `/battery` | `sensor_msgs/BatteryState` | qirc_pico_bridge → vehicle_manager, web app |
| `/arm/joint_states` | `sensor_msgs/JointState` | qirc_pico_bridge → pill_dispenser |
| TF (`/tf`, `/tf_static`) | `tf2_msgs/TFMessage` | robot_state_publisher, ekf, slam_toolbox → all |

Notes:
- **Detections** use the standard `vision_msgs/Detection3DArray` (class label, confidence and 3D position for each detection) rather than a custom type. The OAK driver already publishes this format. Classes: `person`, `object`, `stairwell`.
- **`/local_plan`** starts as `nav_msgs/Path`. If the MPC needs speeds and timing along the path, add a custom `Trajectory.msg` later.
- **`/estop`** is a plain `Bool` so `twist_mux` can use it directly as a lock that blocks all drive commands.

## Custom messages (`qirc_interfaces/msg`)

| Message | Topic | From → To | Issue |
|---|---|---|---|
| `RobotState` | `/robot_state` | vehicle_manager → web app, anyone | #9 |
| `LightCommand` | `/lights` | vehicle_manager → qirc_pico_bridge | #9 |
| `UserInfo` | `/user_info` | user_detection → vehicle_manager, global_planner, pill_dispenser | #10 |
| `DispenserCommand` | `/dispenser/command` | pill_dispenser → qirc_pico_bridge | #11 |
| `DispenserState` | `/dispenser/state` | qirc_pico_bridge → pill_dispenser | #11 |
| `ArmCommand` | `/arm/command` | pill_dispenser → qirc_pico_bridge | #12 |
| `PillScheduleEntry` | (inside schedule services) | – | #13 |

The definitions, with units and comments for each field, are in [`src/qirc_interfaces/msg`](../../src/qirc_interfaces/msg).

## Actions (`qirc_interfaces/action`)

Used for anything that takes time, so the vehicle manager can watch progress, cancel, and get a clear result. Definitions: [`src/qirc_interfaces/action`](../../src/qirc_interfaces/action).

| Action | Server ← Client | Goal → Feedback → Result | Issue |
|---|---|---|---|
| `DispensePills` | pill_dispenser ← vehicle_manager | dispenser id, pill count → pills dispensed so far → success, count, error | #11 |
| `MoveArm` | pill_dispenser ← vehicle_manager | target height → current height → success, final height | #12 |
| `SearchForUser` | global_planner ← vehicle_manager | search area → points checked / remaining → found, user pose | #14 |
| `NavigateToPose` (standard, `nav2_msgs`) | global_planner ← vehicle_manager | goal pose → distance remaining → success | – |

`NavigateToPose` is the standard Nav2 action, used for "approach the user" and "return home". Using it means the Nav2 baseline (#59) and the custom planner can be swapped without changing the vehicle manager.

## Services (`qirc_interfaces/srv` and standard)

Custom definitions: [`src/qirc_interfaces/srv`](../../src/qirc_interfaces/srv).

| Service | Type | Server ← Client | Issue |
|---|---|---|---|
| `/get_schedule` | `GetSchedule` (custom): → list of `PillScheduleEntry` | vehicle_manager ← web app | #13 |
| `/set_schedule` | `SetSchedule` (custom): list of `PillScheduleEntry` → success, message | vehicle_manager ← web app | #13 |
| `/vehicle_manager/start_mission` | `std_srvs/Trigger` | vehicle_manager ← web app | – |
| `/vehicle_manager/stop` | `std_srvs/Trigger` | vehicle_manager ← web app | – |
| `/vehicle_manager/go_home` | `std_srvs/Trigger` | vehicle_manager ← web app | – |
| `/vehicle_manager/dispense_now` | `std_srvs/Trigger` | vehicle_manager ← web app ("Dispense now" button) | #13 |

`start_mission` runs the full mission now (search, approach, dispense, return home). `dispense_now` dispenses the next scheduled dose immediately where the robot is, without searching, for when the user is already at the robot.

## Design decisions

- **`RobotState` keeps the minimum set of states** for the mission. More states are added as they are needed.
- **No homing for the arm or the dispensers** (for now). The Pico counts positions from power-on, so the arm and dispensers must be in their rest position when the robot is switched on. The E-stop cuts only the motor rail, so the Pico keeps its position counts through an E-stop. Limit switch homing (#50) is deferred. `DispenserState` therefore has no `homed` flag.
- **The arm command is a custom message** (`ArmCommand`) rather than `std_msgs/Float64MultiArray`, so the fields are named and typed. The arm state stays `sensor_msgs/JointState`, which RViz and Foxglove already understand.
- **"Dispense now" is its own service** (`/vehicle_manager/dispense_now`), separate from `start_mission`.

## Dependencies

Message packages beyond core ROS: `vision_msgs`, `nav2_msgs`, `std_srvs`. All are installed by `rosdep`.
