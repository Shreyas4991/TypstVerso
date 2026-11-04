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

#import "../../typst/lean.typ": lean-quote, lean-state, lean-command

#set document(title: "A small checked argument", author: "Your Name")
#set page(paper: "a4", margin: (x: 24mm, y: 22mm), numbering: "1")
#set text(size: 11pt)
#set par(justify: true)
#set heading(numbering: "1.")

#align(center)[
  #text(size: 22pt, weight: "bold")[A small checked argument]

  Your Name
]

#block(inset: (x: 12pt), width: 100%)[
  *Abstract.* We prove that every proposition implies itself. A Lean proof and
  its intermediate goals show how the argument works, one step at a time.
]

= A definition

We begin with a small definition. The browser export lets the reader inspect
its type and documentation directly from the highlighted name.

#lean-quote("Demo.hello")

= A checked proof

For arbitrary propositions $P$ and $Q$, each proposition implies itself.
We prove both implications together by constructing a conjunction.

#lean-quote("Demo.identity_pair")

The tactic `constructor` creates two goals. The `all_goals` block introduces
the hypothesis in each branch and then uses it to finish the proof.

= Inspecting the goals

The state after `constructor` makes the two branches explicit:

#lean-state("Demo.identity_pair", index: 2)

Proof-state bubbles in the quotation provide the remaining intermediate states.

= Checking the result

Lean reports the theorem's type and evaluates a small expression:

#lean-command("#check Demo.identity_pair")

#lean-command("#eval (2 + 2)")
