# Yahboom 520 DC gear motor with encoder (MD520)

**Used for:** the arm motors (×2).

**Manufacturer:** Yahboom. Yahboom doesn't publish a downloadable datasheet for this motor. This sheet is compiled from the sources listed at the end.

**Variants:** three, which differ only in their gearbox. The number on the label (e.g. 333RPM) identifies the variant.

| Variant | Gear ratio | Output speed |
|---|---|---|
| MD520Z19_12V | 1:19 | 550 rpm |
| MD520Z30_12V | 1:30 | 333 rpm |
| MD520Z56_12V | 1:56 | 205 rpm |

> **TODO:** record which variant the arm uses: ______

## Electrical

| Parameter | MD520Z19 | MD520Z30 | MD520Z56 |
|---|---|---|---|
| Motor type | Permanent-magnet brushed DC | ← | ← |
| Rated voltage | 12 V | 12 V | 12 V |
| Operating voltage range | 11–16 V (12 V recommended) | ← | ← |
| Rated current | 0.3 A | 0.3 A | 0.3 A |
| Stall current | 3 A | 3 A | 4 A |
| Rated power | ≤ 4 W | ≤ 4 W | ≤ 4 W |
| Stall power at 12 V *(derived: 12 V × stall current)* | 36 W | 36 W | 48 W |

## Mechanical

| Parameter | MD520Z19 | MD520Z30 | MD520Z56 |
|---|---|---|---|
| Gearbox | All-metal spur gears | ← | ← |
| Reduction ratio | 1:19 | 1:30 | 1:56 |
| Motor speed (before gearbox) | 11000 rpm | 11000 rpm | 12000 rpm |
| Output speed (after gearbox)¹ | 550 ± 10 rpm | 333 ± 10 rpm | 205 ± 10 rpm |
| Rated torque | 2.2 kg·cm (0.216 N·m) | 3.3 kg·cm (0.324 N·m) | 6.5 kg·cm (0.638 N·m) |
| Stall torque | 3.1 kg·cm (0.304 N·m) | 4.8 kg·cm (0.471 N·m) | 8.3 kg·cm (0.814 N·m) |
| Output shaft | 6 mm D-shaft, offset from the motor axis | ← | ← |
| Weight | 150 ± 1 g | 150 ± 1 g | 150 ± 1 g |

¹ The output speed is the motor speed divided by the gear ratio (for example 11000 / 30 ≈ 367 rpm), so this is most likely the **no-load** speed, not the speed under rated load.

N·m values are converted at 1 kg·cm = 0.0981 N·m.

## Encoder

| Parameter | Value |
|---|---|
| Type | Incremental Hall encoder, quadrature A/B outputs |
| Supply voltage | 3.3–5 V (supply it from 3.3 V for the Pico, whose pins aren't 5 V tolerant) |
| Magnet ring | 11 lines (11 pulses per motor revolution, per channel) |
| Output | Square wave, with a built-in pull-up and signal shaping, so a microcontroller can read it directly |
| Counts per motor revolution *(derived: 11 × 4 edges)* | 44 |
| Counts per output revolution *(derived: 44 × gear ratio)* | Z19: 836; Z30: 1320; Z56: 2464 |

Counts per output revolution should be checked on the real motor: turn the output shaft exactly 10 turns by hand and divide the count by 10.

## Connector

- **Type:** PH2.0, 6 pins. It carries both the motor and the encoder.
- **Cable:** Yahboom recommends its black PH2.0-6pin double-ended cable.
- **Pinout:** Yahboom doesn't list it in text. Read it from the label on the motor's encoder board and record it here.

| Pin | Signal |
|---|---|
| 1 | ______ |
| 2 | ______ |
| 3 | ______ |
| 4 | ______ |
| 5 | ______ |
| 6 | ______ |

**Phase naming:** Yahboom notes that the motor's "A" output goes to the "B" input of its own driver boards. Phase naming isn't consistent, so check the count direction in software rather than relying on the labels.

## Not published

Yahboom doesn't publish these. Measure them if they're needed:
- no-load current
- overall dimensions, and the size and spacing of the mounting holes
- shaft length
- gearbox backlash

A 3D model may be in Yahboom's "Model File" download, linked from the tutorial page.

## Sources

- **Product page:** [yahboom.store/products/md520](https://www.yahboom.store/products/md520). It blocks automated access, so its contents haven't been checked against this sheet.
- **Spec table:** [Yahboom tutorial, "Motor introduction and usage"](https://www.yahboom.net/study/MD520/14105). All the specs above come from it.
- [Yahboom tutorial index (downloads)](https://www.yahboom.net/study/MD520)
- [YahboomTechnology/520-DC-Motor on GitHub](https://github.com/YahboomTechnology/520-DC-Motor). This is the source for the encoder's built-in pull-up and shaping, and for the carbon brushes and all-metal gears.

Compiled 2026-11-23.
