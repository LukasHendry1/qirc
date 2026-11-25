"""
Generate the QIRC power schematic (qirc_power.kicad_sch) for KiCad 8.

    python3 docs/Electrical/schematic/make_schematic.py

The parts, their connections and the layout are all defined below. The
script writes the KiCad schematic and project, exports qirc_power.svg and
qirc_power.pdf with kicad-cli, and checks the exported netlist against
NETS: every net drawn must match the intended one exactly.

Layout units are grid steps of 2.54 mm (100 mil), so every pin and wire
end lands on KiCad's connection grid.
"""

import os
import re
import subprocess
import sys
import tempfile
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = 'qirc_power'
PROJECT_UUID = uuid.UUID('6f1c1e0a-5b51-4b8e-9a3e-2f0c51d0a403')
G = 2.54        # one layout unit, mm

TITLE = {
    'title': 'QIRC Power Distribution and Wiring',
    'date': '2026-11-24',
    'rev': '1.0',
    'company': "Queen's Intelligent Robotic Companion (QIRC)",
    'comments': [
        'MREN 403 Capstone',
        'L. Hendry, P. Silva, L. McIntaggart, V. Lew',
    ],
}

_uuid_count = 0


def new_uuid():
    """Deterministic UUIDs, so regenerating gives the same file."""
    global _uuid_count
    _uuid_count += 1
    return str(uuid.uuid5(PROJECT_UUID, str(_uuid_count)))


def mm(v):
    """Format a length in layout units as mm."""
    s = f'{v * G:.4f}'.rstrip('0').rstrip('.')
    return '0' if s == '-0' else s


def q(s):
    """Quote a string for KiCad."""
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'


def font(size=1.27, bold=False, justify=None, hide=False):
    out = f'(effects (font (size {size} {size}){" (bold yes)" if bold else ""})'
    if justify:
        out += f' (justify {justify})'
    if hide:
        out += ' (hide yes)'
    return out + ')'


# --- Library symbols ---------------------------------------------------------
#
# Coordinates in library symbols are in units with y pointing up, as KiCad
# stores them. A pin is (name, x, y, angle): (x, y) is where the wire
# connects; the angle points from there into the body.

class Symbol:
    def __init__(self, name, pins, graphics, ref_at, value_at,
                 ref_justify='left bottom', value_justify='left top',
                 show_pin_names=True, show_pin_numbers=True, power=False,
                 value_hidden=False, ref_hidden=False, pin_type='passive'):
        self.name = name
        self.pins = pins
        self.graphics = graphics
        self.ref_at = ref_at
        self.value_at = value_at
        self.ref_justify = ref_justify
        self.value_justify = value_justify
        self.show_pin_names = show_pin_names
        self.show_pin_numbers = show_pin_numbers
        self.power = power
        self.value_hidden = value_hidden
        self.ref_hidden = ref_hidden
        self.pin_type = pin_type

    def pin_number(self, name):
        for i, pin in enumerate(self.pins):
            if pin[0] == name:
                return str(i + 1)
        raise KeyError(f'{self.name} has no pin {name}')

    def lib_sexpr(self, ref_prefix):
        lib = 'power' if self.power else 'qirc'
        out = [f'(symbol {q(lib + ":" + self.name)}']
        if self.power:
            out.append('(power)')
        if not self.show_pin_numbers:
            out.append('(pin_numbers hide)')
        out.append('(pin_names (offset 0.508)' + ('' if self.show_pin_names else ' hide') + ')')
        out.append('(exclude_from_sim no) (in_bom yes) (on_board yes)')
        out.append(f'(property "Reference" {q(ref_prefix)} (at {mm(self.ref_at[0])} '
                   f'{mm(self.ref_at[1])} 0) {font(justify=self.ref_justify, hide=self.ref_hidden)})')
        out.append(f'(property "Value" {q(self.name)} (at {mm(self.value_at[0])} '
                   f'{mm(self.value_at[1])} 0) {font(justify=self.value_justify, hide=self.value_hidden)})')
        for prop in ('Footprint', 'Datasheet', 'Description'):
            out.append(f'(property {q(prop)} "" (at 0 0 0) {font(hide=True)})')
        out.append(f'(symbol {q(self.name + "_0_1")} {" ".join(self.graphics)})')
        pins = []
        for i, (name, x, y, angle) in enumerate(self.pins):
            length = 0 if self.power else G
            pins.append(
                f'(pin {self.pin_type} line (at {mm(x)} {mm(y)} {angle}) (length {length}) '
                f'(name {q(name)} {font()}) (number "{i + 1}" {font()}))')
        out.append(f'(symbol {q(self.name + "_1_1")} {" ".join(pins)})')
        return ' '.join(out) + ')'


