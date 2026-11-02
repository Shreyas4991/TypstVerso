"""Integration checks for repeated tactic states; uses temporary Lean source modules."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SLIDES = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("slide_build", SLIDES / "build.py")
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
        with tempfile.TemporaryDirectory(prefix="SlideStateCheck_", dir=build.PROJECT / "Lec04") as source_dir, \
                tempfile.TemporaryDirectory(prefix="state-check-", dir=build.BUILD) as output_dir:
            directory = Path(source_dir)
            (directory / "Cases.lean").write_text(SOURCE)
            module = "Lec04." + directory.name + ".Cases"
            build.run(["lake", "build", "subverso-extract-mod", "+SubVerso.Signature", "+" + module], cwd=build.PROJECT)
            raw = Path(output_dir) / (module + ".subverso.json")
            decoded = Path(output_dir) / "decoded.json"
            build.run(["lake", "exe", "subverso-extract-mod", module, raw], cwd=build.PROJECT)
            build.run(["lake", "env", "lean", "--run", "ExportSlides.lean", raw, decoded], cwd=build.PROJECT)
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
            build.run(["lake", "env", "lean", "--run", "ResolveSlides.lean", request, result], cwd=build.PROJECT)
            resolved = json.loads(result.read_text())
            self.assertEqual(resolved["Lean.Expr"], "Lean.Expr")
            self.assertTrue(resolved["Nat"].startswith("Init."))

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


if __name__ == "__main__":
    unittest.main()
