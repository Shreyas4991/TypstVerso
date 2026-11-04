"""Compile all sample document types and verify shared rendering and font sizes."""
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("document_build", ROOT / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class DocumentTemplates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = {}
        cls.builders = {}
        for kind in build.DOCUMENT_KINDS:
            builder = build.Builder(document=ROOT / "documents" / kind)
            builder.build()
            cls.builders[kind] = builder
            html = (builder.output / "main.html").read_text()
            match = re.search(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', html, re.S)
            cls.outputs[kind] = (html, json.loads(match.group(1)), PdfReader(builder.output / "main.pdf"))

    def test_samples_have_separate_outputs_and_equivalent_lean_content(self):
        for kind, (html, pages, pdf) in self.outputs.items():
            with self.subTest(kind=kind):
                builder = self.builders[kind]
                self.assertEqual(builder.output, ROOT / "documents" / kind / "build")
                self.assertEqual(builder.path, ROOT / "typst/lean.json")
                self.assertEqual(len(pdf.pages), len(pages))
                self.assertGreaterEqual(sum(len(p["regions"]) for p in pages), 53)
                text = "\n".join(page.extract_text() for page in pdf.pages)
                for fragment in ("hello", "identity_pair", "all_goals", "intro h", "exact h"):
                    self.assertIn(fragment, text)
                self.assertTrue(any(r["role"] == "state" and r["tooltip"] == "No goals"
                                    for p in pages for r in p["regions"]))
                self.assertNotRegex(html, r"__[A-Z_]+__")
                self.assertFalse(list(builder.document.rglob("*.json")))
                for page in pages:
                    for region in page["regions"]:
                        self.assertLessEqual(region["x"] + region["width"], page["width"] + 1)
                        self.assertLessEqual(region["y"] + region["height"], page["height"] + 1)

    def test_browser_layout_matches_document_type(self):
        self.assertIn('id="stage"', self.outputs["slides"][0])
        self.assertNotIn('id="pages"', self.outputs["slides"][0])
        for kind in ("article", "book"):
            self.assertIn('id="pages"', self.outputs[kind][0])
            self.assertNotIn('id="stage"', self.outputs[kind][0])
        self.assertIn('id="table-of-contents"', self.outputs["book"][0])
        self.assertNotIn('id="page-links"', self.outputs["book"][0])
        book = self.outputs["book"][2]
        self.assertGreaterEqual(len(book.pages), 4)
        self.assertIn("Contents", book.pages[1].extract_text())

    def test_contents_uses_numbered_headings_and_exact_section_positions(self):
        headings = [h for page in self.outputs["book"][1] for h in page["headings"]]
        self.assertEqual([h["title"] for h in headings[:6]], [
            "1 From definitions to proofs", "1.1 A first definition",
            "1.2 A proof with two branches", "2 Reading the proof interactively",
            "2.1 Intermediate goals", "2.2 Asking Lean questions"])
        self.assertEqual([h["level"] for h in headings[:6]], [1, 2, 2, 1, 2, 2])
        self.assertEqual(len({h["id"] for h in headings}), len(headings))
        self.assertEqual(headings[1]["page"], headings[2]["page"])
        self.assertLess(headings[1]["y"], headings[2]["y"])

    def test_contents_handles_styled_and_unnumbered_headings_and_empty_documents(self):
        with tempfile.TemporaryDirectory(prefix="contents-check-") as temporary:
            directory = Path(temporary)
            entry = directory / "main.typ"
            for source, expected in [
                ('#set heading(numbering: "1.1")\n= A *rich* #emph[chapter]\n'
                 '== Second section\n#heading(numbering: none)[Unnumbered]\n'
                 '#heading(outlined: false)[Hidden]\n',
                 ["1 A rich chapter", "1.1 Second section", "Unnumbered"]),
                ("A document without headings.", []),
            ]:
                entry.write_text(source)
                builder = build.Builder(document=directory, library=directory, kind="book", formats="html")
                builder.export(entry)
                html = (builder.output / "main.html").read_text()
                pages = json.loads(re.search(
                    r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', html, re.S).group(1))
                self.assertEqual([h["title"] for p in pages for h in p["headings"]], expected)

    def test_code_and_goal_tokens_inherit_each_document_font_size(self):
        widths = {}
        goal_widths = {}
        for kind, (_, pages, _) in self.outputs.items():
            tokens = [r for p in pages for r in p["regions"] if r["role"] == "token"]
            widths[kind] = next(r["width"] for r in tokens if "Demo.hello" in r["tooltip"])
            goal_widths[kind] = [r["width"] for r in tokens if r["tooltip"] == "Prop"]
            self.assertTrue(goal_widths[kind])
            # Single-letter p/q tokens in source, printed goals, and signatures
            # must all inherit the same size within a document.
            for width in goal_widths[kind]:
                self.assertAlmostEqual(width, goal_widths[kind][0])
        self.assertAlmostEqual(widths["slides"] / widths["article"], 20 / 11)
        self.assertAlmostEqual(widths["slides"] / widths["book"], 20 / 10)
        self.assertAlmostEqual(goal_widths["slides"][0] / goal_widths["article"][0], 20 / 11)
        self.assertAlmostEqual(goal_widths["slides"][0] / goal_widths["book"][0], 20 / 10)

    def test_watcher_includes_shared_renderer_and_html_templates(self):
        paths = {item[0] for item in build.watch_snapshot(build.PROJECT, build.DOCUMENT)}
        self.assertIn(str(ROOT / "typst/lean.typ"), paths)
        self.assertIn(str(ROOT / "templates/html/tooltips.js"), paths)
        self.assertIn(str(ROOT / "templates/html/book.html"), paths)
        self.assertNotIn(str(ROOT / "typst/lean.json"), paths)


if __name__ == "__main__":
    unittest.main()
