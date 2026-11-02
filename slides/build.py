#!/usr/bin/env python3
"""Extract checked Lean quotations, then export a Typst deck to PDF and offline HTML."""
import argparse
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

SLIDES = Path(__file__).resolve().parent
PROJECT = SLIDES.parent / "Lec04"
BUILD = SLIDES / "build"


def run(args, cwd=SLIDES, capture=False, env=None):
    return subprocess.run([str(a) for a in args], cwd=cwd, check=True,
                          text=True, stdout=subprocess.PIPE if capture else None, env=env).stdout


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


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


def prepare_subverso():
    """Apply the checked-in highlighter fix without changing the pinned dependency."""
    package = PROJECT / ".lake/packages/subverso"
    patch = PROJECT / "subverso.patch"
    if not package.is_dir():
        raise RuntimeError("Fetch the Lean dependencies first: run lake update in Lec04/")
    # An already-applied patch is expected, including when a watcher rebuilds.
    applied = subprocess.run(["git", "apply", "--reverse", "--check", str(patch)],
                             cwd=package, capture_output=True, text=True)
    if applied.returncode == 0:
        return
    check = subprocess.run(["git", "apply", "--check", str(patch)],
                           cwd=package, capture_output=True, text=True)
    if check.returncode:
        raise RuntimeError("Cannot apply Lec04/subverso.patch to this SubVerso checkout: " + check.stderr.strip())
    run(["git", "apply", patch], cwd=package)


def extract():
    config = json.loads((SLIDES / "lean/config.json").read_text())
    modules = config["modules"]
    if not modules or any(not re.fullmatch(r"[A-Za-z_][\w'.]*(?:\.[\w']+)*", m) for m in modules):
        raise ValueError("lean/config.json must contain a nonempty list of Lean module names")
    prepare_subverso()
    run(["lake", "build", "subverso-extract-mod", "+SubVerso.Signature", *["+" + m for m in modules]], cwd=PROJECT)
    # Native helper executables cannot locate the toolchain sources relative to
    # their own package bin directory. Supply Lean's actual toolchain root.
    sysroot = run(["lake", "env", "lean", "--print-prefix"], cwd=PROJECT, capture=True).strip()
    lean_env = {**os.environ, "LEAN_SYSROOT": sysroot}
    declarations = {}
    commands = []

    def extract_module(module, requested=()):
        raw = BUILD / (module + ".subverso.json")
        decoded = BUILD / (module + ".decoded.json")
        run(["lake", "exe", "subverso-extract-mod", module, raw], cwd=PROJECT, env=lean_env)
        run(["lake", "env", "lean", "--run", "ExportSlides.lean", raw, decoded, *requested], cwd=PROJECT, env=lean_env)
        data = json.loads(decoded.read_text())
        for command in data["commands"]:
            commands.append({"module": module, "source": command["source"].strip(),
                             "lines": quote_lines(command["fragments"]),
                             "messages": [{**message, "lines": quote_lines(message["fragments"])}
                                          for message in command["messages"]]})
        for name, declaration in data["declarations"].items():
            if name in declarations:
                raise ValueError("Duplicate declaration: " + name)
            declarations[name] = {"module": module, "source": declaration["source"],
                                  "signature": declaration["signature"],
                                  "signatureFragments": declaration["signatureFragments"],
                                  "lines": quote_lines(declaration["fragments"])}

    for module in modules:
        extract_module(module)

    requested = set(config.get("declarations", []))
    # Literal quotes are discoverable even before a missing declaration lets the
    # Typst file compile. Computed names can be listed explicitly in config.json.
    for source in SLIDES.rglob("*.typ"):
        if BUILD in source.parents or ".venv" in source.parts:
            continue
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", source.read_text(), flags=re.S)
        for match in re.finditer(r'\blean-(?:quote|state)\s*\(\s*("(?:[^"\\]|\\.)*")', code):
            requested.add(json.loads(match.group(1)))
    missing = sorted(requested - declarations.keys())
    if missing:
        request = BUILD / "requested-declarations.json"
        resolved = BUILD / "resolved-declarations.json"
        write_json(request, {"modules": modules, "declarations": missing})
        run(["lake", "env", "lean", "--run", "ResolveSlides.lean", request, resolved], cwd=PROJECT, env=lean_env)
        groups = {}
        for name, module in json.loads(resolved.read_text()).items():
            groups.setdefault(module, []).append(name)
        for module, names in groups.items():
            extract_module(module, names)
        unresolved = sorted(set(missing) - declarations.keys())
        if unresolved:
            raise RuntimeError("Could not extract the defining source of: " + ", ".join(unresolved))
    write_json(SLIDES / "lean/snippets.json", {"schemaVersion": 1, "declarations": declarations,
                                             "commands": commands})
    print(f"Extracted {len(declarations)} declarations and {len(commands)} commands.", flush=True)


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


