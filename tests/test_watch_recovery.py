# Copyright 2026 Shreyas Srinivas
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Use a real watcher to cover module visibility and the reported SimpleGraph case."""
import json
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SOURCE = '''module
public import Init
@[expose] public section
namespace Demo
def value : Nat := 1
end Demo
'''
DOCUMENT = '''#import "../typst/lean.typ": lean-quote, lean-command
#set text(size: 9pt)
#lean-quote("Demo.value")
#lean-command("SimpleGraph", module: "Mathlib.Combinatorics.SimpleGraph.Basic")
#lean-command("#eval (2 + 2)")
'''


class WatchRecovery(unittest.TestCase):
    def test_command_errors_and_private_definitions_do_not_stop_the_watcher(self):
        self.assertIn("@[expose] public section", (ROOT / "LeanProject/LeanProject/Basic.lean").read_text())
        with tempfile.TemporaryDirectory(prefix="watch-recovery-") as temporary:
            base = Path(temporary)
            project, document, library = (base / name for name in ("LeanProject", "document", "typst"))
            (project / "LeanProject").mkdir(parents=True)
            (project / ".lake").mkdir()
            (project / ".lake/packages").symlink_to(ROOT / "LeanProject/.lake/packages", target_is_directory=True)
            for name in ("lakefile.toml", "lake-manifest.json", "lean-toolchain", "subverso.patch", "ExportLean.lean"):
                shutil.copyfile(ROOT / "LeanProject" / name, project / name)
            (project / "LeanProject.lean").write_text("import LeanProject.Basic\n")
            source = project / "LeanProject/Basic.lean"
            source.write_text(PUBLIC_SOURCE)
            document.mkdir()
            library.mkdir()
            shutil.copyfile(ROOT / "typst/lean.typ", library / "lean.typ")
            entry = document / "main.typ"
            entry.write_text(DOCUMENT)
            output = document / "build/main.html"
            log_path = base / "watch.log"
            with log_path.open("w") as log:
                process = subprocess.Popen([
                    sys.executable, "-u", str(ROOT / "build.py"), "--watch", "--format", "html",
                    "--project", str(project), "--document", str(document), "--library", str(library),
                    "--template", "book"], stdout=log, stderr=subprocess.STDOUT)

                def wait_for(condition):
                    deadline = time.monotonic() + 60
                    while time.monotonic() < deadline:
                        if condition():
                            return
                        if process.poll() is not None:
                            self.fail("Watcher exited:\n" + log_path.read_text())
                        time.sleep(0.1)
                    self.fail("Watcher did not recover:\n" + log_path.read_text())

                def data():
                    return json.loads((library / "lean.json").read_text())

                try:
                    wait_for(output.is_file)
                    commands = {c["source"]: c for c in data()["inlineCommands"]}
                    self.assertTrue(any(m["severity"] == "error" for m in commands["SimpleGraph"]["messages"]))
                    self.assertEqual(commands["#eval (2 + 2)"]["messages"][0]["text"], "4")
                    self.assertIsNone(process.poll())

                    # Correct the command while the same Python process is running.
                    before = output.stat().st_mtime_ns
                    entry.write_text(DOCUMENT.replace('"SimpleGraph"', '"#print SimpleGraph"'))
                    wait_for(lambda: output.stat().st_mtime_ns > before)
                    printed = next(c for c in data()["inlineCommands"] if c["source"] == "#print SimpleGraph")
                    self.assertTrue(all(m["severity"] == "info" for m in printed["messages"]))
                    self.assertIn("structure SimpleGraph", printed["messages"][0]["text"])

                    # Reproduce the visibility failure, preserving the good document.
                    good_output = output.read_bytes()
                    before_log = len(log_path.read_text())
                    source.write_text(PUBLIC_SOURCE.replace("@[expose] public section\n", ""))
                    wait_for(lambda: "add '@[expose] public section'" in log_path.read_text()[before_log:])
                    self.assertIsNone(process.poll())
                    self.assertEqual(output.read_bytes(), good_output)

                    # Restore public visibility and verify new source reaches the document.
                    before = output.stat().st_mtime_ns
                    source.write_text(PUBLIC_SOURCE.replace(":= 1", ":= 2"))
                    wait_for(lambda: output.stat().st_mtime_ns > before)
                    self.assertIn(":= 2", data()["declarations"]["Demo.value"]["source"])
                    self.assertIsNone(process.poll())
                finally:
                    process.send_signal(signal.SIGINT)
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()


if __name__ == "__main__":
    unittest.main()
