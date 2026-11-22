# qirc_gazebo

Gazebo Fortress simulation of the QIRC. It publishes the same topics and frames as the real robot, so the rest of the stack (e.g. `slam_toolbox`) doesn't need to know it's simulated.

## Running

```bash
ros2 launch qirc_gazebo sim.launch.py
ros2 run teleop_twist_keyboard teleop_twist_keyboard   # drive it
```

| Argument | Default | |
|---|---|---|
| `world` | `obstacles.sdf` | World file in `worlds/`. `obstacles.sdf` has walls and boxes for the LiDAR to see; `empty.sdf` is just the ground. The house world is #28. |
| `headless` | `false` | Run the Gazebo server only, without the GUI |
| `ekf` | `true` | Fuse the odometry and the simulated gyro with the EKF (`qirc_localization`'s `ekf.launch.py`), which publishes `odom → base_link`. With `false`, DiffDrive's raw odometry publishes it instead. |

To see the robot and scan in RViz, run `rviz2` and set the fixed frame to `odom`.

## What it starts

- **Gazebo** with the world, through `ros_gz_sim`
- **`robot_state_publisher`** with the robot model built with `sim:=true` (`qirc_description/urdf/gazebo.urdf.xacro`), on simulation time
- **Spawns the robot** from `/robot_description`
- **The EKF** (`ekf:=true`): `imu_bias` and `robot_localization`, from `qirc_localization`
- **`ros_gz_bridge`**, configured in `config/`:

| ROS topic | Direction | Type |
|---|---|---|
| `/clock` | Gazebo → ROS | `rosgraph_msgs/Clock` |
| `/cmd_vel` | ROS → Gazebo | `geometry_msgs/Twist` |
| `/odom` | Gazebo → ROS | `nav_msgs/Odometry` |
| `/tf` | Gazebo → ROS | DiffDrive's `odom → base_link`, only with `ekf:=false` |
| `/joint_states` | Gazebo → ROS | road wheel joints |
| `/scan` | Gazebo → ROS | `sensor_msgs/LaserScan`, frame `laser` |
| `/front_camera/color/image_raw`, `/front_camera/color/camera_info` | Gazebo → ROS | colour image, frame `front_camera_color_optical_frame` |
| `/front_camera/aligned_depth_to_color/image_raw`, `.../camera_info` | Gazebo → ROS | depth aligned to the colour image, 32FC1 in metres |
| `/front_camera/imu` | Gazebo → ROS | `sensor_msgs/Imu`, frame `front_camera_imu_optical_frame` |

## The simulated robot

- **Tracks:** each track is a row of 4 road wheels (collision only, so it still looks like a track) driven by Gazebo's `DiffDrive` system. This works on flat ground. Stairs need the `TrackedVehicle` system instead (#84).
- **Turning skids, like the real tracks.** The front and back wheels drag sideways, so the robot turns about 1.4× less than its wheel speeds suggest. DiffDrive is given the **effective** track separation (`track_skid_factor` in `gazebo.urdf.xacro`), the same calibration #57 does on the real robot. With it, `/odom` matches the true pose within a few degrees per half turn. The EKF takes turns from the gyro instead, so its heading doesn't depend on this calibration; it matters with `ekf:=false`, since slam_toolbox adds no scans while the robot turns on the spot.
- **LiDAR:** set up like the RPLIDAR A2M8 with `rplidar_ros`: 360°, 10 Hz, 800 points per scan, 0.15–12 m, 1 cm noise.
- **Front camera (RealSense D435i):** set up like `realsense2_camera` with `qirc_perception/config/front_camera.yaml`, so the same nodes run on both:
  - **Images:** colour and aligned depth at 848×480, 30 fps, 69°×42° (the colour camera's view, which aligned depth is cropped to on the real camera too). Depth from 0.195 m (the D435i's minimum at this resolution) to 10 m.
  - **IMU:** 200 Hz, gyro and accelerometer, no orientation, in the real IMU's optical axes. Noise from the Bosch BMI055 datasheet, plus a random gyro bias for each run (≈ 0.5°/s, an estimate until it's measured on the real camera), which `imu_bias` removes.
  - **Frames:** `front_camera_color_optical_frame` and `front_camera_imu_optical_frame` are in the simulated model at the offsets from Intel's `realsense2_description`. On the real robot the driver publishes them (#22).
  - **Not simulated:** stereo depth artefacts (holes on dark, shiny or plain surfaces, noise that grows with distance; simulated depth is exact), motion blur, and the IMU's timing offset from the images.

Wheel count, friction, LiDAR and camera settings are properties at the top of each section of `gazebo.urdf.xacro`.

## Notes

- `/joint_states` arrives at 1 kHz (every physics step); Fortress's JointStatePublisher can't be slowed down. `robot_state_publisher` limits its TF output to 20 Hz anyway.
- When stopping with Ctrl-C, Gazebo can take a few seconds to exit. If you stop the launch some other way (e.g. `kill` on just the `ros2 launch` process), check that no `ign gazebo` process is left over: `pgrep -af "ign gazebo"`.
