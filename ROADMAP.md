# QIRC Roadmap

The path from the current state to a fully working robot, focused on software.
Tasks are grouped into phases, roughly in dependency order, but many phases can run in parallel.

**Tags:**
- `now`: no hardware needed (code, simulation, recorded data)
- `hw`: needs a specific part on the bench
- `robot`: needs the assembled robot

## Current state

- [x] ROS 2 Humble workspace with one package per software stack (see the [software architecture](softwareArchitectureV2.png))
- [x] CI: `colcon build` + `colcon test` on every PR; `main` protected (PR + passing CI required)
- [x] Rear camera (OAK-D Lite) driver integration
- [x] Front camera (RealSense D435i, including its IMU) driver integration
- [ ] RPLidar driver integration (PR #4)
- [ ] Hardware decisions pending: motor controller (Raspberry Pi Pico, tentative), drive and arm motors, battery

---

## Phase 0: Foundations (unblock parallel work)

- [ ] `now` **Interfaces between stacks** (`qirc_interfaces`). Agreeing on these lets each stack be built independently.
  - [ ] `Detection` / `DetectionArray`: class (person / object / stairwell), confidence, 3D position, source camera
  - [ ] `RobotState`: vehicle manager state, battery, E-stop, errors
  - [ ] `DispensePills` action: pill count, progress, result
  - [ ] `ArmCommand`: target height
  - [ ] Agree on topic names, and document them in the README
- [ ] `now` **Placeholder URDF** (`qirc_description`)
  - [ ] Chassis, **left/right tracks**, sensor mounts (front camera, rear camera, LiDAR) at estimated positions
  - [ ] Replace the `TODO` parent frames in the sensor launch files with URDF frames
  - [ ] Update with real measurements once the chassis is designed
- [ ] `now` **Gazebo (Fortress) simulation**: the biggest unblocker while hardware is pending
  - [ ] New `qirc_gazebo` package; `ros_gz` bridge for topics
  - [ ] Tracked robot: start with the `DiffDrive` system, then switch to `TrackedVehicle` (see [Tracks in simulation](#tracks-in-simulation))
  - [ ] Simulated 2D LiDAR, RGB-D camera, IMU
  - [ ] House-like world: rooms, furniture, **a staircase**
  - [ ] `use_sim:=true` in bringup to swap real drivers for the simulation
- [ ] `now` **Visualization**: add `foxglove_bridge` to bringup (topics, camera feeds, LiDAR, teleop over the network)
- [ ] `now` **Project management**: turn this roadmap into GitHub Issues and Milestones, and assign owners

**M0: drive the simulated robot with teleop and see its sensors in Foxglove.**

---

## Phase 1: Sensor bring-up

- [ ] `hw` Test the OAK-D Lite on the laptop (`ros2 launch qirc_bringup qirc.launch.py`)
- [ ] `hw` Test the D435i on the laptop; check the IMU rate (`ros2 topic hz /front_camera/imu`)
- [ ] `hw` Test the RPLidar A2M8 (115200 baud); install the udev rule
- [ ] `hw` **Record rosbags** of all sensors around a house or lab, as shared real data for development
- [ ] `hw` Check that the TF tree connects every sensor frame to `base_link`

---

## Phase 2: Jetson Orin Nano bring-up

- [ ] `hw` Flash JetPack 6, install ROS 2 Humble, clone, `rosdep install`, build
- [ ] `hw` Networking: `ROS_DOMAIN_ID`, hostname (`qirc.local`), Tailscale; confirm laptop ↔ robot topic discovery
- [ ] `hw` All sensors at once: check USB bandwidth and CPU/GPU load (`jtop`)
- [ ] `hw` systemd service that starts bringup on boot

---

## Phase 3: Low-level control (motor controller + `qirc_pico_bridge`)

- [ ] `now` Decide on the motor controller (Raspberry Pi Pico RP2040 recommended); write the pin map
- [ ] `now` Define the serial protocol (track speeds, stepper/arm commands, encoder counts, status)
- [ ] `now` Firmware skeleton in `firmware/` (PlatformIO), with a **watchdog** that stops all motors if commands stop arriving
- [ ] `now` CI job that compiles the firmware
- [ ] `now` `qirc_pico_bridge` ROS 2 node: `/cmd_vel` → left/right track speeds → serial; includes a fake-controller mode for testing without hardware
- [ ] `hw` Drive motors without speed feedback (MD10C ×2) → encoders → per-track speed PID
- [ ] `hw` **Track odometry**: publish `/odom` from `qirc_pico_bridge`; the EKF, not the bridge, publishes the `odom → base_link` transform (see [Tracks and odometry](#tracks-and-odometry))
- [ ] `hw` Stepper control (DRV8825 ×2), arm motors, homing with limit switches
- [ ] `hw` Status LEDs and headlights
- [ ] `robot` E-stop end to end: motors cut in hardware, software detects it and reports it

**M1: drive the real robot with teleop from a laptop.**

---

## Phase 4: Localization and mapping

- [ ] `now` **Sensor fusion**: `robot_localization` EKF combining track odometry and the D435i IMU (develop in simulation)
- [ ] `now` **Mapping**: `slam_toolbox` in simulation
- [ ] `now` Decide whether `mapping_node` / `localization_node` stay custom or become wrappers or config around existing tools
- [ ] `robot` Map the real house or lab; save the map and load it on startup
- [ ] `robot` Localize within the saved map; test re-localization after the robot is moved by hand

**M2: the robot knows where it is on a saved map of the house.**

---

## Phase 5: Navigation (global planner, local planner, control)

- [ ] `now` **Nav2 baseline in simulation**: autonomous point-to-point navigation with stock planner/controller
- [ ] `now` **Custom global planner**: search algorithm that generates candidate points around the home to look for the user, picks the next one, and plans a path
- [ ] `now` **Custom local planner**: detours and obstacle avoidance during traversal
- [ ] `now` **MPC controller** (`control_node`), using a skid-steer model of the tracks
- [ ] `now` Compare the custom components against the Nav2 baseline (useful results for the report)
- [ ] `robot` Tune on the real robot: speed limits, obstacle inflation, MPC weights

**M3: autonomous navigation to a goal with obstacle avoidance.**

---

## Phase 6: Perception

- [ ] `hw` **Rear (OAK-D Lite)**: person detection on the camera's own chip, with 3D positions → `Detection` messages
- [ ] `hw` **Front (D435i)**: YOLO on the Orin GPU (TensorRT) + aligned depth for 3D positions → `Detection` messages
- [ ] `now` **Stairwell detection**: choose between a custom-trained model and depth-based edge detection; gather and label data from the rosbags
- [ ] `now` Feed detected obstacles and people into the local planner
- [ ] `now` *(Optional)* identify the specific user (face or a marker) if more than one person could be present

---

## Phase 7: Vehicle manager

- [ ] `now` **State machine**: sleep → wake (schedule or trigger) → search for user → approach → dispense → raise arm → return home → sleep, plus an **error / E-stop state**
- [ ] `now` Pill schedule: when to wake up and what to dispense
- [ ] `now` End-to-end test of the full sequence **in simulation**, with the dispenser and arm faked
- [ ] `now` Unit tests for the state transitions (run in CI)

---

## Phase 8: Pill dispenser and arm

- [ ] `hw` `DispensePills` action server: pill count → stepper moves → success/failure
- [ ] `hw` Calibrate steps per pill; add dispense verification if possible (e.g. a beam-break sensor)
- [ ] `hw` Arm to user height, using the height of the detected person from the cameras
- [ ] `hw` Disable the stepper drivers when idle (less heat and noise)

**M4: a complete dispense cycle on command.**

---

## Phase 9: Stairs ⚠️ highest risk

- [ ] `now` **Decide the scope early**: what "goes up stairs" means for the demo (mechanical + software)
- [ ] `now` Stair climbing in simulation (`TrackedVehicle` + staircase model)
- [ ] `now` Stair detection and aligning the robot square to the first step
- [ ] `now` Monitor the climb with the IMU: pitch, roll, tip-over detection, abort behaviour
- [ ] `robot` Real stair tests, with someone ready to catch the robot

---

## Phase 10: Web app

- [ ] `now` Foxglove for the engineering team in the meantime
- [ ] `now` `qirc_web` package: user-facing app served from the Jetson
  - [ ] `rosbridge_server` + roslibjs for live state and commands
  - [ ] `web_video_server` for camera streams
  - [ ] Robot status, battery, "dispense now", pill schedule, simple drive controls (with a speed cap)
- [ ] `now` Backend for persistent data (e.g. FastAPI inside a ROS node) if schedules and logins outgrow rosbridge
- [ ] `now` Authentication before any demo on a shared network; access over Tailscale

---

## Phase 11: Integration and reliability

- [ ] `robot` Full-scenario tests: scheduled wake → find user → dispense → return home
- [ ] `hw` Battery monitoring (e.g. INA226) and low-battery behaviour (return home, notify)
- [ ] `now` Logging: automatic rosbag recording on errors
- [ ] `robot` Crash recovery: every node restarts cleanly; the robot stops safely if the Jetson fails
- [ ] `now` Unit tests for the logic (state machine, planners, protocol parsing) in CI
- [ ] `now` Documentation and a demo script

**M5: a full autonomous demo.**

---

## Hardware and electrical (supporting tasks)

- [ ] Choose drive motors (with encoders; 12 V or 24 V, depending on the torque stair climbing needs)
- [ ] Confirm arm motor voltage, arm motor driver ×2, and arm position feedback (encoders or potentiometers)
- [ ] Choose the battery (recommended: 4S LiFePO4, 12.8 V, ~12–15 Ah; final choice depends on the drive motors)
- [ ] Power distribution: main fuse, main switch, E-stop (motor rail only), buck-boost to 19 V for the Jetson, 5 V buck for the LEDs
- [ ] Encoder voltage check (the Pico's RP2040 is not 5 V tolerant), level shifting if needed
- [ ] DRV8825 setup: current limit (~1.2–1.5 A), 100 µF capacitors, microstepping pins
- [ ] Wiring diagrams in `docs/wiring/` (WireViz) and a system power block diagram

---

## Critical path

**Simulation (Phase 0)** → **motor controller + odometry (Phase 3)** → **localization (Phase 4)** → **navigation (Phase 5)** → **full dispense cycle (Phases 7–8)**

Everything else can run alongside this chain. Simulation matters most right now because it lets software progress while hardware is still arriving.

---

## Notes on tracks

### Tracks in simulation

URDF has no native track model. Two approaches, used in this order:

1. **Diff drive with road wheels**: model each track as several wheels per side, using Gazebo's `DiffDrive` system. Simple and robust on flat ground; good enough for mapping, localization and navigation.
2. **`TrackedVehicle` system**: Gazebo Fortress has built-in track support (`TrackController` / `TrackedVehicle`). It simulates a track as a contact surface that moves like a conveyor belt, and its example world (`tracked_vehicle_simple.sdf`) includes a staircase. Use this for stair-climbing work.

### Tracks and odometry

Tracks are kinematically the same as differential drive (left/right speeds → forward speed + turn rate), so `/cmd_vel` and the controllers work the same way. But tracks **skid when turning**:
- Turning rate computed from the tracks alone is unreliable. In the odometry, the effective track separation needs calibrating, and is usually wider than the physical spacing.
- **Fusing the D435i IMU** (gyro) for heading is essential, not optional.
- LiDAR scan matching (`slam_toolbox`) corrects the remaining drift.
- The MPC should use a skid-steer model, or include slip in its model.
