"""
Generate the QIRC system architecture diagram (system_architecture.svg).

Same visual style as software_architecture.png, extended to the whole system:
sensors, the ROS 2 software on the Jetson, the Pi Pico firmware, the
actuators, and power distribution.

    python3 docs/architecture/system_architecture.py

Then render the PNG (any SVG renderer works; this uses headless Chrome):

    google-chrome --headless --disable-gpu --hide-scrollbars \
        --window-size=2775,1480 --default-background-color=ffffffff \
        --screenshot=docs/architecture/system_architecture.png \
        docs/architecture/system_architecture.svg
"""

from pathlib import Path
from xml.sax.saxutils import escape

W, H = 2775, 1480
FONT = "Calibri, Carlito, 'Liberation Sans', Arial, sans-serif"

LANE_FILL = '#ECE8F0'
LANE_STROKE = '#7F7F7F'
STACK_STROKE = '#595959'
DATA = '#000000'
POWER = '#C00000'

COLORS = {
    'perception': '#EBF1DE',
    'localization': '#FFF2CC',
    'planning': '#DAEEF3',
    'dispensing': '#F2DCDB',
    'controls': '#FDE9D9',
    'bridge': '#E7E6E6',
    'web': '#E4DFEC',
    'infra': '#F2F2F2',
}

out = []


def text_block(cx, cy, lines, size=15, line_h=None, anchor='middle', x=None):
    """Draw multi-line text vertically centred on cy."""
    line_h = line_h or size * 1.3
    top = cy - line_h * (len(lines) - 1) / 2
    tx = cx if x is None else x
    for i, line in enumerate(lines):
        out.append(
            f'<text x="{tx}" y="{top + i * line_h:.1f}" font-size="{size}" '
            f'text-anchor="{anchor}" dominant-baseline="central">{escape(line.strip())}</text>')


def lane(x, y, w, h, title, size=32):
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{LANE_FILL}" '
               f'stroke="{LANE_STROKE}" stroke-width="1.5"/>')
    out.append(f'<text x="{x + 12}" y="{y + 40}" font-size="{size}">{escape(title)}</text>')


def stack(x, y, w, h, title, color):
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{COLORS[color]}" '
               f'stroke="{STACK_STROKE}" stroke-width="1.2"/>')
    out.append(f'<text x="{x + 10}" y="{y + 22}" font-size="16">{escape(title)}</text>')


def box(x, y, w, h, lines, size=15, stroke=DATA):
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#FFFFFF" '
               f'stroke="{stroke}" stroke-width="1.2"/>')
    text_block(x + w / 2, y + h / 2, lines, size)


def ellipse(cx, cy, rx, ry, lines, size=15):
    out.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="#FFFFFF" '
               f'stroke="{DATA}" stroke-width="1.2"/>')
    text_block(cx, cy, lines, size)


def diamond(cx, cy, hw, hh, lines):
    pts = f'{cx},{cy - hh} {cx + hw},{cy} {cx},{cy + hh} {cx - hw},{cy}'
    out.append(f'<polygon points="{pts}" fill="#FFFFFF" stroke="{DATA}" stroke-width="1.2"/>')
    text_block(cx, cy, lines)


def arrow(points, color=DATA, both=False, width=1.4):
    """Orthogonal polyline with an arrowhead at the end (and start if both)."""
    d = 'M ' + ' L '.join(f'{x},{y}' for x, y in points)
    mid = 'power' if color == POWER else 'data'
    start = f' marker-start="url(#{mid}-start)"' if both else ''
    out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
               f'marker-end="url(#{mid}-end)"{start}/>')


def label(x, y, s, anchor='middle', size=12.5, halo=LANE_FILL):
    out.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
               f'dominant-baseline="central" fill="#404040" stroke="{halo}" '
               f'stroke-width="4" paint-order="stroke">{escape(s)}</text>')


# --------------------------------------------------------------------------
# Lanes
# --------------------------------------------------------------------------
lane(20, 20, 300, 1060, 'Inputs')
lane(345, 20, 1740, 1060, 'Jetson Orin Nano: ROS 2 Humble (qirc-sw)')
lane(2110, 20, 320, 1060, 'Pi Pico Firmware', size=30)
lane(2455, 20, 300, 1060, 'Actuators & Feedback', size=28)
lane(20, 1100, 2735, 360, 'Power Distribution (24 V)', size=30)

# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------
ellipse(170, 200, 120, 55, ['Front Camera', 'RealSense D435i', '(RGB-D + IMU)'])
ellipse(170, 320, 120, 55, ['Back Camera', 'OAK-D Lite', '(RGB-D + on-camera NN)'], size=14)
ellipse(170, 570, 120, 60, ['LiDAR', 'RPLIDAR A2M8'])
ellipse(170, 962, 120, 60, ['User', '(phone / laptop', 'browser)'])

# --------------------------------------------------------------------------
# Jetson: software stacks
# --------------------------------------------------------------------------
# Perception
stack(370, 100, 540, 260, 'Perception Stack (qirc_perception)', 'perception')
box(410, 150, 220, 190, ['Object Detection:', '- Front: YOLO on D435i',
                         '  images + aligned depth', '  (TensorRT on the Orin)',
                         '- Back: OAK on-camera', '  person detection'])
box(710, 175, 180, 140, ['User Detection:', '- Picks the user out', '  of person detections',
                         '- Estimates their', '  height for the arm'])

# Localization
stack(370, 380, 540, 420, 'Localization Stack (qirc_localization)', 'localization')
box(410, 500, 220, 140, ['SLAM (slam_toolbox):', '- Mapping mode: builds', '  the house map',
                         '- Localization mode:', '  pose on the saved map'])
diamond(795, 570, 95, 60, ['House Map'])
box(410, 670, 220, 85, ['Sensor Fusion (EKF):', 'track odometry (/odom)', '+ IMU'])

# Planning
stack(935, 100, 470, 700, 'Planning Stack (qirc_planning)', 'planning')
box(1010, 140, 320, 190, ['Vehicle Manager:', '- Wakes up when a dose is due',
                          '  (pill schedule)', '- Runs the mission: search, approach,',
                          '  dispense, raise arm, return home', '- Error / E-stop state',
                          '- Publishes /robot_state, /lights'])
box(1010, 380, 320, 195, ['Global Planner:', '- Search algorithm generates',
                          '  points around the home to check', '- Chooses the next point',
                          '- Plans a path to it (A*)', '- Serves SearchForUser and',
                          '  NavigateToPose'])
box(1010, 630, 320, 160, ['Local Planner (MPC):', '- Follows the global path and',
                          '  avoids obstacles (/scan,', '  /detections) in one MPC',
                          '- Skid-steer model of the tracks'])

# Pill dispensing
stack(1430, 100, 360, 320, 'Pill Dispensing (qirc_pill_dispenser)', 'dispensing')
box(1460, 150, 300, 90, ['Dispense Pills:', 'DispensePills action,', 'steps the pill box steppers'])
box(1460, 290, 300, 110, ['Move Arm to User Height:', 'MoveArm action,',
                          'height from /user_info'])

# Controls
stack(1430, 610, 360, 190, 'Controls Stack (qirc_control)', 'controls')
box(1460, 660, 300, 120, ['Command Mux (twist_mux):', 'picks nav / teleop / web',
                          'commands by priority;', 'E-stop blocks all driving'])

# Hardware bridge
stack(1815, 100, 245, 965, 'Hardware Bridge', 'bridge')
box(1835, 145, 205, 900, ['qirc_pico_bridge', '', 'The only node that', 'talks to the Pico', '',
                          'Sends:', 'track speeds, lights,', 'dispenser and arm', 'commands', '',
                          'Receives:', '/odom, /estop, /battery,', 'dispenser state,',
                          'arm joint states'])

# Web app
stack(370, 840, 1035, 225, 'Web App Stack (qirc_web)', 'web')
box(410, 885, 290, 155, ['Web Pages:', '- Status and battery', '- Dispense now',
                         '- Pill schedule editor', '- Drive controls (speed cap)',
                         '- Login'])
box(740, 885, 290, 155, ['rosbridge_server:', 'connects the web pages', 'to ROS topics and services',
                         '(schedule, mission control)'])
box(1070, 885, 300, 155, ['web_video_server:', 'front and back', 'camera streams'])

