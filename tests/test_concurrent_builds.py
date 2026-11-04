"""Two independently started builders must preserve each other's extracted data."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("concurrent_build", ROOT / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

WORKER = '''
from pathlib import Path
import sys, time
sys.path.insert(0, sys.argv[1])
import build
root, name = Path(sys.argv[2]), sys.argv[3]
class Worker(build.Builder):
    def discover(self, entry):
        return [{"kind": "declaration", "name": name}]
    def extract_declarations(self, names):
        with (root / "events").open("a") as log:
            log.write("start " + name + "\\n")
        time.sleep(0.2)
        for declaration in names:
            self.data["declarations"][declaration] = {"source": declaration}
        with (root / "events").open("a") as log:
            log.write("end " + name + "\\n")
    def export(self, entry):
        pass
builder = Worker(project=root / "project", document=root / "document", library=root / "typst")
(root / ("ready-" + name)).touch()
while not (root / "start").exists():
    time.sleep(0.01)
builder.build()
'''


class ConcurrentBuilds(unittest.TestCase):
    def test_two_builders_starting_with_empty_data_preserve_both_results(self):
        with tempfile.TemporaryDirectory(prefix="concurrent-build-") as temporary:
            root = Path(temporary)
            (root / "project").mkdir()
            (root / "document").mkdir()
            (root / "document/main.typ").write_text("Example")
            worker = root / "worker.py"
            worker.write_text(WORKER)
            processes = [subprocess.Popen([sys.executable, str(worker), str(ROOT), str(root), name],
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                         for name in ("first", "second")]
            try:
                deadline = time.monotonic() + 10
                while not all((root / ("ready-" + name)).exists() for name in ("first", "second")):
                    if time.monotonic() > deadline:
                        self.fail("Workers did not become ready")
                    time.sleep(0.01)
                (root / "start").touch()
                for process in processes:
                    stdout, stderr = process.communicate(timeout=10)
                    self.assertEqual(process.returncode, 0, stdout + stderr)
                data = json.loads((root / "typst/lean.json").read_text())
                self.assertEqual(set(data["declarations"]), {"first", "second"})
                events = (root / "events").read_text().splitlines()
                self.assertEqual([line.split()[0] for line in events], ["start", "end", "start", "end"])
                self.assertEqual(events[0].split()[1], events[1].split()[1])
                self.assertFalse(list((root / "typst").glob("*.tmp")))
            finally:
                for process in processes:
                    if process.poll() is None:
                        process.kill()
                        process.communicate()

    def test_lock_is_released_after_a_failed_build(self):
        with tempfile.TemporaryDirectory() as temporary:
            library = Path(temporary)
            with self.assertRaisesRegex(RuntimeError, "failed"):
                with build.build_lock(library):
                    raise RuntimeError("failed")
            with build.build_lock(library):
                build.write_json(library / "lean.json", {"recovered": True})
            self.assertTrue(json.loads((library / "lean.json").read_text())["recovered"])

    def test_captured_process_errors_keep_the_real_diagnostic(self):
        with self.assertRaises(subprocess.CalledProcessError) as error:
            build.run([sys.executable, "-c", 'import sys; sys.stderr.write("A useful Lean error"); sys.exit(1)'],
                      cwd=ROOT, capture=True)
        self.assertIn("A useful Lean error", str(error.exception))

    def test_watch_ignores_lock_data_and_temporary_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project, document, library = (root / name for name in ("project", "document", "typst"))
            for directory in (project, document, library):
                directory.mkdir()
            (document / "main.typ").write_text("Example")
            (library / "lean.typ").write_text("// Renderer")
            before = build.watch_snapshot(project, document, library, root / "templates")
            for name in (".build.lock", "lean.json", ".lean-in-progress.tmp"):
                (library / name).write_text("data")
            self.assertEqual(before, build.watch_snapshot(project, document, library, root / "templates"))


if __name__ == "__main__":
    unittest.main()
