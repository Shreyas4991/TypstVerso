#import "../../typst/lean.typ": lean-quote, lean-state, lean-command

#set document(title: [An introduction to checked arguments], author: "Your Name")
#set page(paper: "iso-b5", margin: (x: 18mm, y: 20mm), numbering: "1")
#set text(size: 10pt)
#set par(justify: true)
#set heading(numbering: "1.1")
#show heading.where(level: 1): it => {
  pagebreak(weak: true)
  it
}

#page(numbering: none)[
  #align(center + horizon)[
    #text(size: 27pt, weight: "bold")[An introduction to\ LEAN-checked arguments]

    #v(1cm)
    A Lean + Typst sample book

    #v(1cm)
    Your Name
  ]
]

#outline(title: [Contents], indent: auto)

= From definitions to proofs

This book introduces a small checked argument. We first write down a proof,
then look at the steps Lean uses to check it.

== A first definition

Our starting point is a simple definition from the Lean project:

#lean-quote("Demo.hello")

Names carry their Lean types and documentation in the interactive export.

== A proof with two branches

For propositions $P$ and $Q$, we can prove $(P => P) and (Q => Q)$ by giving
one proof for each side of the conjunction.

#lean-quote("Demo.identity_pair")

The two branches follow the same argument. After introducing a hypothesis,
that hypothesis is already a proof of the required conclusion.

= Reading the proof interactively

== Intermediate goals

After `constructor`, Lean asks for both implications:

#lean-state("Demo.identity_pair", index: 2)

Hover over the proof-state bubbles in the previous chapter to follow the
transition from these goals to a completed proof.

== Asking Lean questions

We can check the theorem's type without duplicating its statement:

#lean-command("#check Demo.identity_pair")

Lean can also calculate the value of an expression:

#lean-command("#eval (2 + 2)")


The result is 4, as expected.

== Simple Graphs

Here's a simple graph in mathlib

#lean-command("#print SimpleGraph")

Here's the type of the function that gets its neighbor set for a given vertex `v`

#lean-command("#check SimpleGraph.neighborSet")

#lean-command("#check Nat")