def stroke(width=0.254, kind='default'):
    return f'(stroke (width {width}) (type {kind}))'


def rect(x0, y0, x1, y1, fill='background', width=0.254):
    return (f'(rectangle (start {mm(x0)} {mm(y0)}) (end {mm(x1)} {mm(y1)}) '
            f'{stroke(width)} (fill (type {fill})))')


def line(*pts, width=0.254, fill='none'):
    xy = ' '.join(f'(xy {mm(x)} {mm(y)})' for x, y in pts)
    return f'(polyline (pts {xy}) {stroke(width)} (fill (type {fill})))'


def circle(x, y, r, width=0.254):
    return (f'(circle (center {mm(x)} {mm(y)}) (radius {mm(r)}) '
            f'{stroke(width)} (fill (type none)))')


def box_symbol(name, left, right, width):
    """A labelled box: `left` and `right` pin names, one per grid row from
    the top (None leaves a row empty)."""
    rows = max(len(left), len(right))
    pins = []
    for i, pin in enumerate(left):
        if pin:
            pins.append((pin, -1, -i, 0))
    for i, pin in enumerate(right):
        if pin:
            pins.append((pin, width + 1, -i, 180))
    graphics = [rect(0, 1, width, -rows)]
    return Symbol(name, pins, graphics, ref_at=(0, 1.4), value_at=(0, -rows - 0.3))


def two_pin(name, graphics, value_at=(0, 0.9), ref_at=None, value_justify='bottom'):
    """A horizontal two-terminal part, pins 2 units either side of the middle."""
    return Symbol(name, [('1', -2, 0, 0), ('2', 2, 0, 180)], graphics,
                  ref_at=ref_at or (0, 1.6), value_at=value_at,
                  ref_justify='bottom', value_justify=value_justify,
                  show_pin_names=False, show_pin_numbers=False, value_hidden=True)


FUSE_GRAPHICS = [rect(-1, 0.35, 1, -0.35, fill='none'), line((-1, 0), (1, 0))]
# Switch: contacts at +-0.8, the lever lifted off the right contact.
SWITCH_GRAPHICS = [circle(-0.8, 0, 0.2), circle(0.8, 0, 0.2),
                   line((-0.6, 0.1), (0.9, 0.7)),
                   line((-1, 0), (-0.95, 0)), line((0.95, 0), (1, 0))]
# Normally closed push button: the bar rests under both contacts; pushing
# the mushroom head moves it away.
ESTOP_GRAPHICS = [circle(-0.8, 0, 0.2), circle(0.8, 0, 0.2),
                  line((-1.1, -0.3), (1.1, -0.3)),
                  line((0, -0.3), (0, 1.1)),
                  line((-0.6, 1.1), (0.6, 1.1), width=0.508),
                  line((-1, 0), (-1, 0)), line((1, 0), (1, 0))]


def diode_symbol(name):
    """Vertical diode: cathode (pin K) at the top, anode (A) at the bottom."""
    graphics = [line((-0.5, -0.5), (0.5, -0.5), (0, 0.5), (-0.5, -0.5), fill='outline'),
                line((-0.5, 0.5), (0.5, 0.5)),
                line((0, 1), (0, -1))]
    return Symbol(name, [('K', 0, 2, 270), ('A', 0, -2, 90)], graphics,
                  ref_at=(0.8, 0.3), value_at=(0.8, -0.3),
                  ref_justify='left bottom', value_justify='left top',
                  show_pin_names=False, show_pin_numbers=False)


GND = Symbol('GND', [('1', 0, 0, 270)], [
    line((0, 0), (0, -0.5), (0.5, -0.5), (0, -1), (-0.5, -0.5), (0, -0.5), width=0),
], ref_at=(0, -2.5), value_at=(0, -1.5), ref_justify='bottom', value_justify='top',
    show_pin_names=False, show_pin_numbers=False, power=True,
    value_hidden=True, ref_hidden=True, pin_type='power_in')

