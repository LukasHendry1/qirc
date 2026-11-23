# StepperOnline 17HS19-2004S1 NEMA 17 stepper motor

**Used for:** the pill dispenser (×2), driven by DRV8825 drivers.

**Official datasheet:** [17HS19-2004S1 Full Datasheet (PDF)](https://static.maritex.eu/file/display/5sXxpHH1SP-JwnhJEZ0lhfX-xdYKZRi3/17HS19-2004S1_Full_Datasheet.pdf), StepperOnline drawing A0842, rev 0, dated 2025-08-01. It's linked rather than copied here because its terms don't allow reproducing it. The product page is [omc-stepperonline.com](https://omc-stepperonline.com/nema-17-bipolar-59ncm-84oz-in-2a-42x48mm-4-wires-w-1m-cable-and-connector.html).

**Manufacturer:** OSM Technology Co., Ltd. (StepperOnline). Bought as a 5-pack from Amazon.ca (ASIN B00QEYADRQ).

## Electrical

| Parameter | Value |
|---|---|
| Type | Bipolar, 4 wires, 2 phases |
| Step angle | 1.8° (200 full steps per revolution); accuracy ±5% (non-cumulative) |
| Rated current | 2.0 A per phase |
| Phase resistance | 1.60 Ω ±10% at 25 °C (the Amazon listing says 1.4 Ω; this sheet uses the drawing) |
| Phase inductance | 3.0 mH ±20% at 1 kHz |
| Recommended drive voltage | 12–24 V (24 V suggested), from the product listing |
| Insulation | Class B (130 °C); 100 MΩ insulation resistance; withstands 500 VAC for 1 min |
| Life | 6000 h or more at 24 V and 300 rpm |

> Use it only with a current-limiting (chopper) driver such as the DRV8825. Connected straight to a power supply, the windings draw far more than 2 A and burn out.

## Mechanical

| Parameter | Value |
|---|---|
| Holding torque | 0.59 N·m (59 N·cm, 84 oz·in) |
| Rotor inertia | 82 g·cm² |
| Body | 42.3 × 42.3 mm max (NEMA 17), 48 mm max long |
| Mounting | 4× M3 holes on a 31 ± 0.2 mm square, ≥ 4.5 mm deep; Ø22 mm pilot |
| Shaft | Ø5 mm, 24 ± 1 mm long, with a flat (D-cut) |
| Shaft load | 21 N max at 20 mm from the face |
| Leads | 1000 ± 15 mm, Harwin 2.54 mm 4-pin connector |
| Weight | ~390 g (Amazon); not given on the drawing |
| Temperature | −10 to 50 °C ambient; 80 °C max temperature rise |

## Wiring

| Connector pin | Signal | Wire colour |
|---|---|---|
| 1 | A+ | Black |
| 2 | A− | Green |
| 3 | B+ | Red |
| 4 | B− | Blue |

Black and green form coil A; red and blue form coil B. To reverse the direction, swap the two wires of one coil (or invert DIR in software).

## Notes for QIRC *(derived)*

- **Holding power at 2 A:** 2² × 1.6 Ω = 6.4 W per phase. With both phases energised, that's ~12.8 W per motor, or ~26 W for the two dispenser steppers. This is why the DRV8825s should be disabled when the dispenser is idle.
- **DRV8825 current limit:** the roadmap uses 1.2–1.5 A per phase. Set it with V_ref = I_limit / 2 (e.g. 0.65 V for 1.3 A). Lower current means less heat and less holding torque. Torque scales roughly with current, so about 0.38 N·m at 1.3 A.
- **Supply current:** a chopper drive takes less from the supply than the phase current, about the winding loss plus the mechanical power divided by the supply voltage. At 24 V and 1.3 A per phase, expect roughly 0.3–0.5 A per motor while moving. Measure it to confirm.
- **Steps:** with 1/16 microstepping, 200 × 16 = 3200 steps per output revolution.

Compiled 2026-11-23.
