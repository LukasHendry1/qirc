# Overall state of the robot, for the web app and anyone else watching.
# Published by vehicle_manager on /robot_state.
#
# Minimal state list for the first version; add states when they are needed
# (e.g. stair climbing, #83).

# state values
uint8 SLEEP=0         # idle, waiting for the next scheduled dose
uint8 SEARCHING=1     # looking for the user (SearchForUser)
uint8 APPROACHING=2   # driving to the user (NavigateToPose)
uint8 DISPENSING=3    # dispensing pills and raising the arm
uint8 RETURNING=4     # driving back home (NavigateToPose)
uint8 ERROR=5         # error or E-stop; see error_message

std_msgs/Header header
uint8 state
string current_task          # human-readable, e.g. "Morning dose: 2 pills"
string error_message         # empty unless state is ERROR
float32 battery_percentage   # 0.0 to 1.0, same convention as sensor_msgs/BatteryState
bool estop                   # true while the E-stop is pressed