# Infrastructure
stack(1430, 840, 360, 225, 'Infrastructure', 'infra')
box(1450, 875, 320, 45, ['Teleop (keyboard / joystick)'])
box(1450, 935, 320, 60, ['Robot Model: URDF +', 'robot_state_publisher (TF)'])
box(1450, 1008, 320, 45, ['foxglove_bridge (dev tools)'])

# --------------------------------------------------------------------------
# Pico firmware
# --------------------------------------------------------------------------
box(2150, 150, 250, 90, ['Stepper Control:', 'STEP/DIR to 2× DRV8825,', 'counts steps from power-on'])
box(2150, 300, 250, 90, ['Arm Motor Control:', 'PWM/DIR to MDD10A,', 'position from encoders'])
box(2150, 445, 250, 80, ['Lights:', 'WS2812B status patterns,', 'headlight PWM'])
box(2150, 655, 250, 130, ['Drive Control:', 'per-track speed PID;', 'watchdog stops the motors',
                          'if commands stop arriving'])
box(2150, 860, 250, 160, ['Sensing:', 'drive encoder counts (PIO)', 'E-stop state',
                          'battery voltage / current'])

# --------------------------------------------------------------------------
# Actuators and feedback
# --------------------------------------------------------------------------
ellipse(2605, 195, 120, 55, ['Dispensing Motors', '2× NEMA 17 stepper'])
ellipse(2605, 345, 120, 55, ['Arm Motors', '2× JGB37-520'])
ellipse(2605, 485, 120, 50, ['Status LEDs', '& Headlights'])
ellipse(2605, 720, 120, 70, ['Drive Motors', '(left / right tracks)', '2× E-S 36PG'])
ellipse(2605, 880, 120, 50, ['Drive Encoders', '(TBD)'])
ellipse(2605, 1005, 120, 58, ['E-stop and', 'Battery Monitor'])

# --------------------------------------------------------------------------
# Data flow
# --------------------------------------------------------------------------
# Sensors into the Jetson
arrow([(290, 200), (410, 200)])
label(345, 188, 'USB 3')
arrow([(290, 320), (410, 320)])
label(345, 308, 'USB 3')
arrow([(50, 200), (35, 200), (35, 712), (410, 712)])
label(180, 700, 'IMU')
arrow([(290, 570), (410, 570)])
label(345, 558, 'USB')
arrow([(290, 962), (410, 962)], both=True)
label(345, 945, 'Wi-Fi / Tailscale')

# Perception
arrow([(630, 245), (710, 245)])
label(670, 232, '/detections', halo=COLORS['perception'])
arrow([(890, 245), (1010, 245)])
label(950, 232, '/user_info')

# Localization
arrow([(520, 670), (520, 640)])
arrow([(630, 570), (700, 570)])
arrow([(890, 570), (965, 570), (965, 478), (1010, 478)])
label(925, 557, '/map')
arrow([(630, 712), (1010, 712)])
label(800, 700, 'robot pose')

# Planning
arrow([(1170, 330), (1170, 380)])
label(1180, 355, 'SearchForUser / NavigateToPose', anchor='start', size=11.5,
      halo=COLORS['planning'])
arrow([(1170, 575), (1170, 630)])
label(1180, 602, '/plan', anchor='start', halo=COLORS['planning'])
arrow([(1330, 195), (1460, 195)])
label(1395, 182, 'DispensePills')
arrow([(1330, 310), (1460, 310)])
label(1395, 297, 'MoveArm')
arrow([(1330, 720), (1460, 720)])
label(1395, 707, '/cmd_vel_nav', size=11.5)

# Controls
arrow([(1760, 720), (1835, 720)])
label(1797, 707, '/cmd_vel', size=11.5)
arrow([(885, 885), (885, 815), (1520, 815), (1520, 780)])
label(1300, 827, '/cmd_vel_web')
arrow([(1690, 875), (1690, 780)])
label(1698, 828, '/cmd_vel_teleop', anchor='start')

# Dispensing <-> bridge
arrow([(1760, 195), (1835, 195)], both=True)
arrow([(1760, 345), (1835, 345)], both=True)

# Bridge <-> Pico over USB serial, fanned out on a bus
arrow([(2040, 590), (2125, 590)], both=True, width=2.2)
label(2082, 573, 'USB serial')
out.append(f'<path d="M 2125,195 L 2125,940" stroke="{DATA}" stroke-width="2.2" fill="none"/>')
for y in (195, 345, 485, 720):
    arrow([(2125, y), (2150, y)])
