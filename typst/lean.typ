// Copyright 2026 Shreyas Srinivas
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// The discovery pass evaluates actual calls, including computed arguments.
// Quotation and state sizes default to 1em: the surrounding document controls them.
#let lean-discover = sys.inputs.at("lean-discover", default: "false") == "true"
#let lean-data = if lean-discover {
  (schemaVersion: 1, declarations: (:), commands: (), inlineCommands: ())
} else { json("lean.json") }

#let lean-request(request) = metadata((kind: "lean-request", request: request))
#let lean-build-fix = "If build.py is already running, wait about a minute for it to update the saved Lean results, then save this Typst file again. Check its terminal for errors.\n\nIf it is not running, open a terminal in the folder containing build.py and run:\n.venv/bin/python build.py --watch --all\n\nTo build once instead, run:\n.venv/bin/python build.py --all\n\nOn Windows, use .venv\\Scripts\\python.exe instead of .venv/bin/python."

#let lean-error(error, cause, fix) = assert(false, message:
  "Error: " + error + "\n\nProbable cause: " + cause + "\n\nProbable fix: " + fix)

#let lean-missing(request) = {
  let error = if request.kind == "declaration" {
    "The Lean definition or proof " + json.encode(request.name, pretty: false) + " is not ready to display."
  } else {
    let file = if request.module == none { "" } else { " Lean file: " + json.encode(request.module, pretty: false) + "." }
    "The Lean command " + json.encode(request.source, pretty: false) + " has no saved result yet." + file
  }
  lean-error(error,
    "build.py has not prepared this result yet. It may still be working, may have stopped after an error, or may not be running.",
    lean-build-fix)
}

#let lean-refresh() = lean-error(
  "The saved Lean results need to be updated.",
  "They were created by an older version of the template or do not contain the information this document needs.",
  lean-build-fix + "\n\nIf rebuilding does not help, run:\n.venv/bin/python build.py --all --refresh")

#let lean-hover(body, tooltip, kind: "token") = context {
  if tooltip == "" { body } else {
    let dimensions = measure(body)
    box[
      #metadata((
        kind: "lean-hover", role: kind, tooltip: tooltip,
        width: dimensions.width.pt(), height: dimensions.height.pt(),
      ))
      #body
    ]
  }
}

#let lean-color(kind) = {
  if kind == "keyword" or kind == "sort" { rgb("8959a8") }
  else if kind.starts-with("const") { rgb("245b96") }
  else if kind == "var" { rgb("744b21") }
  else if kind.starts-with("literal") { rgb("337653") }
  else if kind.contains("comment") { rgb("6a737d") }
  else { rgb("24292e") }
}

// Turn semantic fragments into lines without discarding token metadata.
#let lean-fragment-lines(fragments) = {
  let lines = ()
  let line = ()
  for part in fragments {
    if part.kind == "state" { line.push(part) }
    else {
      for (i, value) in part.text.split("\n").enumerate() {
        if i > 0 { lines.push(line); line = () }
        if value != "" { line.push((..part, text: value)) }
      }
    }
  }
  lines.push(line)
  lines
}

// Scale the leading spaces only; keep the semantic tokens and their hover data.
#let lean-indent-line(line, indent) = {
  if indent == 100% { line } else {
    let spaces = 0
    let leading = true
    let parts = ()
    for part in line {
      if leading and part.kind != "state" {
        let prefix = part.text.match(regex("^ *")).text
        spaces += prefix.len()
        let value = part.text.slice(prefix.len())
        if value != "" {
          leading = false
          parts.push((..part, text: value))
        }
      } else {
        leading = false
        parts.push(part)
      }
    }
    let spaces = int(calc.round(spaces * (indent / 100%)))
    if spaces > 0 { parts.insert(0, (kind: "text", text: " " * spaces, tooltip: "")) }
    parts
  }
}

#let lean-render(lines, size: 1em, states: true, indent: 100%, line-spacing: 0.5em) = {
  set text(size: size)
  show raw: set text(font: ("DejaVu Sans Mono", "Menlo"), size: 1em)
  stack(dir: ttb, spacing: line-spacing, ..lines.map(line => {
      let line = lean-indent-line(line, indent)
      box({
        if line.len() == 0 { raw(" ") }
        for part in line {
          if part.kind == "state" {
            if states {
              h(0.2em)
              lean-hover(
                box(
                  width: 0.75em, height: 0.28em, baseline: -0.14em,
                  radius: 0.14em, fill: none,
                  stroke: 0.65pt + rgb("89949f"),
                ),
                part.tooltip, kind: "state",
              )
            }
          } else {
            lean-hover(text(fill: lean-color(part.kind), raw(part.text)), part.tooltip)
          }
        }
      })
  }))
}

