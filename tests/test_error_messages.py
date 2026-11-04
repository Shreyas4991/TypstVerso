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

"""Check readable Typst errors and automatic recovery without JSON diagnostics."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("error_message_build", ROOT / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class ErrorMessages(unittest.TestCase):
    def test_missing_results_explain_the_cause_and_fixes_without_a_json_dump(self):
        command = '#eval do\n  IO.println "quoted \\value β"'
        requests = [
            ('lean-quote("Demo.pending")', {"kind": "declaration", "name": "Demo.pending"}),
            ('lean-state("Demo.pending")', {"kind": "declaration", "name": "Demo.pending"}),
            ('lean-command("#check SimpleGraph")',
             {"kind": "command", "source": "#check SimpleGraph", "module": None}),
            ('lean-command(' + json.dumps(command, ensure_ascii=False) + ', module: "Init")',
             {"kind": "command", "source": command, "module": "Init"}),
            ('lean-command(' + json.dumps('#eval "Error: The Lean definition or proof is missing"') + ')',
             {"kind": "command", "source": '#eval "Error: The Lean definition or proof is missing"', "module": None}),
        ]
        with tempfile.TemporaryDirectory(prefix="readable-errors-") as temporary:
            directory = Path(temporary)
            shutil.copyfile(ROOT / "typst/lean.typ", directory / "lean.typ")
            build.write_json(directory / "lean.json", {
                "schemaVersion": 1, "declarations": {}, "commands": [], "inlineCommands": []})
            builder = build.Builder(document=directory, library=directory, formats="html")
            entry = directory / "main.typ"
            for call, request in requests:
                with self.subTest(call=call):
                    entry.write_text('#import "lean.typ": *\n#' + call)
                    with self.assertRaises(build.TypstFailure) as caught:
                        builder.typst(["compile", entry, directory / "main.pdf"])
                    diagnostic = str(caught.exception)
                    for text in ("Error:", "Probable cause:", "Probable fix:", "wait about a minute",
                                 "save this Typst file again", "Check its terminal for errors",
                                 ".venv/bin/python build.py --watch --all", ".venv/bin/python build.py --all"):
                        self.assertIn(text, diagnostic)
                    self.assertNotIn("panicked", diagnostic)
                    self.assertNotIn("LEAN_REQUEST:", diagnostic)
                    self.assertNotIn('{"kind":', diagnostic)
                    self.assertEqual(caught.exception.missing_request(), request)

    def test_outdated_results_explain_how_to_refresh_them(self):
        with tempfile.TemporaryDirectory(prefix="outdated-errors-") as temporary:
            directory = Path(temporary)
            shutil.copyfile(ROOT / "typst/lean.typ", directory / "lean.typ")
            build.write_json(directory / "lean.json", {"schemaVersion": 0, "declarations": {}})
            entry = directory / "main.typ"
            entry.write_text('#import "lean.typ": lean-quote\n#lean-quote("Demo.pending")')
            builder = build.Builder(document=directory, library=directory, formats="html")
            with self.assertRaises(build.TypstFailure) as caught:
                builder.typst(["compile", entry, directory / "main.pdf"])
            self.assertIn("Error: The saved Lean results need to be updated.", str(caught.exception))
            self.assertIn("Probable cause:", str(caught.exception))
            self.assertIn("Probable fix:", str(caught.exception))
            self.assertIn("build.py --all --refresh", str(caught.exception))
            self.assertIsNone(caught.exception.missing_request())

    def test_builder_recovers_from_the_new_messages_for_names_and_commands(self):
        with tempfile.TemporaryDirectory(prefix="readable-recovery-") as temporary:
            directory = Path(temporary)
            shutil.copyfile(ROOT / "typst/lean.typ", directory / "lean.typ")
            (directory / "main.typ").write_text('''#import "lean.typ": lean-quote, lean-command
#if sys.inputs.at("lean-discover", default: "false") != "true" {
  lean-quote("Eq")
  lean-command("#eval (2 + 2)")
}
''')
            builder = build.Builder(document=directory, library=directory, formats="html")
            log = io.StringIO()
            with contextlib.redirect_stdout(log):
                builder.build()
            self.assertIn("Preparing the missing result for", log.getvalue())
            self.assertNotIn('{"kind":', log.getvalue())
            self.assertIn("Eq", builder.data["declarations"])
            self.assertEqual(builder.data["inlineCommands"][0]["messages"][0]["text"], "4")
            self.assertTrue((directory / "build/main.html").is_file())


if __name__ == "__main__":
    unittest.main()
