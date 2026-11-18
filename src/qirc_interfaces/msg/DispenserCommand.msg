# Move one pill dispenser's stepper motor.
# Published by pill_dispenser on /dispenser/command; qirc_pico_bridge forwards it to the Pico.

uint8 dispenser_id      # which dispenser (0 or 1)
int32 steps             # relative move; sign gives the direction
float32 speed           # steps/s
bool enable             # false = stepper driver disabled (less heat and noise when idle)
