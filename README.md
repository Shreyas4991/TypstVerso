# Lean + Typst project template

Write checked Lean code in `LeanProject/` and quote it in a slide deck, article,
or book under `documents/`.
The root `build.py` discovers actual Typst calls, extracts only missing Lean
declarations and command results, and exports an offline interactive HTML
document and an annotated PDF. Each document has its own `build/` directory;
all three use the same renderer and extraction cache.

```text
build.py                         incremental build driver
requirements.txt                 PDF annotation dependency
LeanProject/
  lakefile.toml                  Lean, Mathlib, and pinned SubVerso dependency
  lean-toolchain                 pinned Lean toolchain
  lake-manifest.json             Lake's dependency lockfile
  subverso.patch                 selective extraction and tactic-state fixes
  ExportLean.lean                SubVerso decoding and command evaluation
  LeanProject.lean               imports the modules available to quotations
  LeanProject/Basic.lean         starter definition and multiline proof
documents/
  slides/main.typ                sample presentation (20pt body text)
  slides/build/                  main.html and main.pdf for the slides
  article/main.typ               sample A4 article (11pt body text)
  article/build/                 main.html and main.pdf for the article
  book/main.typ                  sample B5 book with contents and chapters (10pt)
  book/build/                    main.html and main.pdf for the book
typst/
  lean.typ                       shared quotation and proof-state rendering
  lean.json                      generated extraction data and cache
templates/html/
  slides.html                    slide navigation and fullscreen presentation
  article.html                   scrolling article reader
  book.html                      scrolling book reader with a table of contents
  reader.js                      shared article/book page rendering
  tooltips.js                    shared Lean token and proof-state popups
  tooltips.css                   shared popup styles
tests/
```

## Setup and build

Requires Python 3.9+, Typst 0.15+, Git, and Lean installed through Elan.
Run these commands from the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python build.py
.venv/bin/python build.py --document documents/article
.venv/bin/python build.py --document documents/book
```

On the first build, the driver runs `lake update` if SubVerso has not been fetched,
applies the checked-in patch, and builds the Lean modules it needs. Mathlib is
included as a dependency; the starter proof only needs Lean itself. When adding
Mathlib imports, downloading its compiled cache first can avoid a large local build:

```sh
cd LeanProject
lake exe cache get
```

For HTML alone, no Python packages or virtual environment are required:

```sh
python3 build.py --format html
python3 build.py --document documents/article --format html --watch
```

Open the selected document's `build/main.html` directly in a browser. Slides use
arrow-key navigation; articles and books display all pages in a scrolling reader.
The book's sidebar uses Typst's outlined chapter and section headings, with links
to their exact positions, including multiple sections on the same page.
Hover or focus a name or proof-state bubble to see its information; click to pin
a popup and press Escape to dismiss it. Popups appear above or below the hovered
text. Move into a popup to keep it open and scroll long documentation; it closes
after leaving both the source and popup unless pinned. The HTML needs no server
or network.

## Writing quotations

Add Lean modules to the imports in `LeanProject/LeanProject.lean`. Then use fully
qualified declaration names in Typst:

```typst
#import "../../typst/lean.typ": lean-quote, lean-state, lean-command

#lean-quote("Demo.hello")
#lean-quote("Demo.identity_pair")
#lean-state("Demo.identity_pair", index: 2)
#lean-command("#check Demo.identity_pair")
#lean-command("#eval (2 + 2)")
```

Imported declarations, including Lean's own definitions, are also resolved against
the selected Lean environment. For example, `#lean-quote("Eq")` extracts its
defining command from `Init.Prelude`. The whole defining module is elaborated to
preserve its context, but only requested declarations are highlighted and decoded.
Generated declarations without quotable source ranges may not support `lean-quote`;
use `lean-command("#check …")` or `lean-command("#print …")` instead.

Computed names and command strings work. Typst evaluates them during discovery;
there is no Python parser for Typst source and no declaration list to maintain.
Calls in imported document files, loops, and wrapper functions are included when
they are evaluated by the document.

Commands run in fresh environments importing `LeanProject`. Use fully qualified
names; a command does not inherit lexical scopes from its original source file.
Use `module: "Some.Module"` to select another import environment. Put related
commands in one multiline string when they share temporary definitions. Lean
diagnostics are logged and displayed alongside their command, as in the demo.

