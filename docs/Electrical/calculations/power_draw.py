"""
Write the component power-draw calculations onto the calculation sheet.

    pip install pypdf reportlab
    python3 docs/Electrical/calculations/power_draw.py

Reads the blank template (docs/Electrical/calculation-sheet.pdf) and writes
power_draw.pdf next to this script, one template page per sheet. The text
sits on the template's 14.17 pt grid. Every value comes from a datasheet in
docs/Electrical/Datasheets unless it is marked "Est.".
"""

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / 'calculation-sheet.pdf'
OUTPUT = HERE / 'power_draw.pdf'

PAGE_H = 792.0
GRID_X0, GRID_X1 = 36.5, 575.0     # grid edges, measured from the template
GRID_TOP = 192.0                   # top grid line, from the top of the page
CELL = (GRID_X1 - GRID_X0) / 38    # 38 columns, 39 rows
ROWS = 39
INK = (0.10, 0.12, 0.40)           # dark blue, like pen on the sheet

HEADER = {
    'Project': (80, 92.75, 'QIRC (MREN 403 Capstone)'),
    'No.': (362, 92.75, 'PWR-01'),
    'Date': (371, 109.5, '2026-11-23'),
    'Area': (68, 126.25, 'Electrical: power budget'),
    'Subject': (80, 143.0, 'Power draw of each component (min / typ / max)'),
}
SHEET_NUM_X, OF_X, SHEET_Y = 455, 535, 168.5

# Value columns: right edges, in grid columns.
VALUE_COLS = {'min': 30, 'typ': 34, 'max': 38}

