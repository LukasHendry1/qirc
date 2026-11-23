# Seeed Studio Grove WS2813 RGB LED strip (30 LED/m, 1 m)

**Used for:** the status LEDs.

**Product:** Seeed Studio part 104020108; RobotShop SKU RB-See-983, US$10.20. The strip is waterproof and has a Grove connector. Specs are from the RobotShop product page (provided by hand on 2026-11-23), except where marked.

## Specifications

| Parameter | Value |
|---|---|
| LED type | WS2813, individually addressable RGB (one data line, 24-bit colour per LED) |
| LEDs | 30 (30 LED/m × 1 m) |
| Operating voltage | 5 V DC |
| Current, maximum | 0.06 A per LED; 1.8 A per metre (all LEDs full white) |
| Power, maximum | 0.3 W per LED; 9 W per metre |
| Max. data rate | 800 kbps |
| Reset time | > 280 µs (typical 300 µs) |
| PWM (scanning) frequency | 2 kHz |
| Operating temperature | −40 to 70 °C |
| Storage temperature | −50 to 80 °C |
| LED life | 50 000 h |
| Cable length | 1 m |
| Weight | 41 g |

## Connector (Grove, 4-pin)

The page doesn't list the pinout. This is the standard Grove digital pinout, so check it against the strip.

| Pin | Wire | Signal |
|---|---|---|
| 1 | Yellow | Data in (DIN) |
| 2 | White | Not connected |
| 3 | Red | 5 V |
| 4 | Black | GND |

## Notes for QIRC

- **Power budget** *(derived)*: at most 1.8 A / 9 W, with every LED on full white. Status colours at partial brightness draw much less. The 5 V buck in the wiring diagram (3 A minimum) covers it.
- **Logic level:** the WS2813's data-high threshold is about 0.7 × VDD, which is 3.5 V at 5 V. The Pico's 3.3 V output is below that. It often works, but isn't guaranteed. A 74AHCT125 level shifter (or similar) on the data line makes it reliable.
- **Resilience:** the WS2813 has a backup data input, so one dead LED doesn't stop the LEDs after it. The Grove cable carries only the main data line.
- **Wiring diagram:** `power.yml` still names the status LEDs "WS2812B". The WS2813 uses the same timing and protocol, so the 5 V and data connections don't change.

## Source

- RobotShop product page: "Seeedstudio Grove WS2813 RGB LED Strip Waterproof 30 LED/m - 1m" (SKU RB-See-983).

Compiled 2026-11-23.
