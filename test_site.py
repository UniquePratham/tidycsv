"""Static-site tests for TidyCSV's landing/SEO pages (run from this directory:
python test_site.py)."""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

FUNCTIONAL = [
    "clean-csv-online.html",
    "remove-duplicate-csv-rows.html",
    "fix-malformed-csv.html",
    "csv-column-cleanup.html",
    "csv-delimiter-conversion.html",
    "csv-encoding-problems.html",
]
GUIDES = [
    "clean-csv-data.html",
    "csv-formatting-tool.html",
    "fix-broken-csv-file.html",
]
ALL_PAGES = FUNCTIONAL + GUIDES

EVENTS = [
    "cta_click",
    "engaged",
    "pricing_view",
    "checkout_start",
    "lead",
    "conversion",
    "visitor",
    "repeat",
]


def page(name):
    return (ROOT / name).read_text(encoding="utf-8")


class PageStructureTests(unittest.TestCase):
    def test_all_nine_pages_exist(self):
        for name in ALL_PAGES:
            self.assertTrue((ROOT / name).is_file(), f"missing page: {name}")

    def test_pages_have_unique_titles_h1_and_canonical(self):
        titles = set()
        for name in ALL_PAGES:
            html = page(name)
            m = re.search(r"<title>([^<]+)</title>", html)
            self.assertIsNotNone(m, f"{name}: no title")
            titles.add(m.group(1))
            self.assertGreater(len(m.group(1)), 20, f"{name}: title too short")
            self.assertEqual(len(re.findall(r"<h1[ >]", html)), 1, f"{name}: need exactly one h1")
            canon = re.search(r'<link rel="canonical" href="([^"]+)"', html)
            self.assertIsNotNone(canon, f"{name}: no canonical")
            self.assertEqual(canon.group(1),
                             f"https://uniquepratham.github.io/tidycsv/{name}")
        self.assertEqual(len(titles), len(ALL_PAGES), "titles must be unique")

    def test_pages_indexable_and_use_stylesheet(self):
        for name in ALL_PAGES:
            html = page(name)
            self.assertIn('name="robots" content="index,follow"', html, name)
            self.assertIn('<link rel="stylesheet" href="site.css">', html, name)
            self.assertTrue((ROOT / "site.css").is_file())

    def test_no_remote_assets_or_trackers(self):
        asset_re = (r'<script[^>]+src="(https?://[^"]+)"|'
                    r'<link[^>]+rel="stylesheet"[^>]+href="(https?://[^"]+)"|'
                    r'<img[^>]+src="(https?://[^"]+)"')
        for name in ALL_PAGES:
            html = page(name)
            remote = [g for m in re.finditer(asset_re, html) for g in m.groups() if g]
            self.assertEqual(remote, [], f"{name}: remote asset {remote}")
            self.assertNotIn("google-analytics", html.lower())
            self.assertNotIn("googletagmanager", html.lower())
            self.assertNotIn("facebook.net", html.lower())

    def test_measurement_is_local_session_log(self):
        for name in ALL_PAGES:
            html = page(name)
            self.assertIn('src="zf-track.js"', html, name)
            self.assertIn("no third-party", html.lower(), name)
            self.assertIn("window.ZF_TRACKING", html, name)
            self.assertIn("exp_006", html, name)
            self.assertIn("tidycsv", html, name)

    def test_footer_honest_pricing_and_service_link(self):
        for name in ALL_PAGES:
            html = page(name)
            self.assertIn("$9", html, f"{name}: missing unlock price")
            self.assertIn("../csv-fix-service/index.html", html, f"{name}: no service link")


class FunctionalPageTests(unittest.TestCase):
    def test_functional_pages_mount_tool_and_load_core(self):
        for name in FUNCTIONAL:
            html = page(name)
            self.assertIn('<div id="tool"></div>', html, name)
            self.assertIn('src="tidycsv.js"', html, name)
            self.assertIn('src="seo-tool.js"', html, name)
            self.assertIn("window.ZF_PAGE", html, name)
            cfg = re.search(r"window\.ZF_PAGE = \{([^}]*)\}", html)
            self.assertIsNotNone(cfg, name)
            body = cfg.group(1)
            self.assertIn("focus:", body, name)
            if 'mode: "' not in body:   # mode pages focus on everything
                focus = re.search(r"focus: \[([^\]]*)\]", body).group(1)
                self.assertGreater(len(focus), 0, f"{name}: focus must not be empty")

    def test_functional_pages_link_the_tool_and_service(self):
        for name in FUNCTIONAL:
            html = page(name)
            if name == "clean-csv-online.html":
                self.assertIn('href="index.html"', html, name)
            else:
                self.assertIn('href="clean-csv-online.html"', html, name)
            self.assertIn('href="../csv-fix-service/index.html"', html, name)

    def test_page_specific_focus_rules(self):
        focus = {
            "remove-duplicate-csv-rows.html": ["duplicate_rows", "empty_rows"],
            "fix-malformed-csv.html": ["header_noise", "empty_rows"],
            "csv-column-cleanup.html": ["whitespace", "header_noise"],
        }
        for name, rules in focus.items():
            html = page(name)
            m = re.search(r"window\.ZF_PAGE = \{focus: \[([^\]]*)\]", html)
            self.assertIsNotNone(m, name)
            for rule in rules:
                self.assertIn(f'"{rule}"', m.group(1), f"{name}: focus missing {rule}")

    def test_mode_pages(self):
        self.assertIn('mode: "delimiter"',
                      page("csv-delimiter-conversion.html"))
        self.assertIn('mode: "encoding"',
                      page("csv-encoding-problems.html"))


