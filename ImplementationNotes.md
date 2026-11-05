# Implementation notes

For setup instructions and where to start writing, see [README.md](README.md).
This file explains how the code works and how to change it. These notes are AI-pilled. Don't read them if you dislike AI text.

## Terms used below

- A **build** turns the document's source files into finished files.
- A **declaration** is a Lean definition or theorem. A **module** is a named Lean file.
- A **proof state** shows the assumptions available and the goals still to prove.
- **Extraction** means collecting Lean code, types, documentation, and proof states for a document.
- A **cache** saves those results so unchanged work does not need to be repeated.
- **Metadata** is information about content, such as a heading's level or a token's position.
- An **environment** is the collection of Lean definitions available to a command.
- A **dependency** is other code this project needs. A **lockfile** records its exact versions.
- A **toolchain** is a particular version of Lean and its build tools. **Pinned** means fixed to a particular version.
- **JSON** is a text format for storing named values and lists. **SVG** is a picture format used for the document pages in the browser.

Lake is Lean's build program. SubVerso reads checked Lean code and collects the
information used in quotations. Mathlib is a collection of mathematical definitions
and proofs for Lean.

## Lean file visibility

With Lean's `module` header, definitions are private by default. The starter file
uses `@[expose] public section` after its imports so the definitions below it can
be used from the project entry file and from document commands. Keep this line
when adding proofs. A missing declaration error includes this check alongside the
name and import checks.

## Project layout

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
  blog/main.typ                  collection of dated posts, sorted latest first
  blog/posts/                    one Typst file per post (title, date, body)
  blog/build/                    main.html and main.pdf for the blog
typst/
  lean.typ                       shared quotation and proof-state rendering
  blog.typ                       blog-date, blog-post, and sorted blog layout
  lean.json                      generated extraction data and cache
templates/html/
  slides.html                    slide navigation and fullscreen presentation
  article.html                   scrolling article reader
  book.html                      scrolling book reader with a table of contents
  blog.html                      book-style reader with a latest-first post index
  blog.js                        blog rendering and post-only navigation
  reader.js                      shared article/book page rendering
  tooltips.js                    shared Lean token and proof-state popups
  tooltips.css                   shared popup styles
tests/
```

## Lean dependencies

On the first build, the driver runs `lake update` if SubVerso has not been fetched,
applies the checked-in patch, and builds the Lean modules it needs. Mathlib is
included as a dependency; the starter proof only needs Lean itself. When adding
Mathlib imports, downloading its compiled cache first can avoid a large local build:

```sh
cd LeanProject
lake exe cache get
```

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
defining command from `Init.Prelude`. The whole defining module is checked to
preserve its context, but only requested declarations are highlighted and decoded.
Generated declarations without source text to quote may not support `lean-quote`;
use `lean-command("#check …")` or `lean-command("#print …")` instead.

Computed names and command strings work. Typst evaluates them during discovery;
there is no Python parser for Typst source and no declaration list to maintain.
Calls in imported document files, loops, and wrapper functions are included when
they are evaluated by the document.

Commands run in fresh environments importing `LeanProject`. Use fully qualified
names; a command does not keep local settings from its original source file.
Use `module: "Some.Module"` to select another import environment. Put related
commands in one multiline string when they share temporary definitions. Lean
diagnostics are logged and displayed alongside their command, as in the demo.

Commands with different `module:` settings run in separate Lean processes.
Importing a larger library can register global Lean extensions; an older
environment in the same process may not have the matching state. Separating
these import contexts prevents a Mathlib command from corrupting a later command
that uses only Lean's basic imports.

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
   those declarations. Missing commands are evaluated together.
3. Python replaces the cache file after its updated contents are ready and runs Typst for the final export.
4. If a final pass encounters another missing item, `lean.typ` reports the error,
   probable cause, and probable fix in plain language. Python reads the quoted
   name or command from that message, extracts the item, and retries automatically.
   Repeated requests that make no progress stop with an error instead of looping.

Missing-result messages suggest waiting about a minute if `build.py` is already
running, checking its terminal for errors, and saving the Typst file again. They
also include the commands to start continuous rebuilding or build once. No JSON
request is shown to the user. The reader still understands older `LEAN_REQUEST`
messages for documents using an older copy of `lean.typ`.

Prose, styling, and page layout changes reuse the cached Lean results. New
quotations only add missing data. Changes to the Lean project, dependency sources,
toolchain configuration, patch, or exporter discard the cache; currently this
conservatively discards all saved results, then extracts the requested subset.
Commands using external data or other side effects need an explicit `--refresh`
when those inputs change.

Ordinary Typst errors and unresolvable Lean declarations are reported without an
extraction retry loop. Failed builds leave the previous HTML and PDF available.
Watch mode stays running so fixing the input triggers another build. It does not
automatically reload browser tabs.

All extraction data and cache bookkeeping live in **one generated JSON file**,
`typst/lean.json`, shared by slides, articles, books, and blogs. SubVerso output,
resolved-name maps, and intermediate command
results pass directly between programs through their standard input and output, without being saved as files. Hover coordinates are embedded in the
HTML and PDF; no region JSON file is produced. Lake's `lake-manifest.json` remains
a separate dependency lockfile, and Lake manages its own ignored dependency caches.

Builders sharing `typst/lean.json` take an operating-system file lock for each
complete document build. Data is reloaded after taking the lock, so a waiting
watcher or manual build sees earlier results rather than overwriting them with
an older copy. File replacement uses a unique temporary filename for each write.
The lock is released when a build finishes or its process exits. Lock and
temporary files are ignored when watching for edits.

Additional commands:

```sh
python3 build.py --all                   # build all four sample documents
python3 build.py --all --watch           # watch all four document folders
python3 build.py --all --format html     # HTML only; no Python packages required
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
`--template article`, `--template book`, or `--template blog`. Custom folder names default to the
article reader. `--library` and `--templates` override the shared resource folders.
Watch mode also watches the shared Typst display code and HTML templates.