# Each row is one grid row:
#   ('title', text)                 bold heading
#   ('text', text)                  a line of working, indented
#   ('item', text, min, typ, max)   a component and its range in W
#   ('total', text, min, typ, max)  a subtotal, boxed
#   ('cols',)                       Min / Typ / Max labels
#   ()                              blank
SHEETS = [
    [
        ('title', 'Method'),
        ('text', 'Electrical power drawn from each supply: P = V × I.  For a motor or stepper winding: P = I² × R.'),
        ('text', 'Min = off / idle / lowest mode.  Typ = normal operation.  Max = worst case from the datasheet.'),
        ('text', 'Values are from docs/Electrical/Datasheets.  "Est." marks an estimate where none is published.'),
        ('text', 'Converter losses (19 V, 12 V, 5 V supplies) are not included: the converters are not chosen yet.'),
        (),
        ('title', 'Computer and USB devices (19 V supply; the Jetson powers the USB devices)'),
        ('cols',),
        ('item', '1. NVIDIA Jetson Orin Nano developer kit (19 V jack)', 7.0, 15.0, 15.0),
        ('text', 'Datasheet power modes: 7 W - 15 W.  Min = 7 W mode, Typ / Max = 15 W mode.'),
        ('text', 'Does not include the USB devices below, which also come through the 19 V input.'),
        ('item', '2. Intel RealSense D435i (USB, 5 V)', 1.78, 3.40, 3.50),
        ('text', 'Typ: all parts at max mode (720p depth + 1080p colour, 30 fps) = 3.40 W'),
        ('text', 'Min: IR projector off: 3.40 W - 1.62 W = 1.78 W'),
        ('text', 'Max: 5.00 V × 0.70 A (board max supply current) = 3.50 W'),
        ('item', '3. Luxonis OAK-D Lite (USB-C, 5 V)', 2.5, 5.0, 6.0),
        ('text', 'Idle (Myriad X booted) 2.5 W.  Running 4 - 6 W, 5 W typical.'),
        ('item', '4. Slamtec RPLIDAR A2M8 (5 V)', 1.00, 2.25, 3.12),
        ('text', 'Min (motor off): 5.0 V × 0.20 A = 1.00 W     Typ (scanning): 5.0 V × 0.45 A = 2.25 W'),
        ('text', 'Max: 5.2 V × 0.60 A = 3.12 W     Start-up, brief: 5.0 V × 1.5 A = 7.5 W'),
        ('item', '5. Raspberry Pi Pico, RP2040 (USB, 5 V)', 0.004, 0.10, 0.47),
        ('text', 'Min (DORMANT): 5 V × 0.8 mA = 0.004 W     Typ (Est.): 5 V × 20 mA = 0.10 W'),
        ('text', 'Max (datasheet heaviest test): 5 V × 94.1 mA = 0.47 W'),
        (),
        ('total', 'USB devices (2 - 5)', 5.28, 10.75, 13.09),
        ('text', 'Min: 1.78 + 2.5 + 1.00 + 0.004 = 5.28 W'),
        ('text', 'Typ: 3.40 + 5.0 + 2.25 + 0.10 = 10.75 W     Max: 3.50 + 6.0 + 3.12 + 0.47 = 13.09 W'),
        (),
        ('total', '19 V supply: Jetson + USB devices', 12.28, 25.75, 28.09),
        ('text', 'Min: 7.0 + 5.28 = 12.28 W   Typ: 15.0 + 10.75 = 25.75 W   Max: 15.0 + 13.09 = 28.09 W'),
        ('text', 'Within the 40 W rating of the 19 V converter in the wiring diagram.'),
    ],
    [
        ('title', '24 V motor rail (after the E-stop)'),
        ('cols',),
        ('item', '6. Drive motor, E-S Motor 36PG-555K-24120-100, each', 0.0, 62.4, 504.0),
        ('text', 'Min: stopped, 0 W.     No load: 24 V × 0.5 A = 12.0 W'),
        ('text', 'Typ (rated load): 24 V × 2.6 A = 62.4 W'),
        ('text', 'Max (stall): 24 V × 21 A = 504 W.  The MD10C allows 13 A continuous: 24 × 13 = 312 W,'),
        ('text', 'so the firmware must limit current; a stall is a fault, not normal running.'),
        ('item', '    × 2 drive motors', 0.0, 124.8, 1008.0),
        (),
        ('item', '7. Dispenser stepper, StepperOnline 17HS19-2004S1, each', 0.0, 2.70, 3.96),
        ('text', 'With a chopper driver the winding power is P = I_limit² × R, the same at every step.'),
        ('text', 'Min: driver asleep, 0 W.     Typ (1.3 A limit): (1.3 A)² × 1.60 ohm = 2.70 W'),
        ('text', 'Max (1.5 A limit, R +10%): (1.5 A)² × 1.76 ohm = 3.96 W'),
        ('text', 'For reference, at the 2.0 A rating: (2.0 A)² × 1.60 ohm = 6.40 W'),
        ('item', '8. DRV8825 stepper driver, each', 0.0005, 0.78, 1.60),
        ('text', 'Supply: sleep 24 V × 20 µA = 0.0005 W; on 24 V × 5 mA = 0.12 W (8 mA max: 0.19 W)'),
        ('text', 'FET loss = 4 × R_DS(on) × (0.7 × I_limit)²'),
        ('text', 'Typ: 4 × 0.20 ohm × (0.7 × 1.3 A)² = 0.66 W  ->  0.66 + 0.12 = 0.78 W'),
        ('text', 'Max: 4 × 0.32 ohm × (0.7 × 1.5 A)² = 1.41 W  ->  1.41 + 0.19 = 1.60 W'),
        ('item', '    × 2 (stepper + driver)', 0.001, 6.96, 11.12),
        ('text', 'Typ: 2 × (2.70 + 0.78) = 6.96 W     Max: 2 × (3.96 + 1.60) = 11.12 W'),
        (),
        ('item', '9. Headlight, goBILDA 3118-0102-0002, each (Est.)', 0.0, 4.5, 5.0),
        ('text', 'Not published.  Est.: 400 lm / ~90 lm per W = 4.5 W; Max 5 W = 24 V × 0.21 A.'),
        ('text', 'Measure at 24 V to replace this estimate.'),
        ('item', '    × 2 headlights (quantity assumed)', 0.0, 9.0, 10.0),
        (),
        ('total', '24 V motor rail, motors at rated load', 0.001, 140.76, 145.92),
        ('text', 'Typ: 124.8 + 6.96 + 9.0 = 140.76 W     Max: 124.8 + 11.12 + 10.0 = 145.92 W'),
        ('total', '24 V motor rail, both drive motors stalled', None, None, 1029.12),
        ('text', 'Peak: 1008 + 11.12 + 10.0 = 1029.12 W (about 43 A at 24 V; the main fuse is 40 A)'),
    ],
    [
        ('title', '12 V arm rail (12 V buck after the E-stop)'),
        ('cols',),
        ('item', '10. Arm motor, Yahboom MD520Z19 (12 V), each', 0.0, 3.6, 4.0),
        ('text', 'Min: stopped, 0 W.     Typ (rated): 12 V × 0.3 A = 3.6 W (Yahboom: <= 4 W)'),
        ('text', 'Stall at full PWM: 12 V × 3 A = 36 W.  Not allowed: the TB6612FNG is rated 1.0 A.'),
        ('text', 'Max, stall with PWM capped at 33%: winding R = 12 V / 3 A = 4 ohm'),
        ('text', 'I_motor = 0.33 × 12 V / 4 ohm = 1.0 A;  P = 0.33 × 12 V × 1.0 A = 4.0 W (= 1.0² × 4)'),
        ('item', '    × 2 arm motors', 0.0, 7.2, 8.0),
        ('item', '11. SparkFun TB6612FNG dual motor driver', 0.0, 0.09, 1.00),
        ('text', 'Logic: 3.3 V × 1.1 mA = 0.004 W (standby <= 1 µA)'),
        ('text', 'Typ FET loss: 0.15 V × 0.3 A = 0.045 W per channel, × 2 = 0.09 W'),
        ('text', 'Max FET loss: 0.5 V × 1.0 A = 0.5 W per channel, × 2 = 1.00 W'),
        (),
        ('total', '12 V arm rail', 0.0, 7.29, 9.00),
        ('text', 'Typ: 7.2 + 0.09 = 7.29 W     Max: 8.0 + 1.00 = 9.00 W'),
        (),
        ('title', '5 V status LEDs (5 V buck)'),
        ('cols',),
        ('item', '12. Status LEDs, Seeed Grove WS2813 strip, 30 LEDs', 0.0, 3.0, 9.0),
        ('text', 'Max: 30 × 0.3 W = 9.0 W (= 5 V × 1.8 A: every LED full white)'),
        ('text', 'Typ (Est.): all LEDs one colour at full: 30 × 20 mA × 5 V = 3.0 W'),
        ('text', 'Min: off, 0 W (standby draw not published)'),
        (),
        ('title', 'Summary by supply (component power, before converter losses)'),
        ('cols',),
        ('item', '19 V supply: Jetson + USB devices', 12.28, 25.75, 28.09),
        ('item', '24 V motor rail (motors at rated load)', 0.0, 140.76, 145.92),
        ('item', '12 V arm rail', 0.0, 7.29, 9.00),
        ('item', '5 V status LEDs', 0.0, 3.0, 9.0),
        ('total', 'Whole robot', 12.28, 176.80, 192.01),
        ('text', 'Typ: 25.75 + 140.76 + 7.29 + 3.0 = 176.80 W  (driving at rated load)'),
        ('text', 'Max: 28.09 + 145.92 + 9.00 + 9.0 = 192.01 W.  Peak with both drive motors stalled: 1075 W.'),
        ('text', 'Standing still (drive motors off), Typ: 176.80 - 124.8 = 52.0 W.'),
        ('text', 'Negligible: MD10C and MOSFET module logic.  Still to measure: headlights.'),
    ],
]


