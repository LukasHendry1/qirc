"""
Work out the battery capacity (Ah) for run times from 30 minutes to 6 hours.

    pip install pypdf reportlab
    python3 docs/Electrical/calculations/battery_capacity.py

Writes battery_capacity.pdf (calculation sheet PWR-02) next to this script,
on the same template and grid as power_draw.py (PWR-01), whose totals it
starts from. Unlike power_draw.py, the numbers here are computed, so changing
an input below updates every line that uses it.
"""

from pathlib import Path

from power_draw import HEADER, write_sheets

OUTPUT = Path(__file__).resolve().parent / 'battery_capacity.pdf'

# ----- Inputs -------------------------------------------------------------
# From PWR-01 (power_draw.py), typical values in W.
P_24V_DRIVING = 140.76      # 24 V motor rail, drive motors at rated load
P_DRIVE_MOTORS = 124.80     # the two drive motors at rated load
P_19V = 25.75               # Jetson + USB devices
P_12V = 7.29                # arm rail
P_5V = 3.00                 # status LEDs

V_NOMINAL = 25.6            # 8S LiFePO4, from the wiring diagram
DOD = 0.80                  # use 80% of the capacity
EFFICIENCY = 0.90           # DC-DC converters (Est.: not chosen yet)
DRIVING_SHARE = 0.25        # mission mix (Est.): driving 25% of the time

HOURS = [0.5, 1, 2, 3, 4, 5, 6]
PLANNED_AH = 10             # battery in the wiring diagram

# ----- Calculation --------------------------------------------------------
p_conv = P_19V + P_12V + P_5V
p_24v_standing = P_24V_DRIVING - P_DRIVE_MOTORS
p_driving = P_24V_DRIVING + p_conv / EFFICIENCY
p_standing = p_24v_standing + p_conv / EFFICIENCY
p_mix = DRIVING_SHARE * p_driving + (1 - DRIVING_SHARE) * p_standing
usable_wh_per_ah = V_NOMINAL * DOD
CASES = (p_driving, p_mix, p_standing)


def ah(power, hours):
    return power * hours / usable_wh_per_ah


def _duration(h):
    return '30 min (0.5 h)' if h == 0.5 else f'{h:g} hour' + ('s' if h != 1 else '')


planned_usable = PLANNED_AH * usable_wh_per_ah

SHEET = [
    ('title', 'Method'),
    ('text', 'Capacity needed:  C (Ah) = P_battery × t / (V_nominal × DoD)'),
    ('text', 'P_battery is the power the battery supplies, including the DC-DC converter losses.'),
    ('text', f'V_nominal = {V_NOMINAL} V (8S LiFePO4, from the wiring diagram).'),
    ('text', f'DoD = {DOD:.2f}: plan to use {DOD:.0%} of the capacity, leaving margin for ageing, cold and battery life.'),
    ('text', f'Converter efficiency η = {EFFICIENCY:.2f} (Est.: the 19 V, 12 V and 5 V converters are not chosen).'),
    (),
    ('title', 'Power drawn from the battery (typical values from PWR-01)'),
    ('cols', '24 V (W)', 'Conv. (W)', 'Battery (W)'),
    ('item', 'Driving (drive motors at rated load)', P_24V_DRIVING, p_conv, p_driving),
    ('item', f'Mission mix (Est.): {DRIVING_SHARE:.0%} driving, {1 - DRIVING_SHARE:.0%} standing', None, None, p_mix),
    ('item', 'Standing still (drive motors off)', p_24v_standing, p_conv, p_standing),
    ('text', f'Converter loads: 19 V {P_19V:.2f} + 12 V {P_12V:.2f} + 5 V {P_5V:.2f} = {p_conv:.2f} W'),
    ('text', f'Driving: P = P_24V + P_conv / η = {P_24V_DRIVING:.2f} + {p_conv:.2f} / {EFFICIENCY:.2f} = {p_driving:.2f} W'),
    ('text', f'Standing: 24 V rail {P_24V_DRIVING:.2f} - {P_DRIVE_MOTORS:.2f} = {p_24v_standing:.2f} W;'
             f'  P = {p_24v_standing:.2f} + {p_conv / EFFICIENCY:.2f} = {p_standing:.2f} W'),
    ('text', f'Mix: {DRIVING_SHARE:.2f} × {p_driving:.2f} + {1 - DRIVING_SHARE:.2f} × {p_standing:.2f} = {p_mix:.2f} W'),
    (),
    ('title', f'Capacity needed (Ah at {V_NOMINAL} V, {DOD:.0%} depth of discharge)'),
    ('text', f'Usable energy per Ah: {V_NOMINAL} V × {DOD:.2f} = {usable_wh_per_ah:.2f} Wh.  Ah for 1 hour = P / {usable_wh_per_ah:.2f}:'),
    ('text', f'driving {p_driving:.2f} / {usable_wh_per_ah:.2f} = {ah(p_driving, 1):.2f} Ah;'
             f'  mix {ah(p_mix, 1):.2f} Ah;  standing {ah(p_standing, 1):.2f} Ah.  × hours for each run time.'),
    ('cols', 'Driving (Ah)', 'Mix (Ah)', 'Standing (Ah)'),
    *[('item', _duration(h), *(ah(p, h) for p in CASES)) for h in HOURS],
    (),
    ('title', f'Check: the {PLANNED_AH} Ah battery in the wiring diagram'),
    ('text', f'{PLANNED_AH} Ah × {V_NOMINAL} V = {PLANNED_AH * V_NOMINAL:.0f} Wh;  usable × {DOD:.2f} = {planned_usable:.1f} Wh.'
             f'  Run time = {planned_usable:.1f} Wh / P:'),
    ('text', f'driving {planned_usable / p_driving:.2f} h;  mix {planned_usable / p_mix:.2f} h;'
             f'  standing {planned_usable / p_standing:.2f} h'),
    ('text', f'Current: driving {p_driving:.1f} W / {V_NOMINAL} V = {p_driving / V_NOMINAL:.1f} A; both drive motors stalled'
             ' ~43 A (PWR-01).'),
    ('text', 'So whatever capacity is chosen, the BMS must allow 40 A or more continuous.'),
    ('text', 'Pick the next standard size up from the table (e.g. 10, 15, 20, 30, 50 Ah).'),
]

HEADER_PWR02 = dict(
    HEADER,
    **{'No.': (362, 92.75, 'PWR-02'),
       'Subject': (80, 143.0, 'Battery capacity (Ah) for 0.5 - 6 h run time')},
)


def main():
    write_sheets([SHEET], OUTPUT, HEADER_PWR02)


if __name__ == '__main__':
    main()
