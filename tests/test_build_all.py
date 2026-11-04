"""Check the all-document build and watch commands without running Lean."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("all_documents_build", ROOT / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class BuildAll(unittest.TestCase):
    def test_all_builds_each_document_and_refreshes_the_shared_cache_once(self):
        with patch.object(build, "watch_snapshot", return_value=[]), \
                patch.object(build, "Builder") as constructor:
            self.assertEqual(build.main(["--all", "--refresh"]), 0)
            self.assertEqual([call.args[1].name for call in constructor.call_args_list],
                             ["slides", "article", "book"])
            self.assertEqual([call.args[4] for call in constructor.call_args_list], [True, False, False])
            self.assertTrue(all(call.args[2] is None for call in constructor.call_args_list))
            self.assertEqual(constructor.return_value.build.call_count, 3)

    def test_output_override_keeps_documents_in_separate_folders(self):
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(build, "watch_snapshot", return_value=[]), \
                patch.object(build, "Builder") as constructor:
            self.assertEqual(build.main(["--all", "--output", temporary]), 0)
            self.assertEqual([call.args[2] for call in constructor.call_args_list],
                             [Path(temporary) / kind for kind in build.DOCUMENT_KINDS])

    def test_one_failed_document_does_not_stop_the_others(self):
        with patch.object(build, "watch_snapshot", return_value=[]), \
                patch.object(build, "Builder") as constructor:
            constructor.return_value.build.side_effect = [RuntimeError("bad slides"), None, None]
            self.assertEqual(build.main(["--all"]), 1)
            self.assertEqual(constructor.return_value.build.call_count, 3)

    def test_watch_rebuilds_all_after_a_change_and_skips_unchanged_inputs(self):
        with patch.object(build, "watch_snapshot", side_effect=[[1], [1], [2], [2]]) as snapshot, \
                patch.object(build, "Builder") as constructor, \
                patch.object(build.time, "sleep", side_effect=[None, None, None, KeyboardInterrupt]):
            with self.assertRaises(KeyboardInterrupt):
                build.main(["--all", "--watch"])
            self.assertEqual(constructor.return_value.build.call_count, 6)
            self.assertEqual([call.args[1].name for call in constructor.call_args_list],
                             ["slides", "article", "book"] * 2)
            self.assertEqual(snapshot.call_args.args[1],
                             [ROOT / "documents" / kind for kind in build.DOCUMENT_KINDS])

    def test_watch_snapshot_includes_all_document_sources_and_excludes_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "LeanProject"
            project.mkdir()
            documents = [root / name for name in ("slides", "book")]
            for document in documents:
                document.mkdir()
                (document / "main.typ").write_text("First version.")
                (document / "build").mkdir()
                (document / "build/main.html").write_text("Generated output.")
            before = build.watch_snapshot(project, documents, root / "typst", root / "templates")
            paths = {item[0] for item in before}
            self.assertTrue(all(str(d / "main.typ") in paths for d in documents))
            self.assertTrue(all(str(d / "build/main.html") not in paths for d in documents))
            (documents[1] / "main.typ").write_text("An updated version of the book.")
            self.assertNotEqual(before, build.watch_snapshot(
                project, documents, root / "typst", root / "templates"))


if __name__ == "__main__":
    unittest.main()
