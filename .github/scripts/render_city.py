"""Render a self-contained night city from the pinned, validated GitWorld SVG.

No API requests, credentials, scripts or external assets. Heights retain the
upstream logarithmic weekly peak scale; they cannot recover exact weekly counts.
"""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


NS = "{http://www.w3.org/2000/svg}"


def load_activity(source: Path) -> tuple[list[int], int]:
    if source.is_symlink() or not source.is_file() or not 0 < source.stat().st_size <= 1024 * 1024:
        raise ValueError("Expected a bounded regular, validated flat SVG")
    svg = source.read_text(encoding="utf-8")
    if re.search(r"<!DOCTYPE|<!ENTITY|<\?", svg, re.IGNORECASE):
        raise ValueError("Unsupported XML declaration")
    root = ET.fromstring(svg)
    if (root.tag != NS + "svg" or root.get("viewBox") != "0 0 900 260"
            or root.get("width") != "900" or root.get("height") != "260"):
        raise ValueError("Expected the pinned flat renderer's dimensions")
    totals = re.findall(r"Jorge-Lana's GitWorld · ([0-9]+) contributions", " ".join(root.itertext()))
    if len(totals) != 1 or int(totals[0]) > 10**9:
        raise ValueError("Missing or invalid contribution identity/total")
    heights = [0] * 52
    seen = set()
    for element in root.iter(NS + "g"):
        if "col" not in element.get("class", "").split():
            continue
        index = element.get("data-week", "")
        if not re.fullmatch(r"[0-9]+", index) or not 0 <= int(index) < 52 or int(index) in seen:
            raise ValueError("Invalid or duplicate weekly column")
        body = element.find(NS + "rect")
        height = body.get("height", "") if body is not None else ""
        if not re.fullmatch(r"[0-9]+", height) or not 11 <= int(height) <= 140:
            raise ValueError("Invalid pinned building height")
        seen.add(int(index))
        heights[int(index)] = int(height)
    return heights, int(totals[0])


def project(u: float, v: float, z: float = 0) -> tuple[float, float]:
    return 480 + (u - v) * 0.85, 278 + (u + v) * 0.35 - z


def points(vertices) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in vertices)


def polygon(vertices, fill: str, extra: str = "") -> str:
    return f'<polygon points="{points(vertices)}" fill="{fill}" {extra}/>'


def world_line(start, end, color: str, width: float = 1, extra: str = "") -> str:
    x1, y1 = project(*start)
    x2, y2 = project(*end)
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{width}" {extra}/>'


def tower(u: float, v: float, height: float, week: int) -> str:
    w, d = 28, 38
    roof = [project(u, v, height), project(u+w, v, height), project(u+w, v+d, height), project(u, v+d, height)]
    a, b, c, e = roof
    B, C, D = project(u+w, v), project(u+w, v+d), project(u, v+d)
    parts = [
        polygon([project(u+8, v+8), project(u+w+24, v+8), project(u+w+50, v+d+28), project(u+32, v+d+28)], "#020713", 'opacity="0.5"'),
        polygon([b, c, C, B], "#192c50", 'stroke="#30496c" stroke-width="0.6"'),
        polygon([c, e, D, C], "#26385f", 'stroke="#3b5078" stroke-width="0.6"'),
        polygon(roof, "#40527a", 'stroke="#8b9fcb" stroke-width="0.7"'),
    ]
    floors = max(1, min(10, int(height / 14)))
    for floor in range(floors):
        z = 8 + floor * (height - 16) / max(floors, 1)
        for column in range(3):
            lit = (week * 3 + floor + column * 5) % 7 != 0
            color = ("#8de9ee" if (week + floor) % 3 else "#b8a8ff") if lit else "#13233f"
            extra = f'class="light window" style="animation-delay:-{(week+floor+column)%17}s"' if lit else ""
            x = u + 4 + column * 7
            y = v + 5 + column * 10
            parts.append(polygon([project(x, v+d+.2, z), project(x+3, v+d+.2, z), project(x+3, v+d+.2, z+4), project(x, v+d+.2, z+4)], color, extra))
            parts.append(polygon([project(u+w+.2, y, z), project(u+w+.2, y+4, z), project(u+w+.2, y+4, z+4), project(u+w+.2, y, z+4)], color, extra))
    # A roof service core and subdued perimeter lights give every tower depth.
    top = height + 5
    parts.append(polygon([project(u+6, v+9, top), project(u+20, v+9, top), project(u+20, v+24, top), project(u+6, v+24, top)], "#647399"))
    parts.append(world_line((u, v+d, height), (u+w, v+d, height), "#9c8bff", 1.3))
    if height > 120:
        parts.append(world_line((u+14, v+16, height+5), (u+14, v+16, height+19), "#a2b1d3"))
        x, y = project(u+14, v+16, height+20)
        parts.append(f'<circle class="light beacon" cx="{x:.1f}" cy="{y:.1f}" r="1.8" fill="#75e8ee" filter="url(#glow)"/>')
    return "".join(parts)


