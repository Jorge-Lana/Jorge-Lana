"""Validate the pinned GitWorld city and correct its contributions label.

Uses only the Python standard library. Never publishes the separate profile card.
"""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def check_css(value: str, ids: set[str], dark: bool = False) -> None:
    """Accept only the unescaped CSS/resource syntax used by the pinned city."""
    # XML references have already been decoded. Reject CSS escapes rather than
    # trying to implement another decoder; the reviewed renderer needs none.
    if "\\" in value:
        raise ValueError("CSS escapes are not supported")
    value = re.sub(r"/\*.*?\*/", "", value, flags=re.DOTALL)
    if "/*" in value or "*/" in value:
        raise ValueError("Malformed CSS comment")
    if dark:
        # The local renderer has exactly this accessibility query. All other
        # media/at-rules remain unsupported; this is not a general CSS parser.
        value = value.replace("@media (prefers-reduced-motion: reduce)", "")
    if re.search(r"@(?!keyframes\b)|(?:https?|ftp|file|javascript|vbscript|data)\s*:|//|[<>&]", value, re.IGNORECASE):
        raise ValueError("External or executable CSS content is not permitted")
    functions = {"url", "rgb", "rgba", "translate", "translatex", "translatey", "rotate", "scale"}
    calls = re.findall(r"([\w-]+)\s*\(", value)
    for function in calls:
        if function.lower() not in functions:
            raise ValueError(f"Unsupported CSS function: {function}")
    targets = re.findall(r"\burl\s*\(([^()]*)\)", value, re.IGNORECASE)
    if len(targets) != sum(function.lower() == "url" for function in calls):
        raise ValueError("Malformed CSS resource reference")
    for target in targets:
        target = target.strip()
        if target.startswith(("\"", "'")):
            if len(target) < 2 or target[-1] != target[0]:
                raise ValueError("Malformed CSS resource quoting")
            target = target[1:-1]
        if not re.fullmatch(r"#[A-Za-z_][\w.-]*", target) or target[1:] not in ids:
            raise ValueError("Only references to city SVG IDs are permitted")


def prepare(source: Path, destination: Path) -> None:
    if source.is_symlink() or not source.is_file():
        raise ValueError("Expected a regular city SVG file")
    if not 0 < source.stat().st_size <= 1024 * 1024:
        raise ValueError("Unexpected city SVG size")
    svg = source.read_text(encoding="utf-8")
    if re.search(r"<!DOCTYPE|<!ENTITY|<\?", svg, re.IGNORECASE):
        raise ValueError("XML declarations and processing instructions are not permitted")
    root = ET.fromstring(svg)
    namespace = "{http://www.w3.org/2000/svg}"
    allowed = {
        "svg", "defs", "linearGradient", "stop", "filter", "feGaussianBlur",
        "feMerge", "feMergeNode", "feTurbulence", "feDisplacementMap", "rect",
        "circle", "ellipse", "g", "animateMotion", "polygon", "line", "path",
        "text", "style",
    }
    attributes = {
        "baseFrequency", "class", "cx", "cy", "d", "data-week", "dur", "fill",
        "filter", "font-family", "font-size", "height", "id", "in", "numOctaves",
        "offset", "opacity", "path", "points", "r", "repeatCount", "result", "rx",
        "ry", "scale", "stdDeviation", "stop-color", "stroke", "stroke-width",
        "style", "type", "viewBox", "width", "x", "x1", "x2", "y", "y1", "y2",
    }
    theme = root.get("data-theme")
    if theme not in (None, "dark-isometric-v1"):
        raise ValueError("Unexpected city theme")
    dark = theme == "dark-isometric-v1"
    if dark:
        allowed.update({"title", "desc"})
        attributes.update({
            "data-theme", "data-intensity", "transform", "aria-label", "role",
            "stroke-linecap", "stroke-linejoin", "stroke-dasharray", "text-anchor",
            "letter-spacing", "font-weight", "rotate",
        })
    width, height = ("1200", "720") if dark else ("900", "260")
    if (root.tag != namespace + "svg" or root.get("viewBox") != f"0 0 {width} {height}"
            or root.get("width") != width or root.get("height") != height):
        raise ValueError("Expected the city, not the profile card")
    ids = {element.get("id") for element in root.iter() if element.get("id")}
    for element in root.iter():
        if element.tag not in {namespace + tag for tag in allowed}:
            raise ValueError(f"Unexpected SVG element: {element.tag}")
        for name, value in element.attrib.items():
            # Namespaced attributes (including xml:base/xlink:href), event
            # handlers and all other unreviewed attributes are unsupported.
            if name not in attributes:
                raise ValueError(f"Unexpected SVG attribute: {name}")
            check_css(value, ids, dark)
        if element.tag == namespace + "style":
            if len(element):
                raise ValueError("Nested style elements are not supported")
            check_css(element.text or "", ids, dark)
    if root.find(".//" + namespace + "animateMotion") is None or "@keyframes" not in svg:
        raise ValueError("Expected an animated city")
    # GitHub's contribution calendar counts more than commits. Keep the drawing
    # unchanged and correct only this pinned renderer's HUD text. Idempotent so
    # the isolated publisher can independently validate the same artifact.
    pattern = r"(Jorge-Lana's GitWorld · \d+) (?:commits|contributions)"
    svg, count = re.subn(pattern, r"\1 contributions", svg)
    if count != 1:
        raise ValueError("Unexpected city identity or contribution label")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: prepare_city.py INPUT.svg OUTPUT.svg")
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))