def export(entry):
    if not entry.is_file() or not entry.is_relative_to(SLIDES):
        raise ValueError("The Typst entry file must be inside slides/")
    stem = entry.stem
    with tempfile.TemporaryDirectory(prefix="export-", dir=BUILD) as temporary:
        directory = Path(temporary)
        run(["typst", "compile", "--root", SLIDES, entry, directory / "slides.pdf"])
        run(["typst", "compile", "--root", SLIDES, "--format", "svg", entry,
             directory / "slide-{n}.svg"])
        expression = '''query(metadata).filter(item => type(item.value) == dictionary and
          item.value.at("kind", default: "") == "lean-hover").map(item => {
          let p = item.location().position()
          (page: p.page, x: p.x.pt(), y: p.y.pt(), ..item.value)
        })'''
        regions = json.loads(run(["typst", "eval", expression, "--root", SLIDES,
                                  "--in", entry], capture=True))
        pages = []
        svgs = sorted(directory.glob("slide-*.svg"), key=lambda p: int(p.stem.split("-")[-1]))
        for number, svg in enumerate(svgs, 1):
            markup = svg.read_text()
            width, height = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', markup).groups()
            pages.append({"svg": markup, "width": float(width), "height": float(height),
                          "regions": [r for r in regions if r["page"] == number]})
        template = (SLIDES / "player.html").read_text()
        # Data lives in a JSON script element; escape '<' so Lean docs cannot end that element.
        payload = json.dumps(pages, ensure_ascii=False).replace("<", "\\u003c")
        document = template.replace("__SLIDE_DATA__", payload).replace("__TITLE__", html.escape(stem))
        (directory / "slides.html").write_text(document)
        annotate_pdf(directory / "slides.pdf", directory / "annotated.pdf", regions)
        (directory / "slides.html").replace(BUILD / (stem + ".html"))
        (directory / "annotated.pdf").replace(BUILD / (stem + ".pdf"))
        write_json(BUILD / (stem + ".regions.json"), regions)
        print(f"Built {len(pages)} slides, {len(regions)} Lean hover regions: build/{stem}.pdf and build/{stem}.html", flush=True)


def inputs():
    paths = [PROJECT / "lakefile.toml", PROJECT / "lake-manifest.json", PROJECT / "lean-toolchain",
             PROJECT / "ExportSlides.lean", PROJECT / "ResolveSlides.lean", PROJECT / "subverso.patch",
             SLIDES / "lean/config.json", SLIDES / "player.html"]
    paths += list((PROJECT / "Lec04").rglob("*.lean"))
    paths += list(PROJECT.glob("*.lean"))
    paths += [p for p in SLIDES.rglob("*.typ") if BUILD not in p.parents and ".venv" not in p.parts]
    return [(str(p), p.stat().st_mtime_ns) for p in sorted(set(paths)) if p.exists()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entry", nargs="?", default="main.typ")
    parser.add_argument("--extract-only", action="store_true")
    parser.add_argument("--watch", action="store_true", help="Rebuild when Lean or Typst sources change")
    args = parser.parse_args()
    BUILD.mkdir(exist_ok=True)
    loaded_script = Path(__file__).stat().st_mtime_ns
    previous = None
    while True:
        if args.watch and Path(__file__).stat().st_mtime_ns != loaded_script:
            os.execv(sys.executable, [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]])
        current = inputs()
        if current != previous:
            previous = current
            try:
                extract()
                if not args.extract_only:
                    export((SLIDES / args.entry).resolve())
            except (subprocess.CalledProcessError, RuntimeError, ValueError, OSError) as error:
                print(f"Build failed: {error}", file=sys.stderr)
                if not args.watch:
                    return 1
        if not args.watch:
            return 0
        time.sleep(0.5)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
