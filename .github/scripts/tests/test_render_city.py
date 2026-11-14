"""Regression checks for the deterministic, contribution-driven dark renderer."""

from pathlib import Path
import re
import runpy
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "render_city.py"
renderer = runpy.run_path(str(SCRIPT))
load_activity = renderer["load_activity"]
render_svg = renderer["render_svg"]
prepare = runpy.run_path(str(HERE.parent / "prepare_city.py"))["prepare"]
FLAT = (HERE / "fixtures" / "gitworld-zero.svg").read_text(encoding="utf-8").replace(
    "0 commits", "0 contributions"
)
NS = "{http://www.w3.org/2000/svg}"


class DarkRendererTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name) / "flat.svg"

    def load(self, text):
        self.source.write_text(text, encoding="utf-8")
        return load_activity(self.source)

    def flat_with_columns(self, columns):
        groups = "".join(
            f'<g class="col" data-week="{week}"><rect x="0" y="55" '
            f'width="16.3" height="{height}"/></g>'
            for week, height in columns
        )
        return FLAT.replace("0 contributions", "102 contributions").replace(
            "</svg>", groups + "</svg>"
        )

    def test_zero_calendar_keeps_all_52_lots(self):
        heights, total = self.load(FLAT)
        self.assertEqual(heights, [0] * 52)
        self.assertEqual(total, 0)
        root = ET.fromstring(render_svg(heights, total))
        lots = [element for element in root.iter() if "data-week" in element.attrib]
        self.assertEqual(sorted(int(lot.get("data-week")) for lot in lots), list(range(52)))

    def test_sparse_calendar_keeps_original_week_positions(self):
        heights, total = self.load(self.flat_with_columns([(0, 11), (25, 75), (51, 140)]))
        expected = [0] * 52
        expected[0], expected[25], expected[51] = 11, 75, 140
        self.assertEqual(heights, expected)
        self.assertEqual(total, 102)

    def test_full_max_calendar_is_deterministic_and_contribution_labeled(self):
        heights, total = self.load(self.flat_with_columns([(i, 140) for i in range(52)]))
        svg = render_svg(heights, total)
        self.assertEqual(svg, render_svg(heights, total))
        root = ET.fromstring(svg)
        self.assertEqual(root.tag, NS + "svg")
        self.assertEqual(root.get("viewBox"), "0 0 1200 720")
        self.assertEqual(root.get("data-theme"), "dark-isometric-v1")
        self.assertIn("Jorge-Lana's GitWorld · 102 contributions", "".join(root.itertext()))
        lots = [element for element in root.iter() if "data-week" in element.attrib]
        self.assertEqual(len(lots), 52)
        self.assertNotIn("102 commits", svg)

    def test_animation_and_reduced_motion_remain_self_contained(self):
        svg = render_svg([70] * 52, 102)
        root = ET.fromstring(svg)
        self.assertIn("@keyframes", svg)
        self.assertIn("prefers-reduced-motion: reduce", svg)
        self.assertIsNotNone(root.find(".//" + NS + "animateMotion"))
        for element in root.iter():
            self.assertNotIn(element.tag, {NS + "script", NS + "foreignObject", NS + "image"})
            for name in element.attrib:
                self.assertFalse(name.lower().startswith("on"))
                self.assertNotIn(name.rsplit("}", 1)[-1], {"href", "src"})
        self.assertNotRegex(svg, r"https?://(?!www\.w3\.org/)|javascript:|@import")
        for target in re.findall(r"url\(([^)]*)\)", svg):
            self.assertTrue(target.strip(" \t\r\n\"'").startswith("#"))

    def test_actual_renderer_output_passes_publication_boundary(self):
        for heights in ([0] * 52, [0] * 47 + [140, 140, 96, 107, 71], [140] * 52):
            with self.subTest(active=sum(h > 0 for h in heights)):
                svg = render_svg(heights, 102)
                source = Path(self.directory.name) / "rendered.svg"
                checked = Path(self.directory.name) / "checked.svg"
                source.write_text(svg, encoding="utf-8")
                prepare(source, checked)
                self.assertEqual(svg, checked.read_text(encoding="utf-8"))
                self.assertLess(source.stat().st_size, 1024 * 1024)

    def test_render_rejects_invalid_data_shapes_and_ranges(self):
        for heights in ([0] * 51, [0] * 53, [0] * 51 + [-1], [0] * 51 + [141],
                        [0] * 51 + [True], [0] * 51 + ["70"], [0] * 51 + [70.5]):
            with self.subTest(heights=heights):
                with self.assertRaises(ValueError):
                    render_svg(heights, 102)
        for total in (-1, True, "102", 1.5):
            with self.subTest(total=total):
                with self.assertRaises(ValueError):
                    render_svg([0] * 52, total)

    def test_load_rejects_invalid_week_indices_and_heights(self):
        for columns in ([(0, 70), (0, 80)], [(-1, 70)], [(52, 70)], [("x", 70)],
                        [(0, -1)], [(0, 141)], [(0, "nan")], [(0, "70.5")]):
            with self.subTest(columns=columns):
                with self.assertRaises(ValueError):
                    self.load(self.flat_with_columns(columns))

    def test_load_rejects_malformed_oversized_or_wrong_profile(self):
        for text in ("<svg", "x" * (1024 * 1024 + 1),
                     FLAT.replace("Jorge-Lana", "another-user"),
                     FLAT.replace("0 0 900 260", "0 0 960 1440"),
                     '<!DOCTYPE svg [<!ENTITY x "test">]>' + FLAT,
                     self.flat_with_columns([(0, 70)]).replace('height="70"', 'height="0"')):
            with self.subTest(text=text[:90]):
                with self.assertRaises((ValueError, ET.ParseError)):
                    self.load(text)

    def test_cli_generates_an_svg_without_network_or_dependencies(self):
        self.source.write_text(FLAT, encoding="utf-8")
        output = Path(self.directory.name) / "dark.svg"
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.source), str(output)],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        root = ET.parse(output).getroot()
        self.assertEqual(root.get("data-theme"), "dark-isometric-v1")


if __name__ == "__main__":
    unittest.main()
