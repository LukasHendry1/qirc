"""
Launch the full QIRC software stack, on the real robot or in simulation.

    ros2 launch qirc_bringup qirc.launch.py                  # real robot
    ros2 launch qirc_bringup qirc.launch.py use_sim:=true    # Gazebo

On the real robot, starts robot_state_publisher (the robot model and its
static TF, from qirc_description) and the sensor drivers.

With use_sim:=true, starts the Gazebo simulation instead (qirc_gazebo's
sim.launch.py). It publishes the robot model, and the simulated sensors on
the same topics and frames as the real drivers. It also runs the EKF, so
the rest of the stack runs unchanged, on simulation time. There is no
simulated rear camera, so rear_detection doesn't run.

Arguments:
    use_sim (default false): run in Gazebo instead of on the hardware, and
        use the simulation clock in every node.
    world (default obstacles.sdf), headless (default false), odometry
        (default encoders; lidar to run without encoders): passed to
        sim.launch.py with use_sim:=true.
    use_front_camera (default true): start the front RealSense driver.
        Set to false when developing without the camera plugged in.
    use_rear_camera (default true): start the rear OAK-D Lite driver.
        Set to false when developing without the camera plugged in.
    use_lidar (default true): start the RPLidar driver.
        Set to false when developing without the LiDAR plugged in.
    use_front_detection (default true): run YOLO on the front camera.
        Needs Ultralytics (src/qirc_perception/README.md); set to false if
        it isn't installed.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

NODES = [
    ('qirc_planning', 'vehicle_manager_node'),
    ('qirc_planning', 'global_planner_node'),
    ('qirc_planning', 'local_planner_node'),
    ('qirc_pill_dispenser', 'pill_box_node'),
    ('qirc_pill_dispenser', 'arm_node'),
]


def _launch_file(package, name):
    return PythonLaunchDescriptionSource(PathJoinSubstitution([
        FindPackageShare(package), 'launch', name,
    ]))


def _on_hardware_if(argument):
    """Run only on the real robot (use_sim:=false), and only if argument is true."""
    return IfCondition(PythonExpression([
        "'", LaunchConfiguration(argument), "' == 'true' and '",
        LaunchConfiguration('use_sim'), "' != 'true'",
    ]))


def generate_launch_description():
    use_sim = LaunchConfiguration('use_sim')
    # Every node runs on the simulation clock in simulation.
    use_sim_time = {'use_sim_time': ParameterValue(use_sim, value_type=bool)}

    # ===== Hardware or simulation ==========================================
    simulation = IncludeLaunchDescription(
        _launch_file('qirc_gazebo', 'sim.launch.py'),
        launch_arguments={
            'world': LaunchConfiguration('world'),
            'headless': LaunchConfiguration('headless'),
            'odometry': LaunchConfiguration('odometry'),
        }.items(),
        condition=IfCondition(use_sim),
    )
    # The simulation publishes its own robot model (with sim:=true).
    robot_description = IncludeLaunchDescription(
        _launch_file('qirc_description', 'description.launch.py'),
        condition=UnlessCondition(use_sim),
    )
    front_camera = IncludeLaunchDescription(
        _launch_file('qirc_perception', 'front_camera.launch.py'),
        condition=_on_hardware_if('use_front_camera'),
    )
    rear_camera = IncludeLaunchDescription(
        _launch_file('qirc_perception', 'rear_camera.launch.py'),
        condition=_on_hardware_if('use_rear_camera'),
    )
    lidar = IncludeLaunchDescription(
        _launch_file('qirc_localization', 'lidar.launch.py'),
        condition=_on_hardware_if('use_lidar'),
    )

    # ===== The rest of the stack: the same on both =========================
    front_detection = Node(
        package='qirc_perception',
        executable='front_detection_node',
        parameters=[
            PathJoinSubstitution([
                FindPackageShare('qirc_perception'), 'config', 'front_detection.yaml']),
            use_sim_time,
        ],
        output='screen',
        condition=IfCondition(LaunchConfiguration('use_front_detection')),
    )
    # The OAK-D Lite runs the detector itself; there is none in simulation.
    rear_detection = Node(
        package='qirc_perception',
        executable='rear_detection_node',
        parameters=[
            PathJoinSubstitution([
                FindPackageShare('qirc_perception'), 'config', 'rear_detection.yaml']),
            use_sim_time,
        ],
        output='screen',
        condition=UnlessCondition(use_sim),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim', default_value='false',
            description='Run in Gazebo instead of on the hardware (simulation clock)'),
        DeclareLaunchArgument(
            'world', default_value='obstacles.sdf',
            description='Gazebo world in qirc_gazebo/worlds (use_sim:=true only)'),
        DeclareLaunchArgument(
            'headless', default_value='false',
            description='Run Gazebo without its GUI (use_sim:=true only)'),
        DeclareLaunchArgument(
            'odometry', default_value='encoders', choices=['encoders', 'lidar'],
            description='Speed source for the EKF: encoders or lidar (use_sim:=true only)'),
        DeclareLaunchArgument(
            'use_front_camera', default_value='true',
            description='Start the front RealSense driver (false if no camera attached)'),
        DeclareLaunchArgument(
            'use_rear_camera', default_value='true',
            description='Start the rear OAK-D Lite driver (false if no camera attached)'),
        DeclareLaunchArgument(
            'use_lidar', default_value='true',
            description='Start the RPLidar driver (false if no LiDAR attached)'),
        DeclareLaunchArgument(
            'use_front_detection', default_value='true',
            description='Run YOLO on the front camera (needs Ultralytics installed)'),
        simulation,
        robot_description,
        front_camera,
        rear_camera,
        lidar,
        front_detection,
        rear_detection,
        *[Node(package=pkg, executable=exe, parameters=[use_sim_time], output='screen')
          for pkg, exe in NODES],
    ])