def _baseline(row):
    """Text baseline of a grid row, in PDF coordinates (origin at the bottom)."""
    return PAGE_H - (GRID_TOP + (row + 1) * CELL - 4.0)


def _col_x(col):
    return GRID_X0 + col * CELL


def _fit(c, text, font, size, width):
    while stringWidth(text, font, size) > width and size > 6:
        size -= 0.25
    c.setFont(font, size)


def _value(v):
    if v is None:
        return ''
    if v == 0:
        return '0'
    if v < 0.01:
        return f'{v:.4f}'.rstrip('0')
    return f'{v:.2f}'


def _overlay(sheet, number, total):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(612, PAGE_H))
    c.setFillColorRGB(*INK)
    c.setStrokeColorRGB(*INK)

    c.setFont('Helvetica', 9.5)
    for x, y, text in HEADER.values():
        c.drawString(x, PAGE_H - y + 2.5, text)
    c.drawCentredString(SHEET_NUM_X, PAGE_H - SHEET_Y + 2, str(number))
    c.drawCentredString(OF_X, PAGE_H - SHEET_Y + 2, str(total))

    assert len(sheet) <= ROWS, f'sheet {number} has {len(sheet)} rows; the grid has {ROWS}'
    values_left = _col_x(VALUE_COLS['min'] - 3.5)
    for row, entry in enumerate(sheet):
        if not entry:
            continue
        y = _baseline(row)
        kind = entry[0]
        if kind == 'title':
            _fit(c, entry[1], 'Helvetica-Bold', 9.5, GRID_X1 - GRID_X0 - 6)
            c.drawString(_col_x(0) + 3, y, entry[1])
        elif kind == 'text':
            _fit(c, entry[1], 'Helvetica', 8.0, GRID_X1 - _col_x(1) - 4)
            c.drawString(_col_x(1) + 3, y, entry[1])
        elif kind == 'cols':
            c.setFont('Helvetica-Bold', 8.0)
            for key, label in (('min', 'Min (W)'), ('typ', 'Typ (W)'), ('max', 'Max (W)')):
                c.drawRightString(_col_x(VALUE_COLS[key]) - 3, y, label)
        elif kind in ('item', 'total'):
            name, *values = entry[1:]
            font = 'Helvetica-Bold' if kind == 'total' else 'Helvetica'
            _fit(c, name, font, 8.5, values_left - _col_x(0) - 6)
            c.drawString(_col_x(0) + 3, y, name)
            c.setFont(font, 8.5)
            for key, v in zip(('min', 'typ', 'max'), values):
                c.drawRightString(_col_x(VALUE_COLS[key]) - 3, y, _value(v))
            if kind == 'total':
                top = PAGE_H - (GRID_TOP + row * CELL)
                c.setLineWidth(0.9)
                c.rect(values_left, top - CELL, GRID_X1 - values_left, CELL)
    c.save()
    buf.seek(0)
    return PdfReader(buf).pages[0]


def main():
    writer = PdfWriter()
    for number, sheet in enumerate(SHEETS, start=1):
        page = writer.add_page(PdfReader(TEMPLATE).pages[0])
        page.merge_page(_overlay(sheet, number, len(SHEETS)))
    with open(OUTPUT, 'wb') as f:
        writer.write(f)
    print(f'wrote {OUTPUT}')


if __name__ == '__main__':
    main()
