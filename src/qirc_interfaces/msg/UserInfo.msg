# The user (the person the pills are for), picked out of the person detections.
# Published by user_detection on /user_info.

std_msgs/Header header           # frame_id is the frame of pose (e.g. map)
bool found                       # false: the user is not currently in view
geometry_msgs/Pose pose          # last known pose of the user
float32 height                   # m, estimated standing height (sets the arm height)
float32 confidence               # 0.0 to 1.0
builtin_interfaces/Time last_seen