arrow([(2150, 940), (2127, 940)])

# Pico -> actuators, feedback -> Pico
for y, s in ((195, 'STEP/DIR'), (345, 'PWM/DIR'), (485, 'data / PWM'), (720, 'PWM/DIR')):
    arrow([(2400, y), (2485, y)])
    label(2442, y - 13, s, size=11.5)
arrow([(2485, 880), (2400, 880)])
label(2442, 867, 'A/B pulses', size=11.5)
arrow([(2485, 1005), (2400, 1005)])
label(2442, 992, 'GPIO / I²C', size=11.5)

# --------------------------------------------------------------------------
# Power distribution
# --------------------------------------------------------------------------
box(60, 1255, 200, 80, ['Battery', '8S LiFePO4', '25.6 V, 10 Ah'])
box(320, 1260, 150, 70, ['Main Fuse', '40 A'])
box(530, 1260, 150, 70, ['Main Switch'])
box(740, 1255, 180, 80, ['24 V Bus', '(unswitched)'])
box(1000, 1155, 180, 70, ['Buck-Boost', '19 V out'])
box(1000, 1260, 180, 70, ['E-stop', '(latching, NC)'])
box(1000, 1365, 180, 70, ['Buck', '5 V out'])
box(1240, 1155, 200, 70, ['Jetson Orin Nano'])
box(1240, 1260, 200, 70, ['Motor Rail 24 V'])
box(1240, 1365, 200, 70, ['Status LEDs', '(WS2812B)'])
box(1500, 1155, 420, 70, ['USB 5 V from the Jetson:', 'cameras, LiDAR, Pico'])
box(1500, 1260, 420, 70, ['Motor drivers: 2× MD10C (drive), MDD10A (arm),',
                          '2× DRV8825 (steppers), headlight MOSFET'])

arrow([(260, 1295), (320, 1295)], color=POWER)
arrow([(470, 1295), (530, 1295)], color=POWER)
arrow([(680, 1295), (740, 1295)], color=POWER)
out.append(f'<path d="M 920,1295 L 960,1295 M 960,1190 L 960,1400" stroke="{POWER}" '
           f'stroke-width="1.4" fill="none"/>')
for y in (1190, 1295, 1400):
    arrow([(960, y), (1000, y)], color=POWER)
    arrow([(1180, y), (1240, y)], color=POWER)
arrow([(1440, 1190), (1500, 1190)], color=POWER)
arrow([(1440, 1295), (1500, 1295)], color=POWER)

# Notes
out.append('<rect x="2000" y="1155" width="715" height="280" fill="#FFFFFF" '
           'stroke="#000000" stroke-width="1.2"/>')
notes = [
    'Notes',
    '- The E-stop cuts the motor rail only. The Jetson, Pico and LEDs stay',
    '  powered, so the robot can log the stop and report it.',
    '- The Jetson has its own 19 V regulator, so motor current spikes that',
    '  dip the battery voltage do not reboot it.',
    '- All grounds meet at one common ground bus.',
    '- Black arrows: data and commands. Red arrows: power.',
    '- Details: docs/architecture (nodes, topics) and docs/wiring (power).',
]
for i, line in enumerate(notes):
    weight = ' font-weight="bold"' if i == 0 else ''
    out.append(f'<text x="2020" y="{1185 + i * 31}" font-size="16"{weight} '
               f'dominant-baseline="central" style="white-space:pre">{escape(line)}</text>')

# --------------------------------------------------------------------------
# Assemble
# --------------------------------------------------------------------------
defs = []
for name, color in (('data', DATA), ('power', POWER)):
    defs.append(
        f'<marker id="{name}-end" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" '
        f'markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
        f'fill="{color}"/></marker>')
    defs.append(
        f'<marker id="{name}-start" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" '
        f'markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
        f'fill="{color}"/></marker>')

svg = (
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}" font-family="{FONT}" fill="#000000" xml:space="preserve">\n'
    f'<defs>{"".join(defs)}</defs>\n'
    f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>\n'
    + '\n'.join(out) + '\n</svg>\n'
)
Path(__file__).with_suffix('.svg').write_text(svg)
print(f'wrote {Path(__file__).with_suffix(".svg")}')
