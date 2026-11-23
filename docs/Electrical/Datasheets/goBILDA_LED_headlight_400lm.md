# goBILDA / ServoCity LED headlight (400 lumens, 5–30 V input)

**Used for:** the headlights.

**Product:** goBILDA part 3118-0102-0002. ServoCity sells it under the same part number, and RobotShop as SKU RB-Sct-3594, at US$21.99 (goBILDA) or $31.41 (RobotShop).

**Sources:**
- [goBILDA product page](https://www.gobilda.com/led-headlight-400-lumens-5-30v-input/)
- RobotShop product page (provided by hand on 2026-11-23)
- [STEP model (zip)](https://www.gobilda.com/content/step_files/3118-0102-0002.zip)

No datasheet PDF is published.

## Specifications

| Parameter | Value |
|---|---|
| Light output | 400 lumens, wide ("extreme flood") beam |
| Input voltage | 5–30 V DC (recommended range) |
| Power connector | XT30 input and XT30 output. The output passes the input through, so headlights can be daisy-chained, or power passed on to other components. |
| Mounting | goBILDA 32 mm square hole pattern; hex counterbores hold 7 mm hex hardware (M4 locknuts) |
| Weight | 37 g, including the mounting hardware |
| Included | 4× M4 × 20 mm socket head screws, 4× M4 × 0.7 mm Nylock nuts |

## Not published

goBILDA doesn't publish these, so measure them on the bench:
- current and power draw at 24 V
- beam angle
- colour temperature
- water resistance
- whether it dims with PWM

The goBILDA page shows a schematic and a view sheet only as images, and the STEP file gives the exact dimensions.

goBILDA sells a separate PWM-dimmable version of this headlight. That this one isn't marketed as dimmable suggests it has a constant-current driver inside. In that case it should be switched on and off (e.g. through a MOSFET from the Pico, as the wiring diagram shows) rather than dimmed with PWM.

## Notes for QIRC *(estimated)*

- **Estimated power:** a 400 lm LED module typically draws about 4–5 W, which is about 0.2 A per headlight at 24 V. Replace this with a measured value for the power calculations.
- **Polarity:** XT30 connectors are keyed, so they can't be plugged in backwards. Check the polarity of any XT30 lead you make yourself.
- **Wiring diagram:** the diagram's "Headlights (12–24 V LED)" entry matches, since 24 V is within the 5–30 V range.

Compiled 2026-11-23.
