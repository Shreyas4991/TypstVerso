#!/usr/bin/env python3
"""Incrementally extract requested Lean code and export a Typst document."""
import argparse
from contextlib import contextmanager
import errno
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT / "LeanProject"
DOCUMENT = ROOT / "documents/slides"
LIBRARY = ROOT / "typst"
TEMPLATES = ROOT / "templates/html"
DOCUMENT_KINDS = ("slides", "article", "book")
BUILD = DOCUMENT / "build"
MODULES = ["LeanProject"]
REQUEST_PREFIX = "LEAN_REQUEST:"


class ProcessFailure(subprocess.CalledProcessError):
    def __str__(self):
        return (self.stderr or self.stdout or "").strip() or super().__str__()


def run(args, cwd=PROJECT, capture=False, env=None, input=None):
    command = [str(a) for a in args]
    result = subprocess.run(command, cwd=cwd, text=True, input=input,
                            stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.PIPE if capture else None, env=env)
    if result.returncode:
        raise ProcessFailure(result.returncode, command, output=result.stdout, stderr=result.stderr)
    if capture and result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.stdout


@contextmanager
def build_lock(library):
    """Serialize builders sharing data; the OS releases this lock after a crash."""
    library.mkdir(parents=True, exist_ok=True)
    with (library / ".build.lock").open("a+b") as lock:
        if os.name == "nt":
            import msvcrt
            if lock.seek(0, os.SEEK_END) == 0:
                lock.write(b"0")
                lock.flush()
            waiting = False
            while True:
                lock.seek(0)
                try:
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as error:
                    if error.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                        raise
                    if not waiting:
                        print("Waiting for another build to finish...", flush=True)
                        waiting = True
                    time.sleep(0.1)
            try:
                yield
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print("Waiting for another build to finish...", flush=True)
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def write_json(path, value):
    """Atomically replace the single extraction/cache file, only when it changes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path.is_file() and path.read_text() == content:
        return
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix=".lean-", suffix=".tmp",
                                     dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def quote_lines(fragments):
    """Keep whitespace and semantic tokens; omit doc comments from displayed code."""
    lines = [[]]
    for fragment in fragments:
        if fragment["kind"] == "doc-comment":
            continue
        if fragment["kind"] == "state":
            lines[-1].append(fragment)
            continue
        for i, part in enumerate(fragment["text"].split("\n")):
            if i:
                lines.append([])
            if part:
                lines[-1].append({**fragment, "text": part})
    def blank(line):
        return all(p["kind"] != "state" and not p["text"].strip() for p in line)
    while lines and blank(lines[0]):
        lines.pop(0)
    while lines and blank(lines[-1]):
        lines.pop()
    return lines


def prepare_subverso(project=None):
    project = PROJECT if project is None else project
    package = project / ".lake/packages/subverso"
    patch = project / "subverso.patch"
    if not package.is_dir():
        raise RuntimeError("Fetch dependencies first: run lake update in " + str(project))
    applied = subprocess.run(["git", "apply", "--reverse", "--check", str(patch)],
                             cwd=package, capture_output=True, text=True)
    if applied.returncode == 0:
        return
    check = subprocess.run(["git", "apply", "--check", str(patch)],
                           cwd=package, capture_output=True, text=True)
    if check.returncode:
        raise RuntimeError("Cannot apply subverso.patch: " + check.stderr.strip())
    run(["git", "apply", patch], cwd=package)


def source_snapshot(project):
    """Include dependency sources; exclude compiled artifacts and nested caches."""
    paths = []
    for base in (project, project / ".lake/packages"):
        for directory, dirs, files in os.walk(base):
            dirs[:] = sorted(d for d in dirs if d not in {
                ".git", ".lake", ".venv", "node_modules", "__pycache__"})
            for name in sorted(files):
                if (name.endswith((".lean", ".patch")) or
                        name in {"lakefile.toml", "lake-manifest.json", "lean-toolchain"}):
                    path = Path(directory) / name
                    try:
                        stat = path.stat()
                    except FileNotFoundError:
                        continue
                    paths.append((str(path.relative_to(project)), stat.st_mtime_ns, stat.st_size))
    return sorted(paths)


def request_key(request):
    return json.dumps(request, ensure_ascii=False, sort_keys=True)


def validate_request(request):
    if not isinstance(request, dict):
        raise ValueError("Invalid Lean extraction request")
    if request.get("kind") == "declaration" and isinstance(request.get("name"), str):
        return {"kind": "declaration", "name": request["name"]}
    if request.get("kind") == "command" and isinstance(request.get("source"), str):
        module = request.get("module")
        if module is not None and not isinstance(module, str):
            raise ValueError("Lean command module must be a string")
        return {"kind": "command", "source": request["source"].strip(), "module": module}
    raise ValueError("Invalid Lean extraction request: " + repr(request))


class TypstFailure(RuntimeError):
    def __init__(self, result):
        self.diagnostics = result.stderr
        super().__init__(result.stderr.strip())

    def missing_request(self):
        for line in self.diagnostics.splitlines():
            if "error:" not in line or REQUEST_PREFIX not in line:
                continue
            try:
                request, _ = json.JSONDecoder().raw_decode(line.split(REQUEST_PREFIX, 1)[1])
                return validate_request(request)
            except (ValueError, TypeError):
                continue
        return None


class Builder:
    def __init__(self, project=PROJECT, document=DOCUMENT, output=None,
                 modules=None, refresh=False, formats="both", library=LIBRARY,
                 templates=TEMPLATES, kind=None):
        self.project = Path(project).resolve()
        self.document = Path(document).resolve()
        self.library = Path(library).resolve()
        self.root = Path(os.path.commonpath([self.document, self.library]))
        self.templates = Path(templates).resolve()
        self.kind = kind or (self.document.name if self.document.name in DOCUMENT_KINDS else "article")
        if self.kind not in DOCUMENT_KINDS:
            raise ValueError("Unknown document template: " + self.kind)
        self.output = Path(output).resolve() if output is not None else self.document / "build"
        self.modules = list(MODULES if modules is None else modules)
        if not self.modules or any(not re.fullmatch(r"[\w']+(?:\.[\w']+)*", m)
                                   for m in self.modules):
            raise ValueError("Provide valid Lean module names with --module")
        self.formats = formats
        self.path = self.library / "lean.json"
        self.refresh = refresh
        self.load_cache(refresh)

    def load_cache(self, refresh=False):
        self.ready = False
        self.built_modules = set()
        self.env = None
        self.data = {"schemaVersion": 1, "declarations": {}, "commands": [], "inlineCommands": []}
        self.fingerprint = self.lean_fingerprint()
        if self.path.is_file() and not refresh:
            try:
                saved = json.loads(self.path.read_text())
                if (saved.get("schemaVersion") == 1 and
                        saved.get("_cache", {}).get("fingerprint") == self.fingerprint and
                        isinstance(saved.get("declarations"), dict) and
                        isinstance(saved.get("commands"), list) and
                        isinstance(saved.get("inlineCommands"), list)):
                    self.data = saved
            except (ValueError, AttributeError):
                print("Discarding invalid extraction cache: " + str(self.path), file=sys.stderr)

    def lean_fingerprint(self):
        digest = hashlib.sha256(Path(__file__).read_bytes())
        digest.update(request_key({"project": str(self.project), "modules": self.modules,
                                   "sources": source_snapshot(self.project)}).encode())
        return digest.hexdigest()

    def save(self):
        if self.lean_fingerprint() != self.fingerprint:
            raise RuntimeError("Lean inputs changed during extraction; rebuild to use the updated sources")
        self.data["_cache"] = {"fingerprint": self.fingerprint}
        write_json(self.path, self.data)

    def prepare(self, extra_modules=()):
        targets = set(self.modules) | set(extra_modules)
        if self.ready and targets <= self.built_modules:
            return
        if not (self.project / ".lake/packages/subverso").is_dir():
            run(["lake", "update"], cwd=self.project)
        prepare_subverso(self.project)
        fingerprint = self.lean_fingerprint()
        if fingerprint != self.fingerprint and "_cache" in self.data:
            raise RuntimeError("Lean inputs changed during the build; rebuild to use the updated sources")
        # Fetching dependencies and applying the patch intentionally change inputs.
        # Capture them before building, so later editor changes cannot bless stale data.
        self.fingerprint = fingerprint
        run(["lake", "build", "subverso-extract-mod", "+SubVerso.Signature",
             *["+" + m for m in sorted(targets - self.built_modules)]], cwd=self.project)
        sysroot = run(["lake", "env", "lean", "--print-prefix"],
                      cwd=self.project, capture=True).strip()
        self.env = {**os.environ, "LEAN_SYSROOT": sysroot}
        self.built_modules.update(targets)
        self.ready = True

    def bridge(self, arguments, value):
        result = run(["lake", "env", "lean", "--run", "ExportLean.lean", *arguments],
                     cwd=self.project, capture=True, env=self.env,
                     input=value if isinstance(value, str) else json.dumps(value))
        return json.loads(result)

    def extract_declarations(self, names):
        self.prepare()
        resolved = self.bridge(["--resolve"], {"modules": self.modules, "declarations": names})
        groups = {}
        for name in names:
            groups.setdefault(resolved[name], []).append(name)
        for module, selected in sorted(groups.items()):
            print(f"Extracting {len(selected)} declaration(s) from {module}", flush=True)
            flags = [arg for name in selected for arg in ("--declaration", name)]
            executable = self.project / ".lake/packages/subverso/.lake/build/bin/subverso-extract-mod"
            raw = run(["lake", "env", executable, *flags, module], cwd=self.project,
                      capture=True, env=self.env)
            decoded = self.bridge(["--decode", module, *selected], raw)
            for name in selected:
                declaration = decoded["declarations"].get(name)
                if declaration is None:
                    raise RuntimeError("No source declaration extracted for " + name)
                self.data["declarations"][name] = {
                    "module": module, "source": declaration["source"],
                    "signature": declaration["signature"],
                    "signatureFragments": declaration["signatureFragments"],
                    "lines": quote_lines(declaration["fragments"])}

    def ensure_requests(self, requests):
        normalized = {request_key(r): r for r in map(validate_request, requests)}
        missing = sorted({r["name"] for r in normalized.values()
                          if r["kind"] == "declaration" and
                          r["name"] not in self.data["declarations"]})
        pending = [r for r in normalized.values() if r["kind"] == "command" and not any(
            c["source"] == r["source"] and c["module"] == r["module"]
            for c in self.data["inlineCommands"])]
        if missing:
            self.extract_declarations(missing)
        if pending:
            self.prepare(r["module"] for r in pending if r["module"] is not None)
            print(f"Evaluating {len(pending)} Lean command(s)", flush=True)
            groups = {}
            for request in pending:
                groups.setdefault(request["module"], []).append(request)
            commands = []
            for module, requests in groups.items():
                # Importing Mathlib registers global Lean extensions. Reusing an
                # older environment afterwards can panic inside Lean. Keep distinct
                # import contexts in separate processes, including their initial import.
                commands.extend(self.bridge(["--commands"], {
                    "modules": self.modules if module is None else [module], "commands": requests}))
            for command in commands:
                self.data["inlineCommands"].append({
                    "module": command["module"], "source": command["source"],
                    "lines": quote_lines(command["fragments"]),
                    "messages": [{**m, "lines": quote_lines(m["fragments"])}
                                 for m in command["messages"]]})
        self.save()
        return bool(missing or pending)

    def typst(self, arguments):
        result = subprocess.run(["typst", *map(str, arguments), "--root", str(self.root),
                                 "--diagnostic-format", "short"],
                                cwd=self.document, capture_output=True, text=True)
        if result.returncode:
            raise TypstFailure(result)
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        return result.stdout

    def discover(self, entry):
        expression = '''query(metadata).filter(item => type(item.value) == dictionary and
          item.value.at("kind", default: "") == "lean-request").map(item => item.value.request)'''
        return json.loads(self.typst(["eval", expression, "--in", entry,
                                      "--input", "lean-discover=true"]))

    def export(self, entry):
        self.output.mkdir(parents=True, exist_ok=True)
        stem = entry.stem
        with tempfile.TemporaryDirectory(prefix="export-", dir=self.output) as temporary:
            directory = Path(temporary)
            targets = []
            if self.formats in {"pdf", "both"}:
                self.typst(["compile", entry, directory / "document.pdf"])
            if self.formats in {"html", "both"}:
                self.typst(["compile", "--format", "svg", entry, directory / "page-{n}.svg"])
            expression = '''query(metadata).filter(item => type(item.value) == dictionary and
              item.value.at("kind", default: "") == "lean-hover").map(item => {
              let p = item.location().position()
              (page: p.page, x: p.x.pt(), y: p.y.pt(), ..item.value)
            })'''
            regions = json.loads(self.typst(["eval", expression, "--in", entry]))
            if self.formats in {"html", "both"}:
                # Ask Typst for outlined headings and their final locations, including
                # computed chapter numbers; never infer a contents list from page text.
                outline_expression = '''
                  let plain(body) = {
                    if type(body) == str { body }
                    else if type(body) == content {
                      if (body.func() == [ ].func() or body.func() == linebreak
                        or body.func() == parbreak or body.func() == h) { " " }
                      else if body.has("text") { body.text }
                      else if body.has("children") { body.children.map(plain).join() }
                      else if body.has("body") { plain(body.body) }
                      else { "" }
                    } else { "" }
                  }
                  query(heading).filter(h => h.outlined).map(h => {
                    let p = h.location().position()
                    let n = if h.numbering == none { "" }
                      else { plain(numbering(h.numbering, ..counter(heading).at(h.location()))) }
                    (level: h.level, title: if n == "" { plain(h.body) }
                      else { n + " " + plain(h.body) },
                      page: p.page, y: p.y.pt())
                  })'''
                headings = json.loads(self.typst(["eval", outline_expression, "--in", entry]))
                for index, heading in enumerate(headings, 1):
                    heading["id"] = f"heading-{index}"
                pages = []
                svgs = sorted(directory.glob("page-*.svg"), key=lambda p: int(p.stem.split("-")[-1]))
                for number, svg in enumerate(svgs, 1):
                    markup = svg.read_text()
                    width, height = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', markup).groups()
                    pages.append({"svg": markup, "width": float(width), "height": float(height),
                                  "regions": [r for r in regions if r["page"] == number],
                                  "headings": [h for h in headings if h["page"] == number]})
                template = (self.templates / (self.kind + ".html")).read_text()
                for marker, name in (("__TOOLTIPS_CSS__", "tooltips.css"),
                                     ("__TOOLTIPS_JS__", "tooltips.js"),
                                     ("__READER_JS__", "reader.js")):
                    if marker in template:
                        template = template.replace(marker, (self.templates / name).read_text())
                payload = json.dumps(pages, ensure_ascii=False).replace("<", "\\u003c")
                document = template.replace("__DOCUMENT_DATA__", payload).replace("__TITLE__", html.escape(stem))
                (directory / "document.html").write_text(document)
                targets.append((directory / "document.html", self.output / (stem + ".html")))
            if self.formats in {"pdf", "both"}:
                annotate_pdf(directory / "document.pdf", directory / "annotated.pdf", regions)
                targets.append((directory / "annotated.pdf", self.output / (stem + ".pdf")))
            for source, destination in targets:
                source.replace(destination)
            print("Built " + ", ".join(str(p) for _, p in targets) +
                  f" ({len(regions)} Lean hover regions)", flush=True)

    def build(self, entry="main.typ", extract_only=False):
        with build_lock(self.library):
            # A different process may have updated the data while this one waited.
            self.load_cache(self.refresh)
            self.refresh = False
            self.build_locked(entry, extract_only)

    def build_locked(self, entry="main.typ", extract_only=False):
        entry = (self.document / entry).resolve()
        if not entry.is_file() or not entry.is_relative_to(self.document):
            raise ValueError("The entry file must be inside the document project")
        self.ensure_requests(self.discover(entry))
        if extract_only:
            return
        attempted = set()
        for _ in range(32):
            try:
                self.export(entry)
                return
            except TypstFailure as error:
                request = error.missing_request()
                if request is None:
                    raise
                key = request_key(request)
                if key in attempted:
                    raise RuntimeError("Typst still reports missing data after extraction: " + key) from error
                attempted.add(key)
                print("Typst requested missing Lean data; extracting and retrying: " + key, flush=True)
                if not self.ensure_requests([request]):
                    raise RuntimeError("Missing-data diagnostic made no extraction progress: " + key) from error
        raise RuntimeError("Stopped after 32 missing-data retries; check document-dependent requests")


def annotate_pdf(source, target, regions):
    try:
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import (ArrayObject, DecodedStreamObject, DictionaryObject, FloatObject,
                                   NameObject, NumberObject, TextStringObject)
    except ImportError:
        raise RuntimeError("Install PDF support: .venv/bin/python -m pip install -r requirements.txt") from None
    writer = PdfWriter()
    writer.clone_document_from_reader(PdfReader(source))
    for region in regions:
        page = writer.pages[region["page"] - 1]
        x, y = region["x"], float(page.mediabox.height) - region["y"]
        w, h = region["width"], region["height"]
        appearance = DecodedStreamObject()
        appearance.set_data(b"")
        appearance.update({NameObject("/Type"): NameObject("/XObject"),
                           NameObject("/Subtype"): NameObject("/Form"),
                           NameObject("/BBox"): ArrayObject([FloatObject(v) for v in (0, 0, w, h)]),
                           NameObject("/Resources"): DictionaryObject()})
        annotation = DictionaryObject({
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Text"),
            NameObject("/Rect"): ArrayObject([FloatObject(v) for v in (x, y - h, x + w, y)]),
            NameObject("/Contents"): TextStringObject(region["tooltip"]),
            NameObject("/T"): TextStringObject("Lean proof state" if region["role"] == "state" else "Lean"),
            # Invisible appearance preserves the typeset token/bubble; contents remain clickable.
            NameObject("/Name"): NameObject("/Comment"),
            NameObject("/F"): NumberObject(0),
            NameObject("/AP"): DictionaryObject({NameObject("/N"): writer._add_object(appearance)}),
        })
        writer.add_annotation(region["page"] - 1, annotation)
    with target.open("wb") as stream:
        writer.write(stream)


def watch_snapshot(project, document, library=LIBRARY, templates=TEMPLATES):
    paths = [(str(Path(__file__)), Path(__file__).stat().st_mtime_ns, Path(__file__).stat().st_size)]
    paths += source_snapshot(project)
    documents = [document] if isinstance(document, (str, os.PathLike)) else document
    for root in documents:
        for directory, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d not in {".git", ".venv", "build", "__pycache__"})
            for name in sorted(files):
                if name == "lean.json":
                    continue
                path = Path(directory) / name
                try:
                    stat = path.stat()
                except FileNotFoundError:
                    continue
                paths.append((str(path), stat.st_mtime_ns, stat.st_size))
    for base in (library, templates):
        for path in sorted(Path(base).rglob("*")):
            if path.is_file() and path.name not in {"lean.json", ".build.lock"} and path.suffix != ".tmp":
                try:
                    stat = path.stat()
                except FileNotFoundError:
                    continue
                paths.append((str(path), stat.st_mtime_ns, stat.st_size))
    return paths


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entry", nargs="?", default="main.typ")
    parser.add_argument("--project", type=Path, default=PROJECT)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--document", type=Path, default=DOCUMENT)
    selection.add_argument("--all", action="store_true", help="Build slides, article, and book")
    parser.add_argument("--output", type=Path, help="Output directory (default: DOCUMENT/build)")
    parser.add_argument("--library", type=Path, default=LIBRARY, help="Shared lean.typ and extraction cache")
    parser.add_argument("--templates", type=Path, default=TEMPLATES, help="HTML template directory")
    parser.add_argument("--template", choices=DOCUMENT_KINDS, help="Browser layout (inferred from document folder)")
    parser.add_argument("--module", action="append", dest="modules", help="Lean environment to import (repeatable)")
    parser.add_argument("--format", choices=["html", "pdf", "both"], default="both")
    parser.add_argument("--extract-only", action="store_true")
    parser.add_argument("--refresh", action="store_true", help="Discard the extraction cache once")
    parser.add_argument("--watch", action="store_true")
    args = parser.parse_args(argv)
    documents = [ROOT / "documents" / kind for kind in DOCUMENT_KINDS] if args.all else [args.document]
    previous = None
    loaded_script = Path(__file__).stat().st_mtime_ns
    while True:
        if args.watch and Path(__file__).stat().st_mtime_ns != loaded_script:
            os.execv(sys.executable, [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]])
        current = watch_snapshot(args.project.resolve(), [p.resolve() for p in documents],
                                 args.library, args.templates)
        failed = False
        if current != previous:
            previous = current
            refresh = args.refresh
            for document in documents:
                output = args.output / document.name if args.all and args.output else args.output
                try:
                    builder = Builder(args.project, document, output, args.modules,
                                      refresh, args.format, args.library, args.templates, args.template)
                    refresh = False
                    builder.build(args.entry, args.extract_only)
                except (subprocess.CalledProcessError, RuntimeError, ValueError, OSError) as error:
                    failed = True
                    print(f"Build failed ({document.name}): {error}", file=sys.stderr)
            args.refresh = False
        if not args.watch:
            return int(failed)
        time.sleep(0.5)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nStopped watching.")
