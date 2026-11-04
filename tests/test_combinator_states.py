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

"""Integration checks for repeated tactic states; uses temporary Lean source modules."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "typst"
spec = importlib.util.spec_from_file_location("slide_build", ROOT / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

SOURCE = """import Init
namespace SlideStateRegression

theorem branches (p q : Prop) :
    (p → p) ∧ (q → q) := by
  constructor
  all_goals
    intro h
    exact h

theorem sequential (p q : Prop) : (p → p) ∧ (q → q) := by
  constructor
  · intro h
    exact h
  · intro h
    exact h

theorem nested (p q : Prop) : ((p → p) ∧ (q → q)) ∧ ((p → p) ∧ (q → q)) := by
  constructor
  all_goals
    constructor
    all_goals
      intro h
      exact h

theorem semicolon (p q : Prop) : (p → p) ∧ (q → q) := by
  constructor <;> intro h <;> exact h

theorem mixed (p : Prop) : (p → p) ∧ True := by
  constructor
  all_goals
    try exact True.intro
  intro h
  exact h

def inferredType (x : Nat) := x + 1

theorem integerCast (n : Nat) : (n : Int) = n := rfl

end SlideStateRegression

-- These commands deliberately include a repeated command and repeated console output.
#check SlideStateRegression.inferredType
#check SlideStateRegression.inferredType
#print SlideStateRegression.inferredType
#eval (2 + 2)
#eval do
  IO.println "same"
  IO.println "same"
