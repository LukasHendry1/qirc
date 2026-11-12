# Queen's Intelligent Robotic Companion (QIRC)

**MREN 403: Capstone**

**Authors:** Lukas Hendry, Pablo Silva, Liam McIntaggart, Vikram Lew

---

## Overview

The QIRC is an autonomous mobile robot that stores, dispenses, and delivers pill medication to the user within the home. It can navigate between floors, including going upstairs, and has a friendly, non-threatening design so it is comfortable to have around.

## Hardware

| Component | Purpose |
|---|---|
| Intel RealSense D435 | Depth/RGB camera for object, person, and stairwell detection |
| OAK-D Lite | Second depth/RGB camera for perception |
| RPLIDAR A2M8 | 360° 2D LiDAR for mapping and localization |
| Jetson Nano | Onboard compute |

<!-- TODO: add drivetrain, stair-climbing mechanism, pill dispenser, and battery details. -->

## Software Architecture

![Software architecture](softwareArchitectureV2.png)

The QIRC runs on **ROS 2 (Humble)**. Functionality is split into packages, each containing nodes that communicate over ROS 2 topics, services, and actions.

| Package | Responsibility |
|---|---|
| `perception` | Detect objects, people, and stairwells from camera input |
| `localization` | Build a map and estimate the robot's pose |
| `planning` | Decide where the robot goes and how it gets there |
| `control` | Turn planned paths into vehicle commands |
| `pill_dispenser` | Dispense pills and operate the delivery arm |

---

## Repository Structure

### Perception Package

Uses camera input from the RealSense D435 and the OAK-D Lite to detect objects, persons, and stairwells.

- **Camera Node**: Primary node responsible for acquiring camera streams and publishing detections for the rest of the system.

### Localization Package

Uses LiDAR input to build a map of the home and determine where the robot is within it.

- **Mapping Node**: Builds the map using SLAM. No prior map of the home is assumed, so the robot maps the space on first deployment.
- **Localization Node**: Uses the saved map to estimate the robot's pose with Adaptive Monte Carlo Localization (AMCL).

### Planning Package

Decides where the vehicle goes and how it gets there.

- **Vehicle Manager Node**: Top-level coordinator that sequences tasks and manages the state of the whole system.
- **Global Planner Node**: Plans a route to the goal using A*.
- **Local Planner Node**: Follows the global route while avoiding obstacles in real time.

### Control Package

Controls the vehicle's motion.

- **Control Node**: Tracks the planned path using a model predictive control (MPC) algorithm.

### Pill Dispenser Package

Handles medication storage and delivery.

- **Pill Box Node**: Controls how many pills are dispensed.
- **Arm Node**: Raises and lowers the arm when appropriate to present the medication to the user.

---

## Getting Started

<!-- TODO: fill in once the build is stable. -->

```bash
# Clone the repository
git clone <repo-url>
cd <repo-name>

# Build (ROS 2 Humble)
colcon build
source install/setup.bash

# Launch
ros2 launch <package> <launch_file>
```

## License

<!-- TODO: add license. -->