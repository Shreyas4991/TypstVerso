#import "../../typst/lean.typ": lean-quote, lean-state, lean-command

#set document(title: "An introduction to checked arguments", author: "Your Name")
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
    #text(size: 27pt, weight: "bold")[An introduction to checked arguments]

    #v(1cm)
    A Lean + Typst sample book

    #v(1cm)
    Your Name
  ]
]

#outline(title: [Contents], indent: auto)

= From definitions to proofs

This book introduces a small checked argument, then returns to the proof to
inspect its intermediate goals. The HTML edition presents the pages in a
scrolling reader; the PDF edition retains the book's typeset layout.

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

Evaluation also uses the imported Lean environment:

#lean-command("#eval (2 + 2)")

These quotations and command results share the same extraction cache as the
article and slide examples.