// Quote a declaration by its fully qualified Lean name.
// `first` and `last` are one-based, inclusive source line numbers within the quote.
#let lean-quote(name, size: 1em, states: true, first: 1, last: none, indent: 100%, line-spacing: 0.5em, blank-lines: true, comments: true) = {
  let request = (kind: "declaration", name: name)
  if lean-discover { return lean-request(request) }
  assert(type(indent) == ratio and indent >= 0%, message: "indent must be a nonnegative percentage, such as 50%")
  if lean-data.at("schemaVersion", default: none) != 1 { lean-refresh() }
  if name not in lean-data.declarations { lean-missing(request) }
  let lines = lean-data.declarations.at(name).lines
  let last = if last == none { lines.len() } else { last }
  assert(first >= 1 and last >= first and last <= lines.len(), message: "Invalid Lean quotation line range")
  let selected = lines.slice(first - 1, last)
  if not comments {
    selected = selected.map(line => line.filter(part => not part.kind.contains("comment")))
  }
  if not blank-lines {
    selected = selected.filter(line => line.any(part => part.kind == "state" or part.text.trim() != ""))
  }
  block(width: 100%, fill: rgb("f6f8fa"), radius: 5pt, inset: 12pt, clip: false,
    lean-render(selected, size: size, states: states, indent: indent, line-spacing: line-spacing))
}

// Render a saved or inline Lean command with Lean's actual output.
#let lean-command(code, module: none, occurrence: 1, output: true, size: 1em, output-size: none) = {
  let request = (kind: "command", source: code.trim(), module: module, occurrence: occurrence)
  if lean-discover { return lean-request(request) }
  if "commands" not in lean-data { lean-refresh() }
  let matches = lean-data.commands.filter(command => command.source.trim() == code.trim() and
    (module == none or command.module == module))
  if matches.len() == 0 {
    matches = lean-data.at("inlineCommands", default: ()).filter(command =>
      command.source.trim() == code.trim() and command.module == module)
  }
  if matches.len() == 0 { lean-missing(request) }
  let modules = ()
  for command in matches {
    if command.module not in modules { modules.push(command.module) }
  }
  assert(modules.len() == 1, message: "Command appears in several modules; specify module: with the Lean module name.")
  assert(occurrence >= 1 and occurrence <= matches.len(), message: "Lean command occurrence out of range: choose 1 to " + str(matches.len()) + ".")
  let command = matches.at(occurrence - 1)
  let panels = (block(width: 100%, fill: rgb("f6f8fa"), radius: 5pt, inset: 12pt,
    lean-render(command.lines, size: size)),)
  if output {
    for message in command.messages {
      let error = message.at("severity", default: "info") == "error"
      panels.push(block(width: 100%, fill: if error { rgb("fff1f0") } else { rgb("fafafa") }, inset: 10pt,
        stroke: (left: 1pt + if error { rgb("cf4545") } else { rgb("c4cbd2") }),
        lean-render(message.lines, size: if output-size == none { size } else { output-size }, states: false)))
    }
  }
  stack(dir: ttb, spacing: 0.4em, ..panels)
}

// Print a tactic state, or the declaration's type when there are no tactic states.
#let lean-state(name, index: 1, size: 1em) = {
  let request = (kind: "declaration", name: name)
  if lean-discover { return lean-request(request) }
  if lean-data.at("schemaVersion", default: none) != 1 { lean-refresh() }
  if name not in lean-data.declarations { lean-missing(request) }
  let declaration = lean-data.declarations.at(name)
  let states = declaration.lines.flatten().filter(p => p.kind == "state")
  let info = if states.len() > 0 {
    assert(index >= 1 and index <= states.len(), message: "Proof-state index out of range for " + name + ": choose an index from 1 to " + str(states.len()) + ".")
    if "fragments" not in states.at(index - 1) { lean-refresh() }
    states.at(index - 1).fragments
  } else {
    assert(index == 1, message: name + " has declaration type information only; use index: 1.")
    if "signatureFragments" in declaration {
      declaration.signatureFragments
    } else {
      // Older snapshots already carry the signature in the name's hover information.
      let names = declaration.lines.flatten().filter(p => p.at("definitionName", default: "") == name and "signatureFragments" in p)
      if names.len() == 0 { lean-refresh() }
      names.first().signatureFragments
    }
  }
  block(width: 100%, fill: rgb("eff6ff"), radius: 5pt, inset: 10pt,
    lean-render(lean-fragment-lines(info), size: size, states: false))
}

