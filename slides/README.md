# Lean quotations in Typst

`build.py` extracts declarations from the existing `../Lec04` project with SubVerso.
`lean.typ` renders their semantic highlighting, signatures, docstrings, and proof-state
bubbles. The script exports the same Touying deck as PDF and an offline HTML presentation.
Requires the project's Lean toolchain, Typst 0.15 or later, and Python 3.9 or later.

## Setup

From `slides/`:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

The Lake configuration already pins SubVerso to the revision tested with this project.
On a fresh checkout, run `lake update` in `Lec04/` to fetch the dependencies.
The build applies `../Lec04/subverso.patch` to that pinned checkout before compiling
the extractor. This fixes repeated tactic invocations under combinators: `all_goals`
gets a bubble for its entry state, and each inner tactic's bubble includes the results
from every branch in execution order. Completed branches contribute no remaining goals.
The patch is kept in the project so the fix survives a fresh dependency download.

The combinator-state integration checks use temporary Lean modules and can be run
from `slides/` with `.venv/bin/python tests/test_combinator_states.py`.

## Insert a declaration into main.typ

Select the modules to extract in `lean/config.json`:

```json
{"modules": ["Lec04.Basic", "Lec04.Recall"]}
```

Import the helper once in `main.typ`, then quote declarations by their Lean names:

```typst
#import "lean.typ": lean-quote, lean-state

#lean-quote("hello")
```

`hello` is an existing declaration in `Lec04.Basic`. A namespace declaration such as
`MyNamespace.myTheorem` is quoted by that fully qualified name, without the module prefix
unless it is actually part of the Lean name. All declarations defined by the selected
modules are extracted. Literal calls such as `#lean-quote("Lean.Expr")` and
`#lean-state("Nat")` also resolve imported declarations against these modules' Lean
environments and extract their defining source automatically. This includes Lean's
toolchain sources and dependency sources. Use fully qualified names for imported
declarations. For names constructed dynamically in Typst, list them explicitly:

```json
{"modules": ["Lec04.Basic", "Lec04.Recall"], "declarations": ["Lean.Expr"]}
```

After adding an imported quotation, rerun `build.py` (or restart an older watcher).
The source modules must compile. The script never edits them.

Run:

```sh
.venv/bin/python build.py
```

Outputs: `build/main.pdf` and `build/main.html`. Open the HTML file directly in a browser;
it embeds the slide images and metadata and needs no server or network connection.
Use arrow keys to navigate. Hover or focus a token or bubble for its information;
click to pin the popup, and press Escape to dismiss it. Documentation displays as plain text.

Proof-state bubbles appear automatically for tactic proofs, including the initial state
at `by` and the states SubVerso records after tactics. PDF uses text annotations over
the tokens and bubbles; hover/click support and popup appearance depend on the PDF viewer.
The current native PDF popups use the viewer's font settings; changing `player.html`
only affects HTML tooltips. The export cannot reliably enforce larger popup text in
Safari's PDF viewer. Use typeset text (such as `lean-state(..., size: 24pt)` for a
tactic proof state) when the PDF must display information at a guaranteed font size.
The browser export provides the interactive behaviour consistently. For a state that
should always be visible on a slide, use `lean-state`.
When a declaration has no tactic states, `lean-state` displays its elaborated type
signature instead. This works for term proofs and ordinary definitions as well.
Both signatures and tactic states retain Lean's semantic highlighting and token
hover information, including local variable types and available docstrings. The
export re-elaborates signatures with SubVerso, so inferred result types are included.
For explicit declaration signatures, `lean-state` retains the saved source's line
breaks and indentation. If a standalone source signature cannot be elaborated (for
example, its return type was inferred), it uses Lean's elaborated signature instead.

```typst
// Replace the name with a tactic theorem in one of your selected modules.
#lean-quote("MyNamespace.myTheorem", size: 20pt)
#lean-state("MyNamespace.myTheorem", index: 1)

// For the existing term proof, show its usual declaration type information.
#lean-state("isEven_iff")

// Optional: hide bubbles or select lines of the displayed declaration.
#lean-quote("MyNamespace.myTheorem", states: false, first: 1, last: 3)

// Scale indentation for this quotation only (rounded to whole spaces).
#lean-quote("Lean.Expr", first: 1, last: 12, indent: 50%)
```

`indent` defaults to `100%`. Use `50%` to halve leading indentation, or `0%` to
remove it. Spaces between tokens and indentation in other quotations are preserved.

Quotations and printed proof states inherit the surrounding slide font size by default.
Set `size:` on a quotation or state to override it.

Line and proof-state indices start at one; doc comments are omitted from the displayed
code but retained in hover information. Lines preserve indentation and do not wrap;
reduce `size` or select a shorter range for a long declaration. The quotation unit is
a Lean command, so a mutual block can include several declarations. Anonymous `example`
commands have no declaration name; use `lean-command` for commands such as `#check` or `#print`.

## Commands and their output

Use `lean-command` to quote a command already present in a selected Lean module:

```typst
#import "lean.typ": lean-command

#lean-command("#check BinaryTree")
#lean-command("#print BinaryTree", output-size: 14pt)
#lean-command("#eval (2 + 2)")
```

Each displays the source command followed by the messages Lean actually produced
while elaborating that module. Available semantic highlighting and token hovers are
retained in the output. Runtime text such as printed strings remains plain text.
Commands with no output display just the source.

```typst
// Show the source only.
#lean-command("#check BinaryTree", output: false)

// Disambiguate commands in different modules or repeated in the same module.
#lean-command("#check BinaryTree", module: "Lec04.Recall", occurrence: 1)
```

The command string must match the saved source, apart from leading and trailing
whitespace. Matching includes any internal line breaks in a multiline command.
A simple `#check` of an extracted declaration, such as `#check incr`, can also show
that declaration's recorded Lean signature without a separate command in the source.
`occurrence` starts at one. A command found in multiple modules requires `module:`.
Regenerate the metadata with `build.py` after adding commands. If a watcher was
started before command support was added, restart it to load the updated script.

## Refresh while editing

```sh
.venv/bin/python build.py --watch
```

Lean changes trigger extraction and rebuilding. Typst changes also rebuild the deck.
The watcher reloads itself when `build.py` changes.
If a build fails, the previous PDF and HTML remain available. Reload the HTML after a
successful build. Watch mode does not launch a server or reload browser tabs.

For the normal Typst editor preview, generate the metadata and compile `main.typ` normally:

```sh
.venv/bin/python build.py --extract-only
typst watch main.typ
```

The editor preview shows the typeset code and bubbles. Interactive hovers require
the script's HTML output; PDF annotations are added by the full build step.

To try the mechanism independently of the lecture:

```sh
.venv/bin/python build.py lean-demo.typ
```

`lean/snippets.json` is the generated snapshot used by Typst. Regenerate it after changing
Lean code, or commit it if readers should be able to compile Typst without a Lean installation.
The intermediate SubVerso format is decoded using the pinned SubVerso library in
`../Lec04/ExportSlides.lean`, rather than parsed by Python. The project's current
[SubVerso API](https://github.com/leanprover/subverso) supplies all Lean metadata;
neither a running Lean server nor lean-repl is needed when presenting the slides.