def lot(week: int, intensity: int) -> str:
    row, column = divmod(week, 13)
    u, v = 12 + column * 48, 15 + row * 78
    base = polygon([project(u-3, v-4), project(u+32, v-4), project(u+32, v+43), project(u-3, v+43)], "#12203a", 'stroke="#273553" stroke-width="0.7"')
    if intensity:
        # Remove the upstream 10px baseline; preserve the rounded log scale.
        height = 25 + (intensity - 10) / 130 * 150
        content = tower(u, v, height, week)
    else:
        # Empty weeks remain parks, never fabricated contribution buildings.
        content = ""
        for a, b in ((8, 8), (18, 28)):
            x, y = project(u+a, v+b)
            content += f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="5" ry="2" fill="#091627"/>'
            content += polygon([project(u+a-3, v+b, 2), project(u+a, v+b-4, 8), project(u+a+4, v+b, 3), project(u+a, v+b+4, 1)], "#25464d")
        content += world_line((u+3, v+39, 1), (u+24, v+39, 1), "#37505e", .7)
    return f'<g class="lot" data-week="{week}" data-intensity="{intensity}">{base}{content}</g>'


def transit(front: bool = True) -> str:
    parts = []
    if front:
        for v in (337, 345):
            parts.append(world_line((-28, v, 2), (652, v, 2), "#6b7397", 1.1))
        for u in range(-24, 652, 14):
            parts.append(world_line((u, 335, 2), (u, 347, 2), "#3d4162", 1.8))
        start, end = project(-24, 341, 9), project(651, 341, 9)
        path = f'M {start[0]:.1f},{start[1]:.1f} L {end[0]:.1f},{end[1]:.1f}'
        cars = []
        for x in (-65, -41, -17):
            cars += [f'<rect x="{x}" y="-7" width="22" height="9" rx="2" fill="#b0b4dd"/>',
                     f'<rect x="{x+2}" y="-6" width="18" height="2" fill="#6c6cc8"/>',
                     f'<rect x="{x+3}" y="-3" width="15" height="2" fill="#a2f2ed"/>']
        parts.append(f'<g class="moving train"><animateMotion dur="28s" repeatCount="indefinite" rotate="auto" path="{path}"/>{"".join(cars)}<circle cx="5" cy="-2" r="2" fill="#d4fff9" filter="url(#glow)"/></g>')
    # Rear traffic is painted before the towers, so it cannot float over them.
    for index, (v, reverse) in enumerate(((315, True),) if front else ((-15, False),)):
        a, b = project(-20, v, 3), project(650, v, 3)
        if reverse:
            a, b = b, a
        route = f'M {a[0]:.1f},{a[1]:.1f} L {b[0]:.1f},{b[1]:.1f}'
        parts.append(f'<g class="moving traffic"><animateMotion dur="{19+index*9}s" repeatCount="indefinite" rotate="auto" path="{route}"/><rect x="-7" y="-3" width="13" height="6" rx="2" fill="#8b8cd5"/><rect x="-3" y="-2" width="5" height="3" fill="#314366"/><circle cx="6" cy="-2" r="1" fill="#c1ffef"/><circle cx="6" cy="2" r="1" fill="#c1ffef"/></g>')
    return "".join(parts)


