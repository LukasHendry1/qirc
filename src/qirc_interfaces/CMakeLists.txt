cmake_minimum_required(VERSION 3.8)
project(qirc_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(std_msgs REQUIRED)

# Field definitions and which node uses each interface:
# docs/architecture/messages.md
set(msg_files
  "msg/ArmCommand.msg"
  "msg/DispenserCommand.msg"
  "msg/DispenserState.msg"
  "msg/LightCommand.msg"
  "msg/PillScheduleEntry.msg"
  "msg/RobotState.msg"
  "msg/UserInfo.msg"
)

set(srv_files
  "srv/GetSchedule.srv"
  "srv/SetSchedule.srv"
)

set(action_files
  "action/DispensePills.action"
  "action/MoveArm.action"
  "action/SearchForUser.action"
)

rosidl_generate_interfaces(${PROJECT_NAME}
  ${msg_files}
  ${srv_files}
  ${action_files}
  DEPENDENCIES builtin_interfaces geometry_msgs std_msgs
)

ament_export_dependencies(rosidl_default_runtime)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # No hand-written source files to check for copyright or C++ style.
  set(ament_cmake_copyright_FOUND TRUE)
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
