"""Regression tests for the pinned city boundary; no network or dependencies.

The fixture is output (trailing whitespace removed) from GitWorld commit
76fe1d0ad8b59801e0352616cd040eece376c8cb, executed with Node 24.22.1 and a
mocked zero-contribution calendar for Jorge-Lana. No real token was used.
"""

from pathlib import Path
import runpy
import tempfile
import unittest
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
prepare = runpy.run_path(str(HERE.parent / "prepare_city.py"))["prepare"]
CITY = (HERE / "fixtures" / "gitworld-zero.svg").read_text(encoding="utf-8")
# Structure-only profile fixture: full visual rendering is exercised separately
# by the local renderer tests. Keep the legacy fixture unchanged for rollback.
DARK_CITY = (CITY.replace('<svg ', '<svg data-theme="dark-isometric-v1" role="img" ', 1)
             .replace('width="900" height="260"', 'width="1200" height="720"', 1)
             .replace('viewBox="0 0 900 260"', 'viewBox="0 0 1200 720"', 1)
             .replace('<defs>', '<title>Night City</title><desc>Weekly activity</desc><defs>', 1))


class CityValidationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name) / "input.svg"
        self.output = Path(self.directory.name) / "output.svg"

    def validate(self, svg):
        self.source.write_text(svg, encoding="utf-8")
        prepare(self.source, self.output)
        return self.output.read_text(encoding="utf-8")

    def reject(self, svg):
        self.output.unlink(missing_ok=True)
        self.source.write_text(svg, encoding="utf-8")
        with self.assertRaises((ValueError, ET.ParseError)):
            prepare(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_pinned_city_preserves_animations(self):
        result = self.validate(CITY)
        self.assertEqual(result, CITY.replace("0 commits", "0 contributions"))
        self.assertIn("@keyframes", result)
        self.assertIn("<animateMotion", result)

    def test_idempotent(self):
        first = self.validate(CITY)
        self.assertEqual(first, self.validate(first))

    def test_malformed_xml(self):
        self.reject(CITY[:-8])

    def test_disallowed_elements(self):
        for tag in ("script", "foreignObject", "image", "animate", "set"):
            with self.subTest(tag=tag):
                self.reject(CITY.replace("</svg>", f"<{tag}/></svg>"))

    def test_event_attributes(self):
        for name in ("onload", "onclick", "ONLOAD"):
            with self.subTest(attribute=name):
                self.reject(CITY.replace('<svg ', f'<svg {name}="alert(1)" ', 1))

    def test_external_resources(self):
        for value in ("https://example.invalid/x", "//example.invalid/x", "data:image/svg+xml,x"):
            with self.subTest(value=value):
                self.reject(CITY.replace('fill="url(#sky)"', f'fill="url({value})"', 1))
        self.reject(CITY.replace('<svg ', '<svg href="//example.invalid/x" ', 1))

    def test_numeric_xml_references_in_css(self):
        # These passed the original raw-string checks: XML decoding turns them
        # into url(//...) and @import before the browser interprets the CSS.
        payloads = (
            '.star { fill: u&#114;l(//example.invalid/x); }',
            '@im&#112;ort "//example.invalid/x";',
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                self.reject(CITY.replace("<style>", "<style>" + payload, 1))
        self.reject(CITY.replace("url(#sky)", "u&#114;l(&#47;&#47;example.invalid/x)", 1))

    def test_css_escapes_comments_and_unexpected_functions(self):
        for value in (r"u\72l(//example.invalid/x)", "u/**/rl(//example.invalid/x)",
                      'image-set("//example.invalid/x")', 'expression(alert(1))',
                      'url(#missing)', 'url(relative.svg', 'url(#sky', 'url()',
                      '''url("'#sky")''', '''url('#sky")'''):
            with self.subTest(value=value):
                payload = f".star {{ fill: {value}; }}"
                self.reject(CITY.replace("<style>", "<style>" + payload, 1))

    def test_namespace_and_processing_instruction(self):
        self.reject(CITY.replace('<svg ', '<svg xml:base="//example.invalid/" ', 1))
        self.reject(CITY.replace('<svg ', '<svg xmlns:e="urn:unreviewed" e:fill="red" ', 1))
        self.reject(CITY.replace("<style>", '<style xmlns="urn:unreviewed">', 1))
        self.reject('<?xml-stylesheet href="//example.invalid/x"?>' + CITY)

    def test_identity_dimensions_and_profile_card(self):
        for old, new in (("Jorge-Lana", "another-user"), ("0 0 900 260", "0 0 960 1440"),
                         ('width="900"', 'width="960"'), ('height="260"', 'height="1440"')):
            with self.subTest(old=old):
                self.reject(CITY.replace(old, new, 1))

    def test_dtd_oversized_and_symlink(self):
        self.reject('<!DOCTYPE svg [<!ENTITY x "test">]>' + CITY)
        self.reject("x" * (1024 * 1024 + 1))
        self.source.unlink()
        self.source.symlink_to(HERE / "fixtures" / "gitworld-zero.svg")
        with self.assertRaises(ValueError):
            prepare(self.source, self.output)

    def test_dark_profile_and_idempotence(self):
        first = self.validate(DARK_CITY)
        self.assertEqual(first, DARK_CITY.replace("0 commits", "0 contributions"))
        self.assertEqual(first, self.validate(first))

    def test_dark_only_dimensions_and_attributes(self):
        for old, new in (("dark-isometric-v1", "unreviewed-theme"),
                         ('width="1200"', 'width="900"'),
                         ('height="720"', 'height="260"')):
            with self.subTest(old=old):
                self.reject(DARK_CITY.replace(old, new, 1))
        self.reject(CITY.replace('<svg ', '<svg role="img" ', 1))
        self.reject(DARK_CITY.replace('<svg ', '<svg href="#sky" ', 1))
        self.reject(DARK_CITY.replace('<svg ', '<svg xml:base="//example.invalid/" ', 1))

    def test_dark_reduced_motion_and_transforms(self):
        css = '@media (prefers-reduced-motion: reduce) { .moving { display:none; } .light { animation:none; } }'
        svg = DARK_CITY.replace('<style>', '<style>' + css, 1)
        svg = svg.replace('<g>', '<g transform="translate(1,2)" data-intensity="0.5">', 1)
        self.assertIn(css, self.validate(svg))
        self.reject(CITY.replace('<style>', '<style>' + css, 1))

    def test_dark_css_security_boundary(self):
        for css in ('@media (prefers-color-scheme: dark) { .star { opacity:0; } }',
                    '@media (prefers-reduced-motion: reduce) { .star { fill:u&#114;l(//example.invalid/x); } }',
                    '@import "//example.invalid/x";', r'.star { fill:u\72l(//example.invalid/x); }'):
            with self.subTest(css=css):
                self.reject(DARK_CITY.replace('<style>', '<style>' + css, 1))


if __name__ == "__main__":
    unittest.main()
