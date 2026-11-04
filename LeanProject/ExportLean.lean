/-
Copyright 2026 Shreyas Srinivas

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-/

import SubVerso.Module
import SubVerso.Signature

/- Decode with SubVerso's own API: its wire format is deliberately private.
   Only the small, versioned schema below is consumed by Typst. -/
open Lean SubVerso.Highlighting

def tokenInfo (kind : Token.Kind) : String × String :=
  match kind with
  | .const _ signature docs .. | .anonCtor _ signature docs .. =>
    (kind.cssClass, signature ++ (docs.map ("\n\n" ++ ·)).getD "")
  | .var _ type .. | .wildcard type .. | .withType type => (kind.cssClass, type)
  | .keyword _ _ docs | .delim _ _ docs | .operator _ _ docs
  | .bracket _ _ docs | .separator _ _ docs | .option _ _ docs =>
    (kind.cssClass, docs.getD "")
  | .sort docs => (kind.cssClass, docs.getD "")
  | .num type .. => (kind.cssClass, type.getD "")
  | _ => (kind.cssClass, "")

/-- Read the elaborated signature at the declaration's definition site. -/
partial def declarationSignature (name : Name) : Highlighted → Option String
  | .token ⟨.const n signature _ true .., _⟩ =>
    if n == name then some signature else none
  | .seq xs => xs.findSome? (declarationSignature name)
  | .span _ content | .tactics _ _ _ content => declarationSignature name content
  | _ => none

/-- Re-elaborate the signature to retain semantic tokens, including inferred result types. -/
def highlightSignature (env : Environment) (signature : String) : IO Highlighted := do
  let ictx := Parser.mkInputContext signature "<slide-signature>"
  let parser := Parser.andthen Parser.Command.declId Parser.Command.declSig
  let parse := Parser.andthenFn Parser.whitespace parser.fn
  let parsed := parse.run ictx { env, options := {} } (Parser.getTokenTable env)
    (Parser.mkParserState signature)
  if parsed.hasError then throw <| IO.userError (parsed.toErrorMsg ictx)
  let name := parsed.stxStack.pop.back
  let sig := parsed.stxStack.back
  let state ← IO.mkRef ({
    commandState := Elab.Command.mkState env
    parserState := {}
    cmdPos := parsed.pos
  } : Elab.Frontend.State)
  Elab.Frontend.runCommandElabM (SubVerso.Compat.commandWithoutAsync do
    Elab.withEnableInfoTree (m := Elab.Command.CommandElabM) true do
      let (code, _, _, _) ← SubVerso.Examples.checkSignature ⟨name⟩ ⟨sig⟩
      return code) { inputCtx := ictx } state

/-- Locate source declaration signatures, retaining their whitespace and universe binders. -/
partial def sourceSignatures (name : Name) (source : String) (stx : Syntax) : Array String := Id.run do
  let args := stx.getArgs
  let mut signatures := #[]
  if let some declId := args.find? (·.getKind == ``Parser.Command.declId) then
    if let some sig := args.find? (fun s => s.getKind == ``Parser.Command.declSig ||
        s.getKind == ``Parser.Command.optDeclSig) then
      let id := declId[0]
      let sourceName := id.getId.toString
      if name == id.getId || name.toString.endsWith ("." ++ sourceName) then
        if let some start := id.getTailPos? then
          if let some stop := sig.getTailPos? then
            signatures := signatures.push (name.toString ++ SubVerso.Compat.String.Pos.extract source start stop)
  for arg in args do
    signatures := signatures ++ sourceSignatures name source arg
  return signatures

/-- Preserve the highlighted hypotheses and conclusions instead of flattening to a string. -/
def goalsCode (goals : Array (Highlighted.Goal Highlighted)) : Highlighted := Id.run do
  if goals.isEmpty then return .text "No goals"
  let mut code : Highlighted := .empty
  let mut firstGoal := true
  for goal in goals do
    if !firstGoal then code := code ++ .text "\n\n"
    firstGoal := false
    if let some name := goal.name then
      code := code ++ .token ⟨.keyword none none none, "case"⟩ ++ .text (" " ++ name ++ "\n")
    for h in goal.hypotheses do
      let mut firstName := true
      for token in h.names do
        if !firstName then code := code ++ .text " "
        firstName := false
        code := code ++ .token token
      code := code ++ .text " : " ++ h.typeAndVal ++ .text "\n"
    code := code ++ .text goal.goalPrefix ++ goal.conclusion
  return code

