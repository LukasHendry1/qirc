# Wiring diagrams

Wiring diagrams written as [WireViz](https://github.com/wireviz/WireViz) YAML. The `.yml` file is the source; the `.svg`, `.png` and `.bom.tsv` (bill of materials) files are generated from it.

| Diagram | Status |
|---|---|
| [power.yml](power.yml) ([SVG](power.svg)) | Draft: battery, protection, distribution, regulators, motor drivers and USB devices |
| Signals (Pico pin map) | Not started; waits on the Pico pin map |

![Power distribution](power.svg)

## Design decisions

- **E-stop cuts the motor rail only.** The Jetson, Pico and LEDs stay powered, so the robot can log the stop and show it on the status LEDs and web app.
- **24 V system:** 8S LiFePO4 battery (25.6 V nominal, 10 Ah), 24 V drive and arm motors. The DRV8825s and headlights run from the same rail.
- **The Jetson has its own buck-boost converter** with a steady 19 V output, so motor current spikes that dip the battery voltage don't reboot it.
- **40 A main fuse**, sized for both drive motors stalling at once (2 x 21 A) on a battery whose BMS allows 40 A or more.
- **All grounds meet at one common ground bus.**
- **USB devices are powered by the Jetson** (cameras, LiDAR, Pico).

## TBD

- **Drive motor encoders:** the E-S Motor 36PG has none. Odometry needs them.
- **Drive current:** motor stall (21 A) is above the MD10C's 13 A continuous rating (30 A peak), so firmware must limit current or detect stalls.
- **30 V margin:** the MD10C and MDD10A are rated to 30 V and a full 8S LiFePO4 is 29.2 V. Don't drive while charging.
- Battery not bought yet; RPLidar model unknown.

## Editing

```bash
pip install wireviz          # also needs Graphviz: sudo apt install graphviz
wireviz docs/wiring/power.yml
```

Commit the regenerated `.svg`, `.png` and `.bom.tsv` together with the `.yml`. Avoid `->`, `<` and `>` in labels; Graphviz rejects them.
