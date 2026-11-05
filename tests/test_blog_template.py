"""Compile dated posts to check ordering, indexes, and the blog's public API."""
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("blog_build", ROOT / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class BlogTemplate(unittest.TestCase):
    def make_builder(self, directory, source):
        directory = Path(directory)
        shutil.copyfile(ROOT / "typst/blog.typ", directory / "blog.typ")
        entry = directory / "main.typ"
        entry.write_text('#import "blog.typ": blog, blog-post, blog-date\n' + source)
        return build.Builder(document=directory, library=directory, kind="blog"), entry

    def test_dates_sort_posts_and_linked_index_across_years_with_stable_ties(self):
        posts = [
            ("December", (2025, 12, 1)),
            ("New year first", (2026, 1, 1)),
            ("Oldest", (2024, 12, 31)),
            ("New year second", (2026, 1, 1)),
            ("Year end", (2025, 12, 31)),
        ]
        source = '#blog((\n' + ',\n'.join(
            f'blog-post(title: [{title}], date: blog-date{date})[\n'
            f'Body of {title}.\n\n== A section inside {title}\nSection text.\n]'
            for title, date in posts) + '\n))'
        expected = ["New year first", "New year second", "Year end", "December", "Oldest"]
        with tempfile.TemporaryDirectory(prefix="blog-order-") as temporary:
            builder, entry = self.make_builder(temporary, source)
            builder.export(entry)
            html = (builder.output / "main.html").read_text()
            pages = json.loads(re.search(
                r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', html, re.S).group(1))
            headings = [h for p in pages for h in p["headings"] if h["level"] == 1]
            self.assertEqual([h["title"] for h in headings], expected)
            self.assertEqual(len({h["page"] for h in headings}), len(expected))
            self.assertNotIn('id="page-count"', html)
            self.assertNotRegex(html, r"__[A-Z_]+__")

            pdf = PdfReader(builder.output / "main.pdf")
            index = pdf.pages[0].extract_text()
            positions = [index.index(title) for title in expected]
            self.assertEqual(positions, sorted(positions))
            self.assertNotIn("A section inside", index)
            self.assertEqual(len(pdf.pages[0]["/Annots"]), len(expected))
            for heading in headings:
                text = pdf.pages[heading["page"] - 1].extract_text()
                self.assertIn(heading["title"], text)
                date = dict(posts)[heading["title"]]
                self.assertIn(build.run([
                    "typst", "eval",
                    f'datetime(year: {date[0]}, month: {date[1]}, day: {date[2]})'
                    '.display("[day] [month repr:long] [year]")',
                ], capture=True).strip('"\n'), text)
            for page in pdf.pages:
                self.assertNotRegex(page.extract_text(), r"(?m)^\d+$")

    def test_empty_blog_has_an_empty_index(self):
        with tempfile.TemporaryDirectory(prefix="blog-empty-") as temporary:
            builder, entry = self.make_builder(temporary, '#blog(())')
            builder.export(entry)
            pdf = PdfReader(builder.output / "main.pdf")
            self.assertEqual(len(pdf.pages), 1)
            self.assertIn("Posts", pdf.pages[0].extract_text())

    def test_each_post_requires_a_title_and_date(self):
        for source, message in [
            ('#blog((blog-post(title: [Undated])[Text],))', "Set each post's date"),
            ('#blog((blog-post(date: blog-date(2026, 11, 5))[Text],))', "Each blog post needs a title"),
        ]:
            with self.subTest(message=message), tempfile.TemporaryDirectory(prefix="blog-invalid-") as temporary:
                builder, entry = self.make_builder(temporary, source)
                with self.assertRaisesRegex(build.TypstFailure, message):
                    builder.export(entry)


if __name__ == "__main__":
    unittest.main()
