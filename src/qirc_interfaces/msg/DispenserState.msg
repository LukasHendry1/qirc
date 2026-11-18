# State of one pill dispenser's stepper motor, reported by the Pico.
# Published by qirc_pico_bridge on /dispenser/state.
#
# No homing: position counts from power-on, so the dispenser must be at rest
# when the robot is switched on (see docs/architecture/messages.md).

uint8 dispenser_id      # which dispenser (0 or 1)
int32 position          # steps since power-on
bool moving
bool fault              # driver fault reported by the DRV8825