`lean-quote` accepts `size`, `states`, one-based inclusive `first`/`last` source
lines, `indent` (a percentage), `line-spacing`, `blank-lines`, and `comments`.
`lean-state` accepts a one-based `index` and `size`; for a declaration without
tactic states, it displays the highlighted type signature.

Code quotations, command output, and printed proof states default to `size: 1em`,
so they inherit the surrounding document's text size. The samples set their body
size with `#set text(size: ...)`; no per-quotation overrides are needed. Use
`size:` only for an intentional local override. The source remains monospaced.

## Incremental builds and recovery

1. Typst runs a discovery pass with `lean-discover=true`. The quotation functions
   emit request metadata instead of rendering code, so this works without a cache.
2. Python compares these requests with `typst/lean.json`, resolves missing
   declarations, groups them by defining module, and invokes SubVerso only for
   those declarations. Missing commands are evaluated in a batch.
3. Python writes the updated cache atomically and runs Typst for the final export.
4. If a final pass encounters another missing item, `lean.typ` emits a tagged
   `LEAN_REQUEST` diagnostic. Python extracts that item and retries automatically.
   Repeated requests that make no progress stop with an error instead of looping.

Prose, styling, and page layout changes reuse the cached Lean results. New
quotations only add missing data. Changes to the Lean project, dependency sources,
toolchain configuration, patch, or exporter invalidate the cache; currently this
conservatively invalidates all saved results, then extracts the requested subset.
Commands using external data or other side effects need an explicit `--refresh`
when those inputs change.

Ordinary Typst errors and unresolvable Lean declarations are reported without an
extraction retry loop. Failed builds leave the previous HTML and PDF available.
Watch mode stays running so fixing the input triggers another build. It does not
automatically reload browser tabs.

All extraction data and cache bookkeeping live in **one generated JSON file**,
`typst/lean.json`, shared by slides, articles, and books. SubVerso output,
resolved-name maps, and intermediate command
results pass through stdin/stdout in memory. Hover coordinates are embedded in the
HTML and PDF; no region JSON file is produced. Lake's `lake-manifest.json` remains
a separate dependency lockfile, and Lake manages its own ignored dependency caches.

Additional commands:

```sh
python3 build.py --refresh --format html  # regenerate requested Lean data
python3 build.py --extract-only          # refresh data for a Typst editor preview
python3 build.py --watch                 # rebuild after Lean/document changes
python3 build.py another.typ             # entry path relative to documents/slides/
python3 build.py --document documents/book --watch
python3 build.py --module LeanProject --module Lean  # additional import environments
```

The document and Lean roots can be changed with `--document` and `--project`;
`--output` overrides that document's build directory. The HTML layout is inferred
from the document folder name, or selected explicitly with `--template slides`,
`--template article`, or `--template book`. Custom folder names default to the
article reader. `--library` and `--templates` override the shared resource folders.
Watch mode also watches the shared Typst renderer and HTML templates.

The HTML exports embed the templates' scripts, styles, SVG pages, and hover data;
there are no runtime file dependencies. Article/book HTML preserves the paginated
Typst layout using SVG, rather than reflowing the prose as native HTML paragraphs.

After extraction, normal Typst compilation works for typesetting. Set the project
root to this repository so sibling imports and the shared cache remain accessible:

```sh
typst compile --root . documents/article/main.typ documents/article/build/preview.pdf
```

The Python driver supplies interactive HTML and PDF annotations. PDF popup
appearance depends on the viewer.

## Checks

```sh
.venv/bin/python -m unittest discover -s tests -v
```

The tests exercise actual Lean/SubVerso and Typst, including multiline proof
states, semantic hover data, computed requests, cold and cached builds, incremental
additions, missing-data recovery, and preservation of successful output after errors.
They also compile all three samples and check separate output folders and inherited
font sizes. An optional browser smoke check uses Playwright and an installed Google
Chrome to test navigation, tooltip pinning, mobile layout, and offline loading:

```sh
.venv/bin/python -m pip install playwright
.venv/bin/python tests/check_html.py
```