"""


class CombinatorStates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build.BUILD.mkdir(exist_ok=True)
        build.prepare_subverso()
        with tempfile.TemporaryDirectory(prefix="SlideStateCheck_", dir=build.PROJECT / "LeanProject") as source_dir, \
                tempfile.TemporaryDirectory(prefix="state-check-", dir=build.BUILD) as output_dir:
            directory = Path(source_dir)
            (directory / "Cases.lean").write_text(SOURCE)
            module = "LeanProject." + directory.name + ".Cases"
            build.run(["lake", "build", "subverso-extract-mod", "+SubVerso.Signature", "+" + module], cwd=build.PROJECT)
            raw = Path(output_dir) / (module + ".subverso.json")
            decoded = Path(output_dir) / "decoded.json"
            build.run(["lake", "exe", "subverso-extract-mod", module, raw], cwd=build.PROJECT)
            build.run(["lake", "env", "lean", "--run", "ExportLean.lean", raw, decoded], cwd=build.PROJECT)
            data = json.loads(decoded.read_text())
            cls.declarations = data["declarations"]
            cls.commands = data["commands"]

    def states(self, name, span=None):
        declaration = self.declarations["SlideStateRegression." + name]
        states = [p for p in declaration["fragments"] if p["kind"] == "state"]
        if span is not None:
            source = SOURCE.encode()
            states = [p for p in states if source[p["startByte"]:p["endByte"]].decode() == span]
        return states

    def test_all_goals_header_and_all_branches(self):
        header, = self.states("branches", "all_goals")
        intro, = self.states("branches", "intro h")
        exact, = self.states("branches", "exact h")
        for state in (header, intro):
            self.assertEqual(state["tooltip"].count("⊢"), 2)
            self.assertLess(state["tooltip"].index("case left"), state["tooltip"].index("case right"))
        self.assertIn("h : p", intro["tooltip"])
        self.assertIn("h : q", intro["tooltip"])
        self.assertEqual(exact["tooltip"], "No goals")

    def test_source_line_breaks_survive_quotes_and_type_views(self):
        declaration = self.declarations["SlideStateRegression.branches"]
        source = "".join(p["text"] for p in declaration["fragments"])
        self.assertIn("(p q : Prop) :\n    (p → p) ∧ (q → q) := by", source)
        signature = "".join(p["text"] for p in declaration["signatureFragments"])
        self.assertIn("(p q : Prop) :\n    (p → p) ∧ (q → q)", signature)

    def test_inferred_result_types_remain_available(self):
        declaration = self.declarations["SlideStateRegression.inferredType"]
        signature = "".join(p["text"] for p in declaration["signatureFragments"])
        self.assertIn("(x : Nat) : Nat", signature)

    def test_explicit_cast_types_survive_signature_extraction(self):
        declaration = self.declarations["SlideStateRegression.integerCast"]
        signature = "".join(p["text"] for p in declaration["signatureFragments"])
        self.assertIn("(n : Int) = n", signature)

    def test_commands_retain_source_order_and_actual_outputs(self):
        self.assertEqual([c["source"] for c in self.commands[:4]], [
            "#check SlideStateRegression.inferredType",
            "#check SlideStateRegression.inferredType",
            "#print SlideStateRegression.inferredType",
            "#eval (2 + 2)",
        ])
        self.assertEqual(self.commands[0]["messages"][0]["text"],
                         "SlideStateRegression.inferredType (x : Nat) : Nat")
        self.assertIn("x + 1", self.commands[2]["messages"][0]["text"])
        self.assertEqual(self.commands[3]["messages"][0]["text"], "4")
        console = "".join(message["text"] for message in self.commands[4]["messages"])
        self.assertEqual(console.count("same"), 2)

    def test_command_output_retains_semantic_tokens(self):
        message = self.commands[0]["messages"][0]
        self.assertEqual("".join(p["text"] for p in message["fragments"]), message["text"])
        self.assertTrue(any(p["tooltip"] and p["kind"].startswith("const") for p in message["fragments"]))

    def test_imported_names_resolve_to_their_defining_modules(self):
        with tempfile.TemporaryDirectory(prefix="resolve-check-", dir=build.BUILD) as temporary:
            request = Path(temporary) / "request.json"
            result = Path(temporary) / "result.json"
            build.write_json(request, {"modules": ["Lean"], "declarations": ["Lean.Expr", "Nat"]})
            resolved = json.loads(build.run(
                ["lake", "env", "lean", "--run", "ExportLean.lean", "--resolve"],
                cwd=build.PROJECT, capture=True, input=request.read_text()))
            self.assertEqual(resolved["Lean.Expr"], "Lean.Expr")
            self.assertTrue(resolved["Nat"].startswith("Init."))


    def test_prelude_quotes_keep_original_source_and_semantic_hovers(self):
        sysroot = build.run(["lake", "env", "lean", "--print-prefix"],
                            cwd=build.PROJECT, capture=True).strip()
        env = {**os.environ, "LEAN_SYSROOT": sysroot}
        with tempfile.TemporaryDirectory(prefix="prelude-check-", dir=build.BUILD) as temporary:
            raw = Path(temporary) / "Init.Prelude.subverso.json"
            decoded = Path(temporary) / "decoded.json"
            build.run(["lake", "exe", "subverso-extract-mod", "--declaration", "Eq",
                       "--declaration", "Nat", "Init.Prelude", raw], cwd=build.PROJECT, env=env)
            build.run(["lake", "env", "lean", "--run", "ExportLean.lean", raw, decoded,
                       "Eq", "Nat"], cwd=build.PROJECT, env=env)
            declarations = json.loads(decoded.read_text())["declarations"]
        self.assertEqual(set(declarations), {"Eq", "Nat"})
        eq = declarations["Eq"]
        lines = ["".join(p["text"] for p in line) for line in build.quote_lines(eq["fragments"])]
        self.assertEqual(lines[0], "inductive Eq : α → α → Prop where")
        self.assertEqual(lines[-1].strip(), "| refl (a : α) : Eq a a")
        self.assertFalse(any("inductive Nat" in line for line in lines))
        name, = [p for p in eq["fragments"] if p.get("definitionName") == "Eq"]
        self.assertIn("The equality relation", name["tooltip"])
        constructor, = [p for p in eq["fragments"] if p.get("definitionName") == "Eq.refl"]
        self.assertIn("reflexivity", constructor["tooltip"])
        self.assertTrue(eq["signatureFragments"])


    def test_nested_all_goals_keeps_four_invocations(self):
        headers = self.states("nested", "all_goals")
        self.assertEqual([s["tooltip"].count("⊢") for s in headers], [2, 4])
        intro, = self.states("nested", "intro h")
        self.assertEqual(intro["tooltip"].count("⊢"), 4)
        self.assertEqual(self.states("nested", "exact h")[0]["tooltip"], "No goals")

    def test_semicolon_keeps_both_invocations(self):
        intro, = self.states("semicolon", "intro h")
        self.assertEqual(intro["tooltip"].count("⊢"), 2)
        self.assertEqual(self.states("semicolon", "exact h")[0]["tooltip"], "No goals")

    def test_sequential_proof_keeps_individual_states(self):
        intros = self.states("sequential", "intro h")
        self.assertEqual(len(intros), 2)
        self.assertEqual([s["tooltip"].count("⊢") for s in intros], [1, 1])
        self.assertEqual(len(self.states("sequential")), 8)

    def test_a_closed_branch_does_not_hide_remaining_goals(self):
        exact, = self.states("mixed", "exact True.intro")
        self.assertEqual(exact["tooltip"].count("⊢"), 1)
        self.assertIn("p → p", exact["tooltip"])

    def test_highlighted_goal_fragments_match_popup_text(self):
        for name in ("branches", "nested", "sequential", "semicolon", "mixed"):
            for state in self.states(name):
                self.assertEqual("".join(p["text"] for p in state["fragments"]), state["tooltip"])

    def test_patch_applies_to_a_clean_copy_and_is_idempotent(self):
        relative = "src/SubVerso/Highlighting/Code.lean"
        package = build.PROJECT / ".lake/packages/subverso"
        clean = {}
        for name in (relative, "ExtractModule.lean"):
            clean[name] = subprocess.run(["git", "show", "HEAD:" + name], cwd=package,
                                         capture_output=True, text=True, check=True).stdout
        original_project = build.PROJECT
        try:
            with tempfile.TemporaryDirectory(prefix="subverso-patch-check-") as temporary:
                build.PROJECT = Path(temporary)
                target = build.PROJECT / ".lake/packages/subverso" / relative
                for name, content in clean.items():
                    destination = build.PROJECT / ".lake/packages/subverso" / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_text(content)
                (build.PROJECT / "subverso.patch").write_bytes((original_project / "subverso.patch").read_bytes())
                build.prepare_subverso()
                patched = target.read_bytes()
                self.assertNotEqual(patched, clean[relative].encode())
                build.prepare_subverso()
                self.assertEqual(target.read_bytes(), patched)
        finally:
            build.PROJECT = original_project


class InlineCommands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sources = [
            "#check Eq", "#check Eq.subst", "#check congrArg", "#check congrFun",
            "#check Eq.rec", "#check Nat.rec", "#check List.map", "#check Lean.Expr",
            "#check @Eq.subst", "#check Eq.{1}", "#check (fun x : Nat => x + 1)",
            "#print Eq", "#print Eq.rec", "#eval (2 + 2)",
            '#eval do\n  IO.println "https://example.com"\n  IO.println "/* literal */"',
            "#check Eq.congrArg", "#check DoesNotExist", "#check fun", "#check Nat",
            "def slideTemporary : Nat := 1\n#check slideTemporary", "#check slideTemporary",
        ]
        request_commands = [{"source": source, "module": None} for source in sources]
        request_commands += [{"source": "#check Lean.Expr", "module": "Init"},
                             {"source": "#check Nat.succ", "module": "Init"}]
        with tempfile.TemporaryDirectory(prefix="inline-check-", dir=build.BUILD) as temporary:
            request = Path(temporary) / "request.json"
            result = Path(temporary) / "result.json"
            build.write_json(request, {"modules": ["Lean"], "commands": request_commands})
            build.run(["lake", "env", "lean", "--run", "ExportLean.lean", "--commands",
                       request, result], cwd=build.PROJECT)
            cls.commands = json.loads(result.read_text())
        cls.by_request = {(c["source"], c["module"]): c for c in cls.commands}

    def messages(self, source, module=None):
        return self.by_request[(source, module)]["messages"]

    def test_valid_names_generated_declarations_and_expressions(self):
        for source in ["#check Eq", "#check Eq.subst", "#check congrArg", "#check congrFun",
                       "#check Eq.rec", "#check Nat.rec", "#check List.map", "#check Lean.Expr",
                       "#check @Eq.subst", "#check Eq.{1}", "#check (fun x : Nat => x + 1)",
                       "#print Eq", "#print Eq.rec"]:
            with self.subTest(source=source):
                messages = self.messages(source)
                self.assertTrue(messages)
                self.assertTrue(all(m["severity"] == "info" for m in messages))

    def test_semantic_tokens_survive_in_input_and_output(self):
        command = self.by_request[("#check congrArg", None)]
        self.assertTrue(any(p["tooltip"] for p in command["fragments"]))
        message, = command["messages"]
        self.assertEqual("".join(p["text"] for p in message["fragments"]), message["text"])
        self.assertTrue(any(p["tooltip"] for p in message["fragments"]))

    def test_eval_and_multiline_console_output(self):
        self.assertEqual(self.messages("#eval (2 + 2)")[0]["text"], "4")
        source = '#eval do\n  IO.println "https://example.com"\n  IO.println "/* literal */"'
        text = "".join(m["text"] for m in self.messages(source))
        self.assertIn("https://example.com", text)
        self.assertIn("/* literal */", text)

    def test_invalid_names_and_syntax_report_actual_lean_errors_and_continue(self):
        for source in ("#check Eq.congrArg", "#check DoesNotExist", "#check fun"):
            with self.subTest(source=source):
                self.assertTrue(any(m["severity"] == "error" for m in self.messages(source)))
        self.assertIn("Eq.congrArg", self.messages("#check Eq.congrArg")[0]["text"])
        self.assertTrue(all(m["severity"] == "info" for m in self.messages("#check Nat")))

    def test_module_selection_and_command_isolation(self):
        self.assertTrue(all(m["severity"] == "info" for m in self.messages("#check Nat.succ", "Init")))
        self.assertTrue(any(m["severity"] == "error" for m in self.messages("#check Lean.Expr", "Init")))
        self.assertTrue(all(m["severity"] == "info" for m in
                            self.messages("def slideTemporary : Nat := 1\n#check slideTemporary")))
        self.assertTrue(any(m["severity"] == "error" for m in self.messages("#check slideTemporary")))

    def test_typst_renders_inline_results_and_lean_errors_without_aborting(self):
        with tempfile.TemporaryDirectory(prefix="inline-render-", dir=build.BUILD) as temporary:
            directory = Path(temporary)
            (directory / "lean").mkdir()
            (directory / "lean.typ").write_bytes((DOCUMENT / "lean.typ").read_bytes())
            commands = [{**c, "lines": build.quote_lines(c["fragments"]),
                         "messages": [{**m, "lines": build.quote_lines(m["fragments"])}
                                      for m in c["messages"]]} for c in self.commands]
            build.write_json(directory / "lean.json", {
                "schemaVersion": 1, "declarations": {}, "commands": [], "inlineCommands": commands})
            source = '#import "lean.typ": lean-command\n#set text(size: 9pt)\n'
            for code, module in [("#check Eq.rec", None), ("#check congrArg", None),
                                 ("#check Eq.congrArg", None), ("#check fun", None),
                                 ("#check Lean.Expr", None), ("#check Lean.Expr", "Init")]:
                options = "" if module is None else ", module: " + json.dumps(module)
                source += "#lean-command(" + json.dumps(code) + options + ")\n"
            entry = directory / "check.typ"
            entry.write_text(source)
            output = directory / "check.pdf"
            build.run(["typst", "compile", "--root", directory, entry, output])
            from pypdf import PdfReader
            text = "\n".join(page.extract_text() for page in PdfReader(output).pages)
            self.assertIn("Eq.rec", text)
            self.assertIn("Unknown constant", text)


if __name__ == "__main__":
    unittest.main()
