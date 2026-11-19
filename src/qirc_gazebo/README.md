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
| `publish_odom_tf` | `true` | Publish DiffDrive's `odom → base_link` on `/tf`. Set to `false` once the EKF (#54) publishes it. |

To see the robot and scan in RViz, run `rviz2` and set the fixed frame to `odom`.

## What it starts

- **Gazebo** with the world, through `ros_gz_sim`
- **`robot_state_publisher`** with the robot model built with `sim:=true` (`qirc_description/urdf/gazebo.urdf.xacro`), on simulation time
- **Spawns the robot** from `/robot_description`
- **`ros_gz_bridge`**, configured in `config/`:

| ROS topic | Direction | Type |
|---|---|---|
| `/clock` | Gazebo → ROS | `rosgraph_msgs/Clock` |
| `/cmd_vel` | ROS → Gazebo | `geometry_msgs/Twist` |
| `/odom` | Gazebo → ROS | `nav_msgs/Odometry` |
| `/tf` | Gazebo → ROS | `odom → base_link`, only with `publish_odom_tf:=true` |
| `/joint_states` | Gazebo → ROS | road wheel joints |
| `/scan` | Gazebo → ROS | `sensor_msgs/LaserScan`, frame `laser` |

## The simulated robot

- **Tracks:** each track is a row of 4 road wheels (collision only, so it still looks like a track) driven by Gazebo's `DiffDrive` system. This works on flat ground. Stairs need the `TrackedVehicle` system instead (#84).
- **Turning skids, like the real tracks.** Driving straight, `/odom` matches the true pose. Turning on the spot, `/odom` overestimates the turn by about 1.4×, because the front and back wheels drag sideways. This is the same problem the real robot has (#57), and slam_toolbox corrects it.
- **LiDAR:** set up like the RPLIDAR A2M8 with `rplidar_ros`: 360°, 10 Hz, 800 points per scan, 0.15–12 m, 1 cm noise.

Wheel count, friction and LiDAR settings are properties at the top of each section of `gazebo.urdf.xacro`.

## Notes

- `/joint_states` arrives at 1 kHz (every physics step); Fortress's JointStatePublisher can't be slowed down. `robot_state_publisher` limits its TF output to 20 Hz anyway.
- When stopping with Ctrl-C, Gazebo can take a few seconds to exit. If you stop the launch some other way (e.g. `kill` on just the `ros2 launch` process), check that no `ign gazebo` process is left over: `pgrep -af "ign gazebo"`.