def render_svg(heights: list[int], total: int) -> str:
    if (len(heights) != 52 or any(type(h) is not int or not 0 <= h <= 140 for h in heights)
            or type(total) is not int or not 0 <= total <= 10**9):
        raise ValueError("Expected 52 bounded integer intensities and a contribution total")
    background = []
    for index in range(65):
        x, y = 28 + index * 173 % 1140, 20 + index * 71 % 270
        background.append(f'<circle class="light star" cx="{x}" cy="{y}" r="{.6 if index%4 else 1}" fill="#849dc9" style="animation-delay:-{index%13}s"/>')
    for index in range(28):
        x, height = 40 + index * 41, 20 + (index * 37) % 93
        background.append(f'<rect x="{x}" y="{320-height}" width="25" height="{height}" fill="#1c2a47" opacity="0.45"/>')
        background.append(polygon([(x+25, 320-height), (x+32, 315-height), (x+32,315), (x+25,320)], "#26314f", 'opacity="0.3"'))
    corners = [(-34, -30), (660, -30), (660, 357), (-34, 357)]
    roof = [project(u, v) for u, v in corners]
    base = [project(u, v, -18) for u, v in corners]
    platform = polygon([roof[1], roof[2], base[2], base[1]], "#161f37")
    platform += polygon([roof[2], roof[3], base[3], base[2]], "#0c1428")
    platform += polygon(roof, "url(#ground)", 'stroke="#47517c" stroke-width="1.2"')
    streets = []
    for u in range(0, 625, 48):
        streets.append(world_line((u, -22, 1), (u, 316, 1), "#293751", 1))
    for v in (0, 64, 142, 220, 301, 315):
        streets.append(world_line((-24, v, 1), (652, v, 1), "#0b1326", 9))
        streets.append(world_line((-24, v, 1.2), (652, v, 1.2), "#52617b", .6, 'stroke-dasharray="4 11"'))
    for v in (-25, 352):
        streets.append(world_line((-29, v, 1), (655, v, 1), "#6669b6", 1.2))
    # Painter's order follows world depth, not contribution value.
    order = sorted(range(52), key=lambda i: (i % 13) * 48 + (i // 13) * 78)
    buildings = "".join(lot(i, heights[i]) for i in order)
    active = sum(h > 0 for h in heights)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720" viewBox="0 0 1200 720" data-theme="dark-isometric-v1" role="img" aria-label="Jorge-Lana's dark isometric contribution city">
<title>Night City — Jorge-Lana</title>
<desc>52 weekly lots. Building heights show relative weekly peak contribution intensity from GitWorld; empty weeks are parks. Background skyline and transit are decorative. Animated SVG, not interactive 3D.</desc>
<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#070c1c"/><stop offset="65%" stop-color="#131c38"/><stop offset="100%" stop-color="#0b1122"/></linearGradient>
<linearGradient id="ground" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#202b48"/><stop offset="100%" stop-color="#101c32"/></linearGradient>
<filter id="glow"><feGaussianBlur stdDeviation="2" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="haze"><feGaussianBlur stdDeviation="18"/></filter>
</defs>
<rect width="1200" height="720" rx="18" fill="url(#sky)"/>
<rect x=".5" y=".5" width="1199" height="719" rx="18" fill="none" stroke="#293350"/>
<ellipse cx="610" cy="350" rx="425" ry="100" fill="#564bba" opacity="0.09" filter="url(#haze)"/>
{"".join(background)}
<g font-family="monospace">
<circle cx="50" cy="39" r="3" fill="#7ee6df" filter="url(#glow)"/>
<text x="65" y="43" fill="#a1a9c9" font-size="11" letter-spacing="2">JORGE LANA / ACTIVITY ATLAS</text>
<text x="1150" y="43" text-anchor="end" fill="#767caa" font-size="11" letter-spacing="2">NIGHT DISTRICT · 01</text>
<text x="48" y="95" font-size="37" font-weight="700" fill="#e3e9fc" letter-spacing="3">NIGHT CITY</text>
<text x="50" y="122" font-size="12" fill="#8797bb">52 weekly lots · relative peak intensity · updated daily</text>
<text x="50" y="151" font-size="13" fill="#aabde1">Jorge-Lana's GitWorld · {total} contributions</text>
</g>
<ellipse cx="600" cy="610" rx="410" ry="32" fill="#040916" opacity="0.7" filter="url(#haze)"/>
{platform}{"".join(streets)}{transit(False)}
{buildings}
{transit()}
<g class="moving fog" opacity="0.06" filter="url(#haze)"><ellipse cx="570" cy="337" rx="380" ry="14" fill="#9f9bdd"/><ellipse cx="550" cy="485" rx="220" ry="9" fill="#7e9bce"/></g>
<g font-family="monospace" font-size="10" fill="#8e9cbb">
<line x1="50" y1="660" x2="1150" y2="660" stroke="#28334e"/>
<circle cx="55" cy="685" r="3" fill="#8c8ee3"/><text x="68" y="689">{active:02d} ACTIVE WEEKS / 52 LOTS</text>
<text x="600" y="689" text-anchor="middle">LOW — RELATIVE WEEKLY PEAK — HIGH</text>
<text x="1150" y="689" text-anchor="end">PARKS = ZERO ACTIVITY</text>
</g>
<style>
.star {{ animation: breathe 9s ease-in-out infinite alternate; }}
.window {{ animation: windows 19s ease-in-out infinite; }}
.beacon {{ animation: breathe 4s ease-in-out infinite alternate; }}
.fog {{ animation: mist 24s ease-in-out infinite alternate; }}
@keyframes breathe {{ from {{opacity:0.35}} to {{opacity:0.85}} }}
@keyframes windows {{ 0%,90%,100% {{opacity:0.85}} 94% {{opacity:0.35}} }}
@keyframes mist {{ from {{transform:translateX(-10px)}} to {{transform:translateX(12px)}} }}
@media (prefers-reduced-motion: reduce) {{ .moving {{display:none}} .light {{animation:none}} }}
</style>
</svg>
'''


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: render_city.py VALIDATED_FLAT.svg DARK.svg")
    activity, total = load_activity(Path(sys.argv[1]))
    output = Path(sys.argv[2])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_svg(activity, total), encoding="utf-8")