class GuidePageTests(unittest.TestCase):
    def test_guides_are_articles_without_tool_widget(self):
        for name in GUIDES:
            html = page(name)
            self.assertNotIn('<div id="tool"></div>', html, name)
            self.assertNotIn('src="seo-tool.js"', html, name)
            self.assertIn("<article>", html, name)
            self.assertIn('href="clean-csv-online.html"', html, name)
            self.assertIn("../csv-fix-service/index.html", html, name)

    def test_broken_file_guide_covers_symptoms(self):
        html = page("fix-broken-csv-file.html")
        for needle in ("single column", "wrong number of fields", "BOM",
                       "delimiter-conversion.html", "csv-encoding-problems.html"):
            self.assertIn(needle, html, needle)

    def test_checklist_guide_covers_order(self):
        html = page("clean-csv-data.html")
        for needle in ("Encoding", "Delimiter", "Structure", "Duplicates",
                       "Validate at the destination"):
            self.assertIn(needle, html, needle)


class SitemapTests(unittest.TestCase):
    def test_sitemap_lists_every_page(self):
        xml = page("sitemap.xml")
        for name in ALL_PAGES:
            self.assertIn(f"/tidycsv/{name}", xml, name)
        self.assertIn("/tidycsv/", xml)

    def test_sitemap_is_well_formed(self):
        import xml.etree.ElementTree as ET
        ET.fromstring(page("sitemap.xml"))

    def test_robots_points_to_sitemap(self):
        robots = page("robots.txt")
        self.assertIn("User-agent: *", robots)
        self.assertIn("Sitemap: https://uniquepratham.github.io/tidycsv/sitemap.xml",
                      robots)


class TrackingEventTests(unittest.TestCase):
    def test_event_names_are_allowlisted(self):
        src = page("zf-track.js")
        for event in EVENTS:
            self.assertRegex(src, rf"(?<![a-z_]){re.escape(event)}(?![a-z_])",
                             f"event not allowlisted: {event}")

    def test_functional_pages_emit_meaningful_events(self):
        html = page("clean-csv-online.html")
        for event in ("cta_click", "pricing_view"):
            self.assertIn(f'data-zf-event="{event}"', html, f"missing hook {event}")
        tool = page("seo-tool.js")
        for event in ("engaged", "cta_click", "pricing_view"):
            self.assertIn(f'data-zf-event="{event}"', tool,
                          f"widget missing hook {event}")


class NodeParityTests(unittest.TestCase):
    """Run the browser core under Node when available (skipped otherwise)."""

    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which("node")

    def test_node_parses_tidycsv_js(self):
        if not self.node:
            self.skipTest("node not available")
        proc = subprocess.run([self.node, "--check", str(ROOT / "tidycsv.js")],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_node_parses_seo_tool_js(self):
        if not self.node:
            self.skipTest("node not available")
        proc = subprocess.run([self.node, "--check", str(ROOT / "seo-tool.js")],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_node_parses_zf_track_js(self):
        if not self.node:
            self.skipTest("node not available")
        proc = subprocess.run([self.node, "--check", str(ROOT / "zf-track.js")],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_browser_core_matches_python_core(self):
        if not self.node:
            self.skipTest("node not available")
        import tidycsv
        script = f"""
        const fs = require('fs');
        const src = fs.readFileSync({str(ROOT / "tidycsv.js")!r}, 'utf8');
        const window = {{}};
        eval(src);
        const text = 'name,city\\nAlice ,London\\n\\nAlice ,London\\nbob,Paris\\n';
        const parsed = window.TidyCSV.parse(text);
        const headers = parsed.headers, rows = parsed.rows;
        const issues = window.TidyCSV.detect(headers, rows);
        const rules = [...new Set(issues.map(i => i.rule))].sort();
        console.log(JSON.stringify({{headers, rows, rules}}));
        """
        proc = subprocess.run([self.node, "-e", script],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        import json
        js = json.loads(proc.stdout)
        headers, rows = tidycsv.parse("name,city\nAlice ,London\n\nAlice ,London\nbob,Paris\n")
        issues = tidycsv.detect(headers, rows)
        py_rules = sorted({i.rule for i in issues})
        self.assertEqual(js["headers"], headers)
        self.assertEqual(js["rows"], rows)
        self.assertEqual(js["rules"], py_rules)


if __name__ == "__main__":
    unittest.main(verbosity=2)
