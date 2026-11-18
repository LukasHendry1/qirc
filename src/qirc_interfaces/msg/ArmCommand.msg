# Target positions for the arm motors.
# Published by pill_dispenser on /arm/command; qirc_pico_bridge forwards it to the Pico.
# The measured positions come back on /arm/joint_states (sensor_msgs/JointState).
#
# No homing: positions count from power-on, so the arm must be at rest when
# the robot is switched on (see docs/architecture/messages.md).

std_msgs/Header header
float64[2] position     # rad, target per arm motor (same order as /arm/joint_states)
float32 max_speed       # rad/s
bool enable             # false = motor drivers off
