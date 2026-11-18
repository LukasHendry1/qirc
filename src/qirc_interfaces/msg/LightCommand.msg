# Status LED pattern and headlight level for the robot.
# Published by vehicle_manager on /lights; qirc_pico_bridge forwards it to the Pico.

# status_pattern values
uint8 IDLE=0        # robot asleep / waiting
uint8 BUSY=1        # running a mission
uint8 ATTENTION=2   # needs the user (e.g. pills ready to take)
uint8 ERROR=3       # error or E-stop

uint8 status_pattern
float32 headlight_brightness    # 0.0 (off) to 1.0 (full)
