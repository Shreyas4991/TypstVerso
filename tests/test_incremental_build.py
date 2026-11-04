"""Exercise discovery, incremental extraction, and recovery with actual Typst/Lean."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("template_build", ROOT / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

HEADER = '#import "lean.typ": lean-quote, lean-state, lean-command\n#set text(size: 10pt)\n'


class IncrementalBuild(unittest.TestCase):
    def test_changed_lean_source_replaces_cached_results(self):
        with tempfile.TemporaryDirectory(prefix="SourceRefresh_", dir=build.PROJECT / "LeanProject") as source_dir, \
                tempfile.TemporaryDirectory(prefix="typst-source-refresh-") as temporary:
            source = Path(source_dir) / "Example.lean"
            module = "LeanProject." + Path(source_dir).name + ".Example"
            base = Path(temporary)
            document = base / "document"
            document.mkdir()
            for name in ("lean.typ",):
                shutil.copyfile(ROOT / "typst" / name, document / name)
            (document / "main.typ").write_text(HEADER + '#lean-quote("sourceRefreshValue")\n')
            for value in (1, 2):
                source.write_text(f"def sourceRefreshValue : Nat := {value}\n")
                b = build.Builder(document=document, library=document, output=base / "build", modules=[module], formats="html")
                b.build()
                self.assertIn(f":= {value}", b.data["declarations"]["sourceRefreshValue"]["source"])

    def test_cold_warm_new_requests_recovery_and_errors(self):
        with tempfile.TemporaryDirectory(prefix="typst-lean-build-") as temporary:
            base = Path(temporary)
            document = base / "document"
            document.mkdir()
            for name in ("lean.typ",):
                shutil.copyfile(ROOT / "typst" / name, document / name)
            entry = document / "main.typ"
            output = base / "build"

            def builder():
                return build.Builder(document=document, library=document, output=output, formats="html")

            # Evaluate real imports, computed names and loops, not source text matches.
            (document / "part.typ").write_text(
                HEADER + '#let prefix = "Demo."\n#for suffix in ("hello",) { lean-quote(prefix + suffix) }\n'
                '// #lean-quote("DoesNotExist")\n```typst\n#lean-quote("AlsoNotReal")\n```\n')
            entry.write_text('#include "part.typ"\n')
            b = builder()
            b.build()
            self.assertEqual(set(b.data["declarations"]), {"Demo.hello"})
            self.assertEqual(list(document.glob("*.json")), [document / "lean.json"])
            self.assertTrue((output / "main.html").is_file())
            self.assertFalse(list(output.glob("*.json")))

            # A wording change and a separate Python process both reuse extraction.
            cache_time = (document / "lean.json").stat().st_mtime_ns
            entry.write_text(entry.read_text() + '\nUpdated prose.\n')
            with patch.object(build.Builder, "prepare", side_effect=AssertionError("Lean reran")):
                builder().build()
            self.assertEqual((document / "lean.json").stat().st_mtime_ns, cache_time)
            result = subprocess.run([
                "python3", str(ROOT / "build.py"), "--document", str(document),
                "--output", str(output), "--library", str(document), "--format", "html"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("Extracting", result.stdout)
            self.assertNotIn("Evaluating", result.stdout)

            # Quote and state share one entry; commands have independent cached results.
            entry.write_text(HEADER + '#include "part.typ"\n'
                             '#let name = "Demo." + "identity_pair"\n'
                             '#lean-quote(name)\n#lean-state(name, index: 2)\n'
                             '#lean-command("#eval (2 + 2)")\n')
            b = builder()
            with patch.object(b, "extract_declarations", wraps=b.extract_declarations) as extract:
                b.build()
            extract.assert_called_once_with(["Demo.identity_pair"])
            self.assertEqual(set(b.data["declarations"]), {"Demo.hello", "Demo.identity_pair"})
            self.assertEqual(b.data["inlineCommands"][0]["messages"][0]["text"], "4")

            # Deliberately hide a call during discovery to exercise real error/retry recovery.
            entry.write_text(HEADER + '#lean-quote("Demo.hello")\n'
                             '#if sys.inputs.at("lean-discover", default: "false") != "true" {\n'
                             '  lean-quote("Eq", size: 8pt)\n}\n')
            b = builder()
            with patch.object(b, "extract_declarations", wraps=b.extract_declarations) as extract:
                b.build()
            extract.assert_called_once_with(["Eq"])
            self.assertIn("Eq", b.data["declarations"])

            # Unrelated Typst errors must neither run Lean nor replace a good export.
            before = (output / "main.html").read_bytes()
            entry.write_text(HEADER + '#unknown_function()\n')
            with patch.object(build.Builder, "prepare", side_effect=AssertionError("Lean reran")):
                with self.assertRaises(build.TypstFailure):
                    builder().build()
            self.assertEqual((output / "main.html").read_bytes(), before)

            # An unresolvable Lean declaration fails once and preserves output and cache.
            before_cache = (document / "lean.json").read_bytes()
            entry.write_text(HEADER + '#lean-quote("NoSuchDeclarationAnywhere")\n')
            with self.assertRaises(subprocess.CalledProcessError):
                builder().build()
            self.assertEqual((output / "main.html").read_bytes(), before)
            self.assertEqual((document / "lean.json").read_bytes(), before_cache)

            # Source changes invalidate saved results, even if document text is unchanged.
            with tempfile.TemporaryDirectory(prefix="CacheInvalidation_", dir=build.PROJECT) as source_dir:
                (Path(source_dir) / "Changed.lean").write_text("def cacheInvalidationExample := 1\n")
                self.assertEqual(builder().data["declarations"], {})

            # A missing/corrupt cache can be regenerated by the discovery pass.
            entry.write_text(HEADER + '#lean-quote("Demo.hello")\n')
            (document / "lean.json").write_text("not valid JSON")
            builder().build()
            self.assertEqual(set(json.loads((document / "lean.json").read_text())["declarations"]),
                             {"Demo.hello"})


class RecoveryControl(unittest.TestCase):
    def test_changes_during_extraction_cannot_mark_stale_data_fresh(self):
        with tempfile.TemporaryDirectory() as temporary:
            b = build.Builder(document=Path(temporary), library=Path(temporary), formats="html")
            with patch.object(b, "lean_fingerprint", return_value="changed-during-extraction"):
                with self.assertRaisesRegex(RuntimeError, "changed during extraction"):
                    b.save()
            self.assertFalse(b.path.exists())

    def test_diagnostics_only_recover_explicit_missing_data(self):
        request = {"kind": "command", "source": '#eval "a\\nb"', "module": None}
        result = subprocess.CompletedProcess([], 1, stderr=(
            "main.typ:3:2: error: panicked with: LEAN_REQUEST:" + json.dumps(request)))
        self.assertEqual(build.TypstFailure(result).missing_request(), request)
        result.stderr = 'main.typ:3:2: error: unknown variable\nhelp: LEAN_REQUEST:{}'
        self.assertIsNone(build.TypstFailure(result).missing_request())

    def test_retry_stops_if_extraction_cannot_make_progress(self):
        with tempfile.TemporaryDirectory() as temporary:
            document = Path(temporary)
            (document / "main.typ").write_text("Hello")
            b = build.Builder(document=document, library=document, output=document / "build", formats="html")
            error = build.TypstFailure(subprocess.CompletedProcess([], 1, stderr=
                'main.typ:1:1: error: panicked with: LEAN_REQUEST:{"kind":"declaration","name":"Eq"}'))
            with patch.object(b, "discover", return_value=[]), \
                    patch.object(b, "ensure_requests", return_value=False), \
                    patch.object(b, "export", side_effect=error) as export:
                with self.assertRaisesRegex(RuntimeError, "no extraction progress"):
                    b.build()
            self.assertEqual(export.call_count, 1)

    def test_watch_retries_after_an_error_when_the_input_changes(self):
        error = build.TypstFailure(subprocess.CompletedProcess([], 1, stderr="error: syntax"))
        with patch.object(build, "watch_snapshot", side_effect=[[1], [2], [2]]), \
                patch.object(build, "Builder") as constructor, \
                patch.object(build.time, "sleep", side_effect=[None, None, KeyboardInterrupt]):
            constructor.return_value.build.side_effect = [error, None]
            with self.assertRaises(KeyboardInterrupt):
                build.main(["--watch", "--format", "html"])
            self.assertEqual(constructor.return_value.build.call_count, 2)


if __name__ == "__main__":
    unittest.main()
