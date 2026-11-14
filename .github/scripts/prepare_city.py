"""Validate the pinned GitWorld city and correct its contributions label.

Uses only the Python standard library. Never publishes the separate profile card.
"""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def prepare(source: Path, destination: Path) -> None:
    if source.is_symlink() or not source.is_file():
        raise ValueError("Expected a regular city SVG file")
    if not 0 < source.stat().st_size <= 1024 * 1024:
        raise ValueError("Unexpected city SVG size")
    svg = source.read_text(encoding="utf-8")
    if re.search(r"<!DOCTYPE|<!ENTITY", svg, re.IGNORECASE):
        raise ValueError("XML declarations are not permitted")
    root = ET.fromstring(svg)
    namespace = "{http://www.w3.org/2000/svg}"
    allowed = {
        "svg", "defs", "linearGradient", "stop", "filter", "feGaussianBlur",
        "feMerge", "feMergeNode", "feTurbulence", "feDisplacementMap", "rect",
        "circle", "ellipse", "g", "animateMotion", "polygon", "line", "path",
        "text", "style",
    }
    if root.tag != namespace + "svg" or root.get("viewBox") != "0 0 900 260":
        raise ValueError("Expected the city, not the profile card")
    for element in root.iter():
        if element.tag not in {namespace + tag for tag in allowed}:
            raise ValueError(f"Unexpected SVG element: {element.tag}")
        for name, value in element.attrib.items():
            local_name = name.rsplit("}", 1)[-1].lower()
            if local_name.startswith("on"):
                raise ValueError("SVG event handlers are not permitted")
            if local_name in {"href", "src"} and not value.startswith("#"):
                raise ValueError("External SVG resources are not permitted")
    if re.search(r"@(?:import|font-face)|https?://(?!www\.w3\.org/)|javascript:|data:", svg, re.IGNORECASE):
        raise ValueError("External or executable SVG content is not permitted")
    for target in re.findall(r"url\(([^)]*)\)", svg, re.IGNORECASE):
        if not target.strip(" \t\r\n\"'").startswith("#"):
            raise ValueError("Only internal SVG resource references are permitted")
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
