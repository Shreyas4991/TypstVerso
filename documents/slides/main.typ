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

#import "@preview/touying:0.7.4": *
#import themes.simple: *
#import "../../typst/lean.typ": lean-quote, lean-state, lean-command

#show: simple-theme.with(aspect-ratio: "16-9", footer: [Lean + Typst])
#set text(size: 20pt)

== A checked Lean declaration

#lean-quote("Demo.hello")

Hover over a name to inspect its type and documentation.

== A multiline proof

#lean-quote("Demo.identity_pair")

Hover over a bubble to inspect the proof state.

== A proof state

#lean-state("Demo.identity_pair", index: 2)

== A Lean command

#lean-command("#check Demo.identity_pair")

#lean-command("#eval (2 + 2)")