`--all` builds `documents/slides`, `documents/article`, `documents/book`, and
`documents/blog`
sequentially, preserving their separate output directories and shared cache.
`--all --refresh` discards the cache once before the first document, so subsequent
documents can reuse and extend the newly extracted data. With `--all --output DIR`,
each document's output goes into `DIR/slides`, `DIR/article`, `DIR/book`, or `DIR/blog`.
`--all --watch` watches all four document folders and the shared inputs together;
a change triggers a rebuild of all four. Failed documents are reported while the
other documents still build. A one-off run returns a nonzero exit code if any fail.

The HTML exports embed the templates' scripts, styles, SVG pages, and hover data;
no extra files need to be loaded when reading the document. Article/book/blog HTML preserves the paginated
Typst layout using SVG, rather than rearranging the prose to fit the browser window.

After extraction, normal Typst compilation works for typesetting. Set the project
root to this repository so sibling imports and the shared cache remain accessible:

```sh
typst compile --root . documents/article/main.typ documents/article/build/preview.pdf
```

The Python driver supplies interactive HTML and PDF annotations. PDF popup
appearance depends on the viewer.

## Browser navigation and tooltips

The book's table of contents comes from `query(heading)` in the final Typst layout.
Only outlined headings are included. The exporter records their levels, computed
numbering, plain-text titles, page numbers, and vertical positions in the HTML's
embedded page data. The reader creates nested links and anchors at those positions,
so different sections on one page can be targeted separately.

The blog uses the same heading positions and interactive rendering as the book.
Each file in `documents/blog/posts/` exports a `post` made with `blog-post`, with a
manually chosen `blog-date(year, month, day)`. The collection in `main.typ` is
sorted by descending calendar date before typesetting, so PDF pages, SVG pages,
and the sidebar index agree. Equal dates retain import order. Post titles use
level-one headings; the HTML sidebar filters out deeper section headings.
Both HTML and PDF open directly with the latest post, without an introductory
title or index page. The blog disables heading and page numbering and omits
the HTML page count.

All HTML layouts use the same tooltip code and styles. The popup is placed above
or below its triggering region and its height is limited to the available space.
A 200ms close delay lets the pointer cross the gap from source text to the popup.
Hovering or focusing the popup cancels that delay. Wheel scrolling stays inside a
long popup instead of scrolling the reader underneath it. Clicking a source region
pins its popup; Escape or a click outside dismisses it.

## Checks

```sh
.venv/bin/python -m unittest discover -s tests -v
```

The tests exercise actual Lean/SubVerso and Typst, including multiline proof
states, Lean types and documentation shown on hover, computed requests, cold and cached builds, incremental
additions, missing-data recovery, and preservation of successful output after errors.
They also compile all four samples and check separate output folders and inherited
font sizes. An optional browser smoke check uses Playwright and an installed Google
Chrome to test navigation, tooltip pinning, mobile layout, and offline loading:

```sh
.venv/bin/python -m pip install playwright
.venv/bin/python tests/check_html.py
```
