# DRV8825 stepper driver module (StepStick)

**Used for:** the dispenser steppers (×2), one module per motor.

**Product:** SazkJere 6-pack with heat sinks, from Amazon.ca (ASIN B0BLKPQ5NY, part SJ15). This is a clone of [Pololu's DRV8825 carrier](https://www.pololu.com/product/2133), with the same size, pinout and interface. The chip is Texas Instruments' DRV8825.

**Official chip datasheet:** [TI DRV8825 datasheet, SLVSA73F (rev. F, July 2014)](https://www.ti.com/lit/ds/symlink/drv8825.pdf).

Board-level values below come from Pololu's carrier page and the Amazon listing; chip values come from the TI datasheet.

## Specifications

| Parameter | Value | Source |
|---|---|---|
| Motor supply (VMOT) | 8.2–45 V | Pololu, TI |
| Undervoltage lockout | 7.8 V typ, 8.2 V max (VM rising) | TI |
| Current per phase, no heat sink or airflow | ~1.5 A | Pololu |
| Current per phase, with enough cooling | 2.2 A (board sense resistors); chip rated 2.5 A | Pololu, Amazon |
| Overcurrent trip | 3 A min | TI |
| Thermal shutdown | 150 °C min, 160 °C typ (die) | TI |
| FET on-resistance (each, high or low side) | 0.2 Ω typ at 25 °C; 0.25 Ω typ, 0.32 Ω max at 85 °C | TI |
| VM supply current, operating | 5 mA typ, 8 mA max (at 24 V) | TI |
| VM supply current, sleep | 10 µA typ, 20 µA max (at 24 V) | TI |
| Logic supply | None needed (built-in regulator) | Pololu |
| Logic inputs | Work with 3.3 V and 5 V; VIL ≤ 0.7 V, VIH 2.2–5.25 V | TI, Pololu |
| Max STEP frequency | 250 kHz | TI |
| Min STEP pulse | 1.9 µs high and 1.9 µs low | Pololu |
| Chopping (PWM) frequency | 30 kHz | TI |
| Microstepping | Full, 1/2, 1/4, 1/8, 1/16, 1/32 | Amazon, TI |
| Protection | Overtemperature, overcurrent, undervoltage lockout, short-to-ground, shorted load | Amazon, TI |
| Board | 4-layer, 2 oz copper PCB; 16-pin 0.1" header | Amazon, Pololu |

## Pinout (standard StepStick layout)

Pololu's page shows the pinout only as an image. This is the standard StepStick layout; check it against the silkscreen.

| Left side | Right side |
|---|---|
| EN (ENABLE, active low) | VMOT |
| M0 | GND (motor) |
| M1 | B2 |
| M2 | B1 |
| RST (RESET, active low) | A1 |
| SLP (SLEEP, active low) | A2 |
| STEP | FLT (FAULT) |
| DIR | GND (logic) |

**Default states:**
- **RESET and SLEEP** must both be high for the driver to run. SLEEP is pulled low inside the chip by default. Tie RESET and SLEEP together and drive them high, or pull them high. Any external pull-up on SLEEP should be 4.7 kΩ or less.
- **ENABLE** has a pull-down, so the outputs are enabled by default. Drive it high to switch them off.
- **M0–M2, STEP and DIR** have pull-downs. Left open, the board runs in full-step mode.
- **FAULT** goes low on overcurrent or overtemperature.

## Step resolution

| M0 | M1 | M2 | Resolution | Microsteps per rev (1.8° motor) |
|---|---|---|---|---|
| L | L | L | Full | 200 |
| H | L | L | 1/2 | 400 |
| L | H | L | 1/4 | 800 |
| H | H | L | 1/8 | 1600 |
| L | L | H | 1/16 | 3200 |
| H | L | H | 1/32 | 6400 |

The combinations L-H-H and H-H-H also give 1/32.

## Setting the current limit

**Current limit = 2 × V_ref.** This holds for 0.100 Ω sense resistors, which are marked "R100" on the board. Clones sometimes use a different value, so check the marking. V_ref is measured between the potentiometer and GND.

| Target current per phase | V_ref |
|---|---|
| 1.2 A | 0.60 V |
| 1.3 A | 0.65 V |
| 1.5 A | 0.75 V (about the most without a heat sink) |

The roadmap uses **1.2–1.5 A**, below the stepper's 2 A rating. That keeps the driver within its no-heat-sink range, and the supplied heat sinks give extra margin.

## Wiring notes

- **Capacitor:** fit a **≥ 47 µF electrolytic capacitor across VMOT and GND, close to the board.** The wiring diagram specifies 100 µF 50 V. Without it, LC voltage spikes when power is connected can exceed 45 V and destroy the driver, even on a 12 V supply.
- **Hot-plugging:** never connect or disconnect the motor while the driver is powered.

## Notes for QIRC *(derived)*

- **Driver loss:** TI gives P = 4 × R_DS(on) × I_rms², with I_rms ≈ 0.7 × the current limit.
  - At 1.3 A: I_rms ≈ 0.91 A, so P ≈ 0.66 W at 25 °C, or ~0.83 W at 85 °C.
  - Add VM's own draw: 24 V × 5 mA ≈ 0.12 W.
- **Idle:** SLEEP drops the driver to ~10 µA and switches the motor current off. The motor then has no holding torque, so check the dispenser can't move while unpowered.

## Sources

- **Product listing:** Amazon.ca, ASIN B0BLKPQ5NY (provided by hand on 2026-11-23).
- [Pololu DRV8825 stepper motor driver carrier](https://www.pololu.com/product/2133)
- [TI DRV8825 datasheet (SLVSA73F)](https://www.ti.com/lit/ds/symlink/drv8825.pdf)

Compiled 2026-11-23.
