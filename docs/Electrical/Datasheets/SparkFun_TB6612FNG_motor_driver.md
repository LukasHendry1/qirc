# SparkFun TB6612FNG dual motor driver

**Used for:** both arm motors (Yahboom MD520Z19), one per channel, on the 12 V arm rail.

**Board:** SparkFun Motor Driver, Dual TB6612FNG (1A), current SKU ROB-14451. This one was given to the team, so its exact version is unknown. Check the silkscreen. The chip is Toshiba's TB6612FNG.

**Sources:**
- [Toshiba TB6612FNG datasheet (2007-06-30)](https://cdn.sparkfun.com/datasheets/Robotics/TB6612FNG.pdf), as hosted by SparkFun. Chip values come from here.
- [SparkFun product page](https://www.sparkfun.com/products/14451). Board values come from here.

## Specifications (Toshiba datasheet unless noted)

| Parameter | Value |
|---|---|
| Channels | 2 H-bridges (A and B), one motor each |
| Motor supply VM, operating | 4.5–13.5 V (5 V typical) |
| Motor supply VM, absolute max | 15 V |
| Logic supply VCC | 2.7–5.5 V |
| Output current, operating | **1.0 A max per channel** (VM ≥ 5 V) |
| Output current, absolute max | 1.2 A average per channel; 2 A for 20 ms pulses at ≤ 20% duty; **3.2 A for a single 10 ms pulse** |
| Voltage drop (upper + lower FET) | 0.5 V typ (0.7 V max) at 1 A; 0.15 V typ at 0.3 A |
| PWM frequency | 100 kHz max |
| Logic input high / low | ≥ 0.7 × VCC / ≤ 0.3 × VCC (≥ 2.31 V / ≤ 0.99 V at 3.3 V) |
| Logic supply current | 1.1 mA typ at VCC = 3 V; ≤ 1 µA in standby |
| VM current in standby | ≤ 1 µA |
| Protection | Thermal shutdown at 175 °C (20 °C hysteresis); low-voltage detection on VCC (1.9 V, recovers at 2.2 V). No overcurrent protection. |
| Board | 0.8 × 0.8 in; supply decoupling capacitors fitted (SparkFun) |

## Control

Each channel has IN1, IN2 and PWM inputs, and STBY is shared by both. All inputs have 200 kΩ pull-downs, so the board sits in standby until STBY is driven high.

| IN1 | IN2 | PWM | STBY | Output | Mode |
|---|---|---|---|---|---|
| H | L | H | H | OUT1 H, OUT2 L | CW |
| L | H | H | H | OUT1 L, OUT2 H | CCW |
| H/L | H/L (same) | H | H | — | H-H: short brake; L-L: stop (outputs off) |
| any | any | L | H | both L | Short brake |
| any | any | any | L | outputs off | Standby |

Speed is set by PWM on the PWM pin, with IN1/IN2 giving the direction. During the off part of each PWM cycle the bridge brakes rather than coasting.

## Pins (SparkFun board; check against the silkscreen)

| Inputs side | Outputs side |
|---|---|
| PWMA | VM (12 V arm rail) |
| AIN2 | VCC (3.3 V from the Pico) |
| AIN1 | GND |
| STBY | AO1 (arm motor 1) |
| BIN1 | AO2 (arm motor 1) |
| BIN2 | BO2 (arm motor 2) |
| PWMB | BO1 (arm motor 2) |
| GND | GND |

That's 7 Pico GPIOs in all: PWMA, AIN1, AIN2, PWMB, BIN1, BIN2 and STBY.

## Notes for QIRC

The board is comfortable with the arm motors when they're running, but it can't survive a held stall.

| | Arm motor (MD520Z19 at 12 V) | TB6612FNG per channel |
|---|---|---|
| Running | 0.3 A rated | 1.0 A operating ✅ |
| Starting or stalled | 3 A | 3.2 A for 10 ms ⚠️ |

The firmware needs to protect it:

1. **Cap the PWM duty.**
   - The winding is about 4 Ω (12 V ÷ 3 A), so the average stall current is roughly duty × 3 A.
   - A cap of **≤ 33% duty** keeps a stall at about 1 A, within the operating rating, and still gives about 180 rpm at the output.
   - Raise the cap only if the arm needs more speed or torque, and only together with step 2.
2. **Detect stalls.** If a channel is driven but its encoder count doesn't change for about 50–100 ms, set its PWM to 0. The arm has no limit switches yet (#50), so hitting the end of travel is the likely stall.
3. **Ramp the PWM** up from zero rather than stepping it, to limit the starting current.
4. **Keep VM at 12 V.** It must never be connected to the 24 V rail, because 15 V is the absolute maximum. The buck's output must not overshoot past 13.5 V.

**Holding:** check on the bench how much current it takes to hold the arm up against gravity. It needs to stay under 1 A per motor. If it doesn't, either use short brake to hold, or choose a bigger driver.

**Power (derived):** at 0.3 A per motor, the driver loses about 0.15 V × 0.3 A ≈ 0.05 W per channel, which is negligible. Its logic draws about 1 mA at 3.3 V.

Compiled 2026-11-23.