partial def fragments (code : Highlighted) : Array Json := Id.run do
  match code with
  | .token tok =>
    let (kind, tooltip) := tokenInfo tok.kind
    let mut fields := [("kind", toJson kind), ("text", toJson tok.content),
      ("tooltip", toJson tooltip)]
    if let .const name _ _ true .. := tok.kind then
      fields := fields ++ [("definitionName", toJson name.toString)]
    return #[Json.mkObj fields]
  | .text s | .unparsed s =>
    return #[Json.mkObj [("kind", "text"), ("text", toJson s), ("tooltip", "")]]
  | .seq xs => return xs.foldl (fun acc x => acc ++ fragments x) #[]
  | .span _ content => return fragments content
  | .point .. => return #[]
  | .tactics goals start stop content =>
    let state := if goals.isEmpty then "No goals" else
      "\n\n".intercalate (goals.toList.map (·.toString))
    return fragments content |>.push (Json.mkObj [
      ("kind", "state"), ("text", ""), ("tooltip", toJson state),
      ("fragments", toJson (fragments (goalsCode goals))),
      ("startByte", toJson start), ("endByte", toJson stop)])

/-- Keep semantic tokens in Lean's actual command output. -/
partial def messageCode : Highlighted.MessageContents Highlighted → Highlighted
  | .text text => .text text
  | .term code => code
  | .goal goal => goalsCode #[goal]
  | .append messages => .seq (messages.map messageCode)
  | .trace cls message children collapsed =>
    let header := Highlighted.text s!"[{cls}] " ++ messageCode message
    if collapsed then header ++ .text "\n"
    else children.foldl (fun code child => code ++ .text "\n  " ++ (messageCode child).indent 2) header

def messageJson (severity : Highlighted.Span.Kind)
    (message : Highlighted.MessageContents Highlighted) : Json :=
  Json.mkObj [("severity", toJson severity.toString), ("text", toJson message.toString),
    ("fragments", toJson (fragments (messageCode message)))]

partial def commandMessages : Highlighted → Array Json
  | .span messages code => messages.map (fun (severity, message) => messageJson severity message) ++ commandMessages code
  | .point severity message => #[messageJson severity message]
  | .seq codes => codes.foldl (fun messages code => messages ++ commandMessages code) #[]
  | .tactics _ _ _ code => commandMessages code
  | _ => #[]

/-- Stream interchange keeps intermediate JSON out of the document project. -/
def readPayload (path : String) : IO String := do
  if path == "-" then (← IO.getStdin).readToEnd else IO.FS.readFile path

def writePayload (path value : String) : IO Unit := do
  if path == "-" then (← IO.getStdout).putStrLn value else IO.FS.writeFile path (value ++ "\n")

/-- Resolve only the declarations requested by the document. -/
unsafe def resolveDeclarations : IO Unit := do
  let request ← IO.ofExcept <| Json.parse (← readPayload "-")
  let modules ← IO.ofExcept <| request.getObjValAs? (Array String) "modules"
  let names ← IO.ofExcept <| request.getObjValAs? (Array String) "declarations"
  initSearchPath (← findSysroot)
  enableInitializersExecution
  let env ← SubVerso.Compat.importModules (modules.map fun name => { module := name.toName }) {}
  let mut resolved := #[]
  for name in names do
    let some index := env.getModuleIdxFor? name.toName
      | throw <| IO.userError s!"Declaration '{name}' is not available from the imported Lean files. Check its full name and the imports in LeanProject.lean. If its file starts with 'module', add '@[expose] public section' before the definitions you want to use in documents."
    resolved := resolved.push (name, Json.str env.header.moduleNames[index.toNat]!.toString)
  writePayload "-" (Json.mkObj resolved.toList).compress

/-- Evaluate inline slide commands in imported environments, without editing source modules. -/
unsafe def exportInlineCommands (input output : String) : IO Unit := do
  let request ← IO.ofExcept <| Json.parse (← readPayload input)
  let modules ← IO.ofExcept <| request.getObjValAs? (Array String) "modules"
  let commands ← IO.ofExcept <| request.getObjValAs? (Array Json) "commands"
  initSearchPath (← findSysroot)
  enableInitializersExecution
  let defaultEnv ← SubVerso.Compat.importModules
    (modules.map fun name => { module := name.toName }) {}
  let mut environments : Std.HashMap String Environment := {}
  let mut exported := #[]
  for command in commands do
    let source ← IO.ofExcept <| command.getObjValAs? String "source"
    let selected := (command.getObjValAs? String "module").toOption
    let env ← match selected with
      | none => pure defaultEnv
      | some name =>
        if let some env := environments[name]? then pure env
        else
          -- Command evaluation can disable initializer execution globally.
          enableInitializersExecution
          let env ← SubVerso.Compat.importModules #[{ module := name.toName }] {}
          environments := environments.insert name env
          pure env
    let ictx := Parser.mkInputContext source "<slide-command>"
    let (header, parserState, messages) ← Parser.parseHeader ictx
    let state ← IO.mkRef ({
      commandState := { Elab.Command.mkState env with messages }
      parserState
      cmdPos := parserState.pos
    } : Elab.Frontend.State)
    let context : Elab.Frontend.Context := { inputCtx := ictx }
    let result ← SubVerso.Compat.Frontend.processCommands header context state
    let result := result.updateLeading source
    let codes ← Elab.Frontend.runCommandElabM
      (Elab.Command.liftTermElabM <| highlightFrontendResult result) context state
    let code := Highlighted.seq codes
    let messages := commandMessages code
    if code.hasError then
      IO.eprintln s!"Lean reported an error in inline command: {source}"
      for message in messages do
        if (message.getObjValAs? String "severity").toOption == some "error" then
          IO.eprintln ((message.getObjValAs? String "text").toOption.getD "")
    exported := exported.push <| Json.mkObj [
      ("module", toJson selected), ("source", toJson source),
      ("fragments", toJson (fragments code)), ("messages", toJson messages)]
  writePayload output (toJson exported).compress