PWR_FLAG = Symbol('PWR_FLAG', [('1', 0, 0, 90)], [
    line((0, 0), (0, 0.5), (-0.4, 0.75), (0, 1), (0.4, 0.75), (0, 0.5), width=0),
], ref_at=(0, 0.75), value_at=(0, 1.25), ref_justify='bottom', value_justify='bottom',
    show_pin_names=False, show_pin_numbers=False, power=True,
    value_hidden=True, ref_hidden=True, pin_type='power_out')


# --- Schematic ----------------------------------------------------------------

class Sheet:
    def __init__(self):
        self.lib = {}           # library name -> (Symbol, ref prefix)
        self.parts = {}         # ref -> (Symbol, x, y)
        self.items = []         # placed symbol s-expressions
        self.segments = []      # wire segments ((x0, y0), (x1, y1), colour)
        self.labels = []
        self.texts = []
        self.graphics = []
        self.pin_points = []
        self._power_count = 0

    def add(self, ref, symbol, x, y, value=None, notes=None, notes_at=None,
            ref_prefix='U'):
        """Place a symbol with its origin at (x, y). Notes go under the
        value, or at notes_at (relative to the origin)."""
        self.lib.setdefault(symbol.name, (symbol, ref_prefix))
        self.parts[ref] = (symbol, x, y)
        self._place(symbol, x, y, ref, value or symbol.name)
        if notes:
            nx, ny = notes_at if notes_at else (symbol.value_at[0], -symbol.value_at[1] + 1.1)
            self.text(notes, x + nx, y + ny)
        return self

    def _place(self, symbol, x, y, ref, value, power=False):
        lib = ('power:' if symbol.power else 'qirc:') + symbol.name
        rx, ry = symbol.ref_at
        vx, vy = symbol.value_at
        pins = ' '.join(f'(pin "{i + 1}" (uuid "{new_uuid()}"))' for i in range(len(symbol.pins)))
        self.items.append(
            f'(symbol (lib_id {q(lib)}) (at {mm(x)} {mm(y)} 0) (unit 1) '
            f'(exclude_from_sim no) (in_bom {"no" if symbol.power else "yes"}) '
            f'(on_board yes) (dnp no) (uuid "{new_uuid()}") '
            f'(property "Reference" {q(ref)} (at {mm(x + rx)} {mm(y - ry)} 0) '
            f'{font(bold=not symbol.power, justify=symbol.ref_justify, hide=symbol.ref_hidden)}) '
            f'(property "Value" {q(value)} (at {mm(x + vx)} {mm(y - vy)} 0) '
            f'{font(justify=symbol.value_justify, hide=symbol.value_hidden)}) '
            f'(property "Footprint" "" (at {mm(x)} {mm(y)} 0) {font(hide=True)}) '
            f'(property "Datasheet" "" (at {mm(x)} {mm(y)} 0) {font(hide=True)}) '
            f'(property "Description" "" (at {mm(x)} {mm(y)} 0) {font(hide=True)}) '
            f'{pins} (instances (project {q(NAME)} (path "/{ROOT_UUID}" '
            f'(reference {q(ref)}) (unit 1)))))')
        for _, px, py, _ in symbol.pins:
            self.pin_points.append((x + px, y - py))

    def pin(self, ref, name):
        """Where a placed part's pin connects, in sheet units."""
        symbol, x, y = self.parts[ref]
        for pin_name, px, py, _ in symbol.pins:
            if pin_name == name:
                return (x + px, y - py)
        raise KeyError(f'{ref} has no pin {name}')

    def gnd(self, x, y):
        self._power_count += 1
        self.lib.setdefault('GND', (GND, '#PWR'))
        self._place(GND, x, y, f'#PWR{self._power_count:02d}', 'GND')

    def pwr_flag(self, x, y):
        self._power_count += 1
        self.lib.setdefault('PWR_FLAG', (PWR_FLAG, '#FLG'))
        self._place(PWR_FLAG, x, y, f'#FLG{self._power_count:02d}', 'PWR_FLAG')

    def wire(self, *points, colour=None, gauge=None, gauge_at=None, below=False):
        """A wire through points; each point is (x, y) or a (ref, pin) pair."""
        pts = [self.pin(*p) if isinstance(p[0], str) else p for p in points]
        for a, b in zip(pts, pts[1:]):
            assert a[0] == b[0] or a[1] == b[1], f'wire not straight: {a} {b}'
            self.segments.append((a, b, colour))
        if gauge:
            if gauge_at is None:
                (x0, y0), (x1, y1) = pts[0], pts[1]
                gauge_at = ((x0 + x1) / 2, y0 - 0.25) if y0 == y1 else (x0 + 0.3, (y0 + y1) / 2)
            just = ('top' if below else 'bottom') if pts[0][1] == pts[1][1] else 'left'
            self.text(gauge, *gauge_at, size=1.0, justify=just, colour=(0, 0, 132))
        return pts[-1]

    def label(self, name, x, y):
        self.labels.append(
            f'(label {q(name)} (at {mm(x)} {mm(y)} 0) {font(justify="left bottom")} '
            f'(uuid "{new_uuid()}"))')

    def text(self, s, x, y, size=1.27, justify='left top', bold=False, colour=None):
        col = f' (color {colour[0]} {colour[1]} {colour[2]} 1)' if colour else ''
        self.texts.append(
            f'(text {q(s)} (exclude_from_sim no) (at {mm(x)} {mm(y)} 0) '
            f'(effects (font (size {size} {size}){" (bold yes)" if bold else ""}{col}) '
            f'(justify {justify})) (uuid "{new_uuid()}"))')

    def zone(self, x0, y0, x1, y1, title):
        self.graphics.append(
            f'(rectangle (start {mm(x0)} {mm(y0)}) (end {mm(x1)} {mm(y1)}) '
            f'(stroke (width 0.3) (type dash) (color 110 110 110 1)) (fill (type none)) '
            f'(uuid "{new_uuid()}"))')
        self.text(title, x0 + 0.5, y0 + 0.5, size=1.5, bold=True, colour=(90, 90, 90))

    # -- output --

    def _split_segments(self):
        """Break wires wherever another wire ends or a pin sits on them, so
        every connection is end to end, and find the junctions."""
        ends = {p for a, b, _ in self.segments for p in (a, b)} | set(self.pin_points)
        out = []
        for a, b, colour in self.segments:
            on = [p for p in ends if p not in (a, b) and _between(p, a, b)]
            pts = sorted([a, b, *on], key=lambda p: (p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2)
            out += [(p, r, colour) for p, r in zip(pts, pts[1:])]
        count = {}
        for a, b, _ in out:
            for p in (a, b):
                count[p] = count.get(p, 0) + 1
        for p in self.pin_points:
            if p in count:
                count[p] += 1
        junctions = [p for p, n in count.items() if n >= 3]
        return out, junctions

    def write(self, path):
        segments, junctions = self._split_segments()
        wires = []
        for (x0, y0), (x1, y1), colour in segments:
            col = f' (color {colour[0]} {colour[1]} {colour[2]} 1)' if colour else ''
            wires.append(
                f'(wire (pts (xy {mm(x0)} {mm(y0)}) (xy {mm(x1)} {mm(y1)})) '
                f'(stroke (width {0.3 if colour else 0}) (type default){col}) '
                f'(uuid "{new_uuid()}"))')
        juncs = [f'(junction (at {mm(x)} {mm(y)}) (diameter 0) (color 0 0 0 0) '
                 f'(uuid "{new_uuid()}"))' for x, y in junctions]
        tb = TITLE
        title = (f'(title_block (title {q(tb["title"])}) (date {q(tb["date"])}) '
                 f'(rev {q(tb["rev"])}) (company {q(tb["company"])}) '
                 + ' '.join(f'(comment {i + 1} {q(c)})' for i, c in enumerate(tb['comments']))
                 + ')')
        lib = ' '.join(s.lib_sexpr(prefix) for s, prefix in self.lib.values())
        body = [
            '(kicad_sch (version 20231120) (generator "qirc_make_schematic") '
            '(generator_version "8.0")',
            f'(uuid "{ROOT_UUID}")', '(paper "User" 325 220)', title,
            f'(lib_symbols {lib})',
            *juncs, *wires, *self.labels, *self.texts, *self.graphics, *self.items,
            '(sheet_instances (path "/" (page "1")))', ')',
        ]
        with open(path, 'w') as f:
            f.write(_indent('\n'.join(body)) + '\n')


def _between(p, a, b):
    if a[0] == b[0] == p[0]:
        return min(a[1], b[1]) < p[1] < max(a[1], b[1])
    if a[1] == b[1] == p[1]:
        return min(a[0], b[0]) < p[0] < max(a[0], b[0])
    return False


def _indent(text):
    """One top-level item per line; KiCad re-formats the file when it saves."""
    lines = text.split('\n')
    return '\n'.join([lines[0]] + ['\t' + ln for ln in lines[1:-1]] + [lines[-1]])


ROOT_UUID = str(uuid.uuid5(PROJECT_UUID, 'root'))


# --- The design ---------------------------------------------------------------

def build():
    s = Sheet()
    wire12, wire14, wire16, wire18, wire20, wire22 = (
        '12 AWG', '14 AWG', '16 AWG', '18 AWG', '20 AWG', '22 AWG')

    # ---- Source, main switch, E-stop and contactor (top left) ----
    s.add('BAT', box_symbol('Battery', [], ['B+', None, 'B-'], 9), 7, 12,
          value='8S LiFePO4, 25.6 V')
    s.add('F_BAT', two_pin('Fuse_40A', FUSE_GRAPHICS), 24, 12, ref_prefix='F',
          notes='0895040.Z', notes_at=(-2.2, 1.0))
    s.text('40 A', 24, 11.5, size=1.0, justify='bottom')
    s.add('SW1', two_pin('Loop_key', SWITCH_GRAPHICS), 37, 12, ref_prefix='SW',
          notes='XT90-S loop key', notes_at=(-3, 1.0))
    s.add('K1', box_symbol('Contactor', ['IN', None, 'COIL+', 'COIL-'], ['OUT'], 10),
          59, 12, value='Altran ALEV50-C, 50 A, 24 V coil', ref_prefix='K')
    s.add('ES1', two_pin('E-stop', ESTOP_GRAPHICS, ref_at=(0, 2.0)), 47, 20, ref_prefix='SW',
          notes='E-stop (NC)', notes_at=(-2.2, 1.0))
    s.add('D1', diode_symbol('1N4007'), 53, 16, ref_prefix='D')

    s.wire(('BAT', 'B+'), ('F_BAT', '1'), gauge=wire12)
    s.wire(('BAT', 'B-'), (19, 14))
    s.gnd(19, 14)
    s.pwr_flag(19, 14)
    s.wire(('F_BAT', '2'), ('SW1', '1'), gauge=wire12)
    s.wire(('SW1', '2'), ('K1', 'IN'), gauge=wire12, gauge_at=(51, 11.75))
    s.label('+BAT_SW', 39.5, 12)
    # E-stop in series with the contactor coil; D1 across the coil.
    s.wire((44, 12), (44, 20), ('ES1', '1'), gauge=wire18, gauge_at=(44.3, 16.5))
    # +BAT_SW down to the always-on converters (DC19, DC5), before K1.
    s.wire((44, 20), (44, 24), (7, 24), (7, 60), gauge=wire18, gauge_at=(25, 23.75))
    s.wire(('ES1', '2'), (50, 20), (50, 14), ('K1', 'COIL+'))
    s.wire(('D1', 'A'), (56, 18), (56, 15), ('K1', 'COIL-'))
    s.gnd(56, 18)
    trunk = 77
    s.wire(('K1', 'OUT'), (trunk, 12), gauge=wire12, gauge_at=(73.5, 12.25), below=True)
    s.label('+24V_MOT', 71, 12)

    # ---- Actuators, cut by the E-stop (right) ----

    for side, y in (('L', 12), ('R', 22)):
        side_name = 'left' if side == 'L' else 'right'
        s.add(f'F_M{side}', two_pin('Fuse_15A', FUSE_GRAPHICS), 83, y, ref_prefix='F',
              notes='0287015.PXCN', notes_at=(-2.5, 0.9))
        s.text('15 A ATO', 83, y - 0.5, size=1.0, justify='bottom')
        s.add(f'MD_{side}', box_symbol('MD10C', ['POWER+', 'POWER-'], ['MA', 'MB'], 11),
              94, y, value=f'Cytron MD10C ({side_name})')
        s.add(f'M_{side}', box_symbol('Drive_motor', ['M+', 'M-'], [], 9), 114, y,
              value='E-S Motor 36PG-555K')
        s.wire((trunk, y), (f'F_M{side}', '1'), gauge=wire14)
        s.wire((f'F_M{side}', '2'), (f'MD_{side}', 'POWER+'), gauge=wire14)
        s.wire((f'MD_{side}', 'POWER-'), (91, y + 1))
        s.gnd(91, y + 1)
        s.wire((f'MD_{side}', 'MA'), (f'M_{side}', 'M+'), gauge=wire14)
        s.wire((f'MD_{side}', 'MB'), (f'M_{side}', 'M-'))

    # 12 V arm rail and the arm driver.
    y = 32
    s.add('DC12', box_symbol('Buck_12V', ['IN+', 'IN-'], ['OUT+', 'OUT-'], 5), 82, y,
          value='Buck 24 -> 12 V, 6 A', ref_prefix='PS')
    s.add('AD', box_symbol('TB6612FNG', ['VM', 'GND'],
                           ['AO1', 'AO2', None, None, None, None, 'BO1', 'BO2'], 11),
          94, y, value='SparkFun TB6612FNG (arm)')
    for i, n in enumerate(('1', '2')):
        s.add(f'AM_{n}', box_symbol('Arm_motor', ['M+', 'M-'], [], 9), 114, y + 6 * i,
              value='Yahboom MD520Z19')
    s.wire((trunk, y), ('DC12', 'IN+'), gauge=wire18)
    s.wire(('DC12', 'IN-'), (79, y + 1))
    s.gnd(79, y + 1)
    s.wire(('DC12', 'OUT+'), ('AD', 'VM'), gauge=wire18)
    s.wire(('DC12', 'OUT-'), ('AD', 'GND'))
    s.gnd(91, y + 1)
    s.wire(('AD', 'AO1'), ('AM_1', 'M+'), gauge=wire20)
    s.wire(('AD', 'AO2'), ('AM_1', 'M-'))
    s.wire(('AD', 'BO1'), ('AM_2', 'M+'), gauge=wire20)
    s.wire(('AD', 'BO2'), ('AM_2', 'M-'))

    # Dispenser steppers.
    coil_colours = [(0, 0, 0), (0, 150, 0), (200, 0, 0), (0, 70, 220)]
    for i, y in enumerate((45, 55)):
        n = str(i + 1)
        s.add(f'DRV_{n}', box_symbol('DRV8825', ['VMOT', 'GND'], ['A1', 'A2', 'B1', 'B2'], 11),
              94, y, value=f'TI DRV8825 (dispenser {n})')
        s.add(f'ST_{n}', box_symbol('NEMA17', ['A+', 'A-', 'B+', 'B-'], [], 9), 114, y,
              value='NEMA 17 stepper')
        s.wire((trunk, y), (f'DRV_{n}', 'VMOT'), gauge=wire18)
        s.wire((f'DRV_{n}', 'GND'), (91, y + 1))
        s.gnd(91, y + 1)
        for pin_a, pin_b, colour in zip(('A1', 'A2', 'B1', 'B2'), ('A+', 'A-', 'B+', 'B-'),
                                        coil_colours):
            s.wire((f'DRV_{n}', pin_a), (f'ST_{n}', pin_b), colour=colour)
        s.text(f'{wire22} x4', 109, y - 0.25, size=1.0, justify='bottom', colour=(0, 0, 132))

    # Headlights.
    y = 65
    s.add('MOSFET', box_symbol('MOSFET_module', ['VIN+', 'VIN-'], ['OUT+', 'OUT-'], 11), 94, y,
          value='MOSFET module', ref_prefix='Q')
    s.add('HEAD', box_symbol('Headlights', ['+', '-'], [], 9), 114, y,
          value='goBILDA headlights')
    s.wire((trunk, 12), (trunk, y), ('MOSFET', 'VIN+'), gauge=wire18,
           gauge_at=(85, y - 0.25))
    s.wire(('MOSFET', 'VIN-'), (91, y + 1))
    s.gnd(91, y + 1)
    s.wire(('MOSFET', 'OUT+'), ('HEAD', '+'), gauge=wire20)
    s.wire(('MOSFET', 'OUT-'), ('HEAD', '-'))

    # ---- Always on: computer, sensors, status LEDs (left) ----
    y = 31
    s.add('DC19', box_symbol('Buck_boost_19V', ['IN+', 'IN-'], ['OUT+', 'OUT-'], 8), 17, y,
          value='Buck-boost -> 19 V', ref_prefix='PS')
    s.add('JETSON', box_symbol('Jetson', ['DC_IN+', 'DC_IN-'],
                               ['USB1', 'USB2', 'USB3', 'USB4'], 10), 33, y,
          value='Jetson Orin Nano dev kit')
    s.wire((7, y), ('DC19', 'IN+'), gauge=wire18, gauge_at=(13.5, y - 0.25))
    s.wire(('DC19', 'IN-'), (14, y + 1))
    s.gnd(14, y + 1)
    s.wire(('DC19', 'OUT+'), ('JETSON', 'DC_IN+'), gauge=wire16)
    s.wire(('DC19', 'OUT-'), ('JETSON', 'DC_IN-'))
    s.gnd(29, y + 1)

    devices = [
        ('CAM_F', 'USB-C', 'Intel RealSense D435i (front)', 'USB 3 cable, A to C', 29, 50),
        ('CAM_R', 'USB-C', 'Luxonis OAK-D Lite (rear)', 'USB 3 cable, A to C', 37, 49),
        ('LIDAR', 'USB', 'Slamtec RPLIDAR A2M8', 'USB, via its adapter board', 45, 48),
        ('PICO', 'Micro-USB', 'Raspberry Pi Pico (RP2040)',
         'signals: separate diagram', 53, 47),
    ]
    for i, (ref, pin, value, note, dy, xr) in enumerate(devices):
        s.add(ref, box_symbol(ref.title() + '_dev', [pin], [], 11), 54, dy, value=value,
              ref_prefix='J')
        port = ('JETSON', f'USB{i + 1}')
        _, sy = s.pin(*port)
        s.wire(port, (xr, sy), (xr, dy), (ref, pin))

    y = 60
    s.add('DC5', box_symbol('Buck_5V', ['IN+', 'IN-'], ['OUT+', 'OUT-'], 8), 17, y,
          value='Buck 24 -> 5 V, 3 A', ref_prefix='PS')
    s.add('LEDS', box_symbol('LED_strip', ['5V', 'GND'], [], 10), 33, y,
          value='Seeed Grove WS2813 strip')
    s.wire((7, y), ('DC5', 'IN+'), gauge=wire20, gauge_at=(13.5, y - 0.25))
    s.wire(('DC5', 'IN-'), (14, y + 1))
    s.gnd(14, y + 1)
    s.wire(('DC5', 'OUT+'), ('LEDS', '5V'), gauge=wire20)
    s.wire(('DC5', 'OUT-'), ('LEDS', 'GND'))
    s.gnd(29, y + 1)

    return s


# The intended nets: each is a set of (ref, pin name). The drawn schematic
# must give exactly these.
GROUND = {('BAT', 'B-'), ('K1', 'COIL-'), ('D1', 'A'), ('MD_L', 'POWER-'), ('MD_R', 'POWER-'),
          ('DC12', 'IN-'), ('DC12', 'OUT-'), ('AD', 'GND'), ('DRV_1', 'GND'), ('DRV_2', 'GND'),
          ('MOSFET', 'VIN-'), ('DC19', 'IN-'), ('DC19', 'OUT-'), ('JETSON', 'DC_IN-'),
          ('DC5', 'IN-'), ('DC5', 'OUT-'), ('LEDS', 'GND')}
NETS = [
    GROUND,
    {('BAT', 'B+'), ('F_BAT', '1')},
    {('F_BAT', '2'), ('SW1', '1')},
    {('SW1', '2'), ('K1', 'IN'), ('ES1', '1'), ('DC19', 'IN+'), ('DC5', 'IN+')},
    {('ES1', '2'), ('K1', 'COIL+'), ('D1', 'K')},
    {('K1', 'OUT'), ('F_ML', '1'), ('F_MR', '1'), ('DC12', 'IN+'), ('DRV_1', 'VMOT'),
     ('DRV_2', 'VMOT'), ('MOSFET', 'VIN+')},
    {('F_ML', '2'), ('MD_L', 'POWER+')}, {('F_MR', '2'), ('MD_R', 'POWER+')},
    {('MD_L', 'MA'), ('M_L', 'M+')}, {('MD_L', 'MB'), ('M_L', 'M-')},
    {('MD_R', 'MA'), ('M_R', 'M+')}, {('MD_R', 'MB'), ('M_R', 'M-')},
    {('DC12', 'OUT+'), ('AD', 'VM')},
    {('AD', 'AO1'), ('AM_1', 'M+')}, {('AD', 'AO2'), ('AM_1', 'M-')},
    {('AD', 'BO1'), ('AM_2', 'M+')}, {('AD', 'BO2'), ('AM_2', 'M-')},
    *({(f'DRV_{n}', a), (f'ST_{n}', b)} for n in '12'
      for a, b in zip(('A1', 'A2', 'B1', 'B2'), ('A+', 'A-', 'B+', 'B-'))),
    {('MOSFET', 'OUT+'), ('HEAD', '+')}, {('MOSFET', 'OUT-'), ('HEAD', '-')},
    {('DC19', 'OUT+'), ('JETSON', 'DC_IN+')},
    {('JETSON', 'USB1'), ('CAM_F', 'USB-C')}, {('JETSON', 'USB2'), ('CAM_R', 'USB-C')},
    {('JETSON', 'USB3'), ('LIDAR', 'USB')}, {('JETSON', 'USB4'), ('PICO', 'Micro-USB')},
    {('DC5', 'OUT+'), ('LEDS', '5V')},
]


def check_netlist(sheet, sch):
    """Export the netlist with kicad-cli and compare it with NETS."""
    with tempfile.TemporaryDirectory() as tmp:
        net_file = os.path.join(tmp, 'power.net')
        subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '-o', net_file, sch],
                       check=True, capture_output=True)
        text = open(net_file).read()
    # Pin numbers back to names.
    names = {}
    for ref, (symbol, _, _) in sheet.parts.items():
        for i, pin in enumerate(symbol.pins):
            names[(ref, str(i + 1))] = pin[0]
    drawn = []
    for block in re.findall(r'\(net \(code "\d+"\) \(name "([^"]*)"\)(.*?)\)\s*(?=\(net |\)\s*\)\s*$)',
                            text, re.S):
        nodes = re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', block[1])
        members = {(r, names[(r, p)]) for r, p in nodes if not r.startswith('#')}
        if members:
            drawn.append((block[0], frozenset(members)))
    want = {frozenset(n) for n in NETS}
    got = {m for _, m in drawn}
    ok = True
    for n in want - got:
        print('MISSING net:', sorted(n))
        ok = False
    for name, n in drawn:
        if n not in want:
            print(f'UNEXPECTED net {name}:', sorted(n))
            ok = False
    unconnected = [n for n in got if len(n) < 2]
    for n in unconnected:
        print('unconnected pin:', sorted(n))
    print(f'netlist: {len(got)} nets drawn, {len(want)} intended:', 'OK' if ok else 'MISMATCH')
    return ok


def main():
    sheet = build()
    sch = os.path.join(HERE, NAME + '.kicad_sch')
    sheet.write(sch)
    with open(os.path.join(HERE, NAME + '.kicad_pro'), 'w') as f:
        f.write('{\n  "meta": {\n    "filename": "%s.kicad_pro",\n    "version": 1\n  },\n'
                '  "sheets": [\n    [\n      "%s",\n      "Root"\n    ]\n  ]\n}\n'
                % (NAME, ROOT_UUID))
    ok = check_netlist(sheet, sch)
    subprocess.run(['kicad-cli', 'sch', 'export', 'svg', '-o', HERE, sch],
                   check=True, capture_output=True)
    subprocess.run(['kicad-cli', 'sch', 'export', 'pdf', '-o',
                    os.path.join(HERE, NAME + '.pdf'), sch], check=True, capture_output=True)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
