import math
import subprocess


SVG_DEFS = '''  <defs>
    <marker id="arrow1" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto" markerUnits="userSpaceOnUse">
      <polygon points="0 0, 8 3, 0 6" fill="black"/>
    </marker>
    <marker id="arrow2" markerWidth="10" markerHeight="8" refX="10" refY="4" orient="auto" markerUnits="userSpaceOnUse">
      <polygon points="0 0, 10 4, 0 8" fill="black"/>
    </marker>
  </defs>'''


def make_svg(width, height, *content_blocks, border=0):
    inner = "\n".join(content_blocks)
    if border:
        inner = f'<g transform="translate({border},{border})">\n{inner}\n</g>'
    w, h = width + 2 * border, height + 2 * border
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">\n{SVG_DEFS}\n{inner}\n</svg>'


def save_svg_and_png(svg, base_path):
    svg_path = base_path + ".svg"
    png_path = base_path + ".png"
    with open(svg_path, "w") as f:
        f.write(svg)
    subprocess.run(["rsvg-convert", svg_path, "-o", png_path], check=True)
    return svg_path, png_path


def _legend_svg(cx, y, legend):
    lines = [legend] if isinstance(legend, str) else legend
    tspans = "".join(
        f'<tspan x="{cx}" dy="{"0" if i == 0 else "1.4em"}">{line}</tspan>'
        for i, line in enumerate(lines)
    )
    return f'\n  <text x="{cx}" y="{y}" text-anchor="middle" font-family="sans-serif" font-size="13" fill="black">{tspans}</text>'


def phasor_clock(cx, cy, outer_radius, angle1_deg, radius1_pc, angle2_deg, radius2_pc, legend=None, legend_gap=10, stroke_width_light = 1.5, stroke_width_heavy = 2.5):
    def endpoint(angle_deg, radius_pc):
        a = math.radians(angle_deg)
        return cx + outer_radius * radius_pc * math.cos(a), cy - outer_radius * radius_pc * math.sin(a)

    x1, y1 = endpoint(angle1_deg, radius1_pc)
    x2, y2 = endpoint(angle2_deg, radius2_pc)

    return (
        f'  <circle cx="{cx}" cy="{cy}" r="{outer_radius}" stroke="black" stroke-width="1.5" fill="none"/>\n'
        f'  <line x1="{cx}" y1="{cy}" x2="{x1:.2f}" y2="{y1:.2f}" stroke="black" stroke-width="{stroke_width_light}" marker-end="url(#arrow1)"/>\n'
        f'  <line x1="{cx}" y1="{cy}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="black" stroke-width="{stroke_width_heavy}" marker-end="url(#arrow2)"/>\n'
        f'  <circle cx="{cx}" cy="{cy}" r="3" fill="black"/>'
        + (_legend_svg(cx, cy + outer_radius + legend_gap, legend) if legend else '')
    )


LEGEND_FONT_SIZE = 13
LEGEND_LINE_HEIGHT = LEGEND_FONT_SIZE * 1.4


def _legend_line_count(spec):
    if len(spec) < 5 or spec[4] is None:
        return 0
    return len(spec[4]) if isinstance(spec[4], list) else 1


def make_clock_grid_svg(clock_specs, grid_cols=3, clock_size=150, padding=20,
                        border=20, legend_gap=26, row_titles=None,
                        row_title_pad_above=20, row_title_pad_below=0):
    outer_radius = 0.9 * clock_size / 2
    cell_w = clock_size + 2 * padding
    grid_rows = math.ceil(len(clock_specs) / grid_cols)
    row_titles = (row_titles or []) + [None] * grid_rows

    def row_cell_height(r):
        row_specs = clock_specs[r * grid_cols:(r + 1) * grid_cols]
        max_lines = max((_legend_line_count(s) for s in row_specs), default=0)
        legend_h = (legend_gap + LEGEND_FONT_SIZE + (max_lines - 1) * LEGEND_LINE_HEIGHT) if max_lines else 0
        return clock_size + legend_h + 2 * padding

    row_y = []
    y = 0
    for r in range(grid_rows):
        title_space = (row_title_pad_above + row_title_pad_below) if row_titles[r] else 0
        row_y.append((y, title_space))
        y += title_space + row_cell_height(r)

    total_height = y
    row_width = grid_cols * cell_w

    blocks = []
    for r in range(grid_rows):
        y0, title_space = row_y[r]
        if row_titles[r]:
            blocks.append(
                f'  <text x="{row_width / 2}" y="{y0 + row_title_pad_above}"'
                f' text-anchor="middle" font-family="sans-serif" font-size="14"'
                f' font-weight="bold" fill="black">{row_titles[r]}</text>'
            )
        for col in range(grid_cols):
            i = r * grid_cols + col
            if i >= len(clock_specs):
                break
            cx = col * cell_w + padding + clock_size / 2
            cy = y0 + title_space + padding + clock_size / 2
            blocks.append(phasor_clock(cx, cy, outer_radius, *clock_specs[i], legend_gap=legend_gap))

    return make_svg(row_width, total_height, *blocks, border=border)


if __name__ == "__main__":
    # Row 1: standalone components, voltage (thin) as reference at 0°
    # Row 2: series RLC at resonance, current (bold) as reference at 0°
    #         XL = XC so |V_L| = |V_C|; the two reactive voltages cancel,
    #         leaving a purely real net impedance — same as the row-1 resistor
    clock_specs = [
        # row 1
        (0,   0.80,   0, 0.65, ["Resistor", "(V and I in phase)"]),
        (0,   0.45, -90, 0.60, ["Inductor", "(I lags V by 90°)"]),
        (0,   0.90,  90, 0.30, ["Capacitor", "(I leads V by 90°)"]),
        # row 2 — series resonant RLC: current as reference, |V_L| = |V_C|
        (0,   0.65,   0, 0.65, ["Resistor", "(unchanged)"]),
        (90,  0.55,   0, 0.65, ["Inductor at resonance", "(V leads I 90°, |V_L|=|V_C|)"]),
        (-90, 0.55,   0, 0.65, ["Capacitor at resonance", "(V lags I 90°, cancels V_L)"]),
        # row 3 — parallel resonant RLC: voltage as reference, |I_L| = |I_C|
        (0,   0.75,   0, 0.65, ["Resistor", "(unchanged)"]),
        (0,   0.75, -90, 0.55, ["Inductor at resonance", "(I lags V 90°, |I_L|=|I_C|)"]),
        (0,   0.75,  90, 0.55, ["Capacitor at resonance", "(I leads V 90°, cancels I_L)"]),
    ]
    row_titles = [
        "Random collection of R L C",
        "Series resonant R L C",
        "Parallel resonant R L C",
    ]
    svg = make_clock_grid_svg(clock_specs, grid_cols=3, row_titles=row_titles)
    save_svg_and_png(svg, "phasor_clock")
