# ROS 2 Node Graph

How the QIRC nodes connect. Details for each node are in [nodes.md](nodes.md) and for each message in [messages.md](messages.md).

**Legend:**
- `-->` topic
- `==>` action (vehicle manager sends a goal, the server reports progress and a result)
- `-.->` TF transform, published to the TF tree. TF is read by every node that needs positions, so those edges are not drawn.

```mermaid
flowchart LR
    subgraph HW["Hardware"]
        PICO["Pi Pico firmware"]
    end

    subgraph DRV["Sensor drivers (vendor packages)"]
        FC["front_camera<br/>(RealSense D435i)"]
        RC["rear_camera<br/>(OAK-D Lite)"]
        LIDAR["rplidar"]
    end

    subgraph BRIDGE["Hardware bridge"]
        PB["qirc_pico_bridge"]
    end

    subgraph INFRA["Infrastructure (standard packages)"]
        RSP["robot_state_publisher"]
        EKF["ekf<br/>(robot_localization)"]
        MUX["twist_mux"]
        TELEOP["teleop"]
        TF(("TF tree"))
    end

    subgraph PER["Perception"]
        OD["object_detection"]
        UD["user_detection"]
    end

    subgraph LOC["Localization"]
        SLAM["slam_toolbox"]
    end

    subgraph PLAN["Planning and control"]
        VM["vehicle_manager"]
        GP["global_planner"]
        LP["local_planner"]
        CTRL["control (MPC)"]
    end

    subgraph DISP["Pill dispensing"]
        PD["pill_dispenser"]
    end

    subgraph WEB["Web app"]
        RB["rosbridge_server"]
        WVS["web_video_server"]
    end

    %% Hardware
    PB <-->|"USB serial"| PICO

    %% Sensors
    FC -->|"/front_camera/color/image_raw<br/>/front_camera/aligned_depth_to_color/image_raw"| OD
    RC -->|"/rear_camera/nn/spatial_detections"| OD
    FC -->|"/front_camera/imu"| EKF
    LIDAR -->|"/scan"| SLAM
    LIDAR -->|"/scan"| LP
    FC -->|"camera images"| WVS
    RC -->|"camera images"| WVS

    %% Odometry and TF
    PB -->|"/odom"| EKF
    EKF -->|"/odometry/filtered"| CTRL
    RSP -.->|"base_link to sensor frames"| TF
    EKF -.->|"odom to base_link"| TF
    SLAM -.->|"map to odom"| TF

    %% Perception
    OD -->|"/detections"| UD
    OD -->|"/detections"| LP
    UD -->|"/user_info"| VM
    UD -->|"/user_info"| GP
    UD -->|"/user_info"| PD

    %% Planning and control
    SLAM -->|"/map"| GP
    VM ==>|"SearchForUser<br/>NavigateToPose"| GP
    GP -->|"/plan"| LP
    LP -->|"/local_plan"| CTRL
    CTRL -->|"/cmd_vel_nav"| MUX
    TELEOP -->|"/cmd_vel_teleop"| MUX
    RB -->|"/cmd_vel_web"| MUX
    MUX -->|"/cmd_vel"| PB

    %% Safety and status
    PB -->|"/estop"| MUX
    PB -->|"/estop<br/>/battery"| VM
    VM -->|"/lights"| PB
    VM -->|"/robot_state"| RB
    RB -->|"schedule and mission services"| VM

    %% Pill dispensing
    VM ==>|"DispensePills<br/>MoveArm"| PD
    PD -->|"/dispenser/command<br/>/arm/command"| PB
    PB -->|"/dispenser/state<br/>/arm/joint_states"| PD
```

`foxglove_bridge` (development visualization) can see every topic, so it isn't drawn.