unsafe def main (args : List String) : IO Unit := do
  if args == ["--resolve"] then
    resolveDeclarations
    return
  if args == ["--commands"] then
    exportInlineCommands "-" "-"
    return
  if let ["--commands", input, output] := args then
    exportInlineCommands input output
    return
  let (input, output, requested, moduleName) ← match args with
    | "--decode" :: moduleName :: requested => pure ("-", "-", requested, moduleName)
    | input :: output :: requested => pure (input, output, requested,
        ((input : System.FilePath).fileName.getD "").replace ".subverso.json" "")
    | _ => throw <| IO.userError "Usage: ExportLean.lean --resolve | --commands | --decode MODULE [DECLARATIONS...] (JSON on stdin/stdout)"
  let raw ← readPayload input
  let mod : SubVerso.Module.Module ← IO.ofExcept <| Json.parse raw >>= fromJson?
  initSearchPath (← findSysroot)
  enableInitializersExecution
  let env ← SubVerso.Compat.importModules #[{ module := moduleName.toName }] {}
  let paths ← SubVerso.Compat.initSrcSearchPath
  let root ← findSysroot
  let paths : SearchPath := (paths : List System.FilePath) ++
    [root / "src" / "lean" / "lake", root / "src" / "lean", ("." : System.FilePath)]
  let some sourceFile ← paths.findModuleWithExt "lean" moduleName.toName
    | throw <| IO.userError s!"Source for {moduleName} was not found on Lean's source search path"
  let sourceText ← IO.FS.readFile sourceFile
  let fileMap := FileMap.ofString sourceText
  let mut declarations := #[]
  let mut commands : Array Json := #[]
  for item in mod.items do
    if !requested.isEmpty && !item.defines.any (fun name => requested.contains name.toString) then continue
    if item.code.hasError then
      throw <| IO.userError s!"Lean errors in extracted command: {item.code.toString}"
    let source := match item.range with
      | some (start, stop) => SubVerso.Compat.String.Pos.extract sourceText
          (fileMap.ofPosition start) (fileMap.ofPosition stop)
      | none => item.code.toString
    if (SubVerso.Compat.String.trimLeft source).startsWith "#" then
      commands := commands.push (Json.mkObj [("source", toJson source),
        ("fragments", toJson (fragments item.code)), ("messages", toJson (commandMessages item.code))])
    if item.defines.isEmpty then continue
    let code := fragments item.code
    for name in item.defines do
      if !requested.isEmpty && !requested.contains name.toString then continue
      let some signature := declarationSignature name item.code
        | throw <| IO.userError s!"No elaborated signature found for {name}"
      -- Prefer the checked source: pretty-printing can omit type annotations
      -- needed to reconstruct coercions and overloaded notation faithfully.
      let mut sourceSignatureCode : Option Highlighted := none
      let source := item.code.toString
      if let .ok stx := Parser.runParserCategory env `command source then
        for formatted in sourceSignatures name source stx do
          try
            sourceSignatureCode := some (← highlightSignature env formatted)
            break
          catch _ =>
            -- Inferred result types and locally scoped notation may require the
            -- elaborated signature rather than a standalone source signature.
            pure ()
      let signatureCode ← match sourceSignatureCode with
        | some code => pure code
        | none => highlightSignature env signature
      let signatureTokens := fragments signatureCode
      -- Keep this on the name token as well, for already-running extraction watchers.
      let code := code.map fun token =>
        if (token.getObjValAs? String "definitionName").toOption == some name.toString then
          token.setObjVal! "signatureFragments" (toJson signatureTokens)
        else token
      declarations := declarations.push (name.toString, Json.mkObj [
        ("source", toJson item.code.toString), ("signature", toJson signature),
        ("signatureFragments", toJson signatureTokens),
        ("fragments", toJson code)])
  let json := Json.mkObj [("schemaVersion", toJson (1 : Nat)),
    ("declarations", Json.mkObj declarations.toList), ("commands", toJson commands)]
  writePayload output json.compress
