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
  *Abstract.* This sample article connects mathematical prose with checked Lean
  declarations. Code, intermediate goals, and command results all come from the
  same Lean project and inherit the article's font size.
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
