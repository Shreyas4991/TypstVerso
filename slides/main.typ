#import "@preview/touying:0.7.4": *
#import themes.simple: *
#import "lean.typ": lean-quote, lean-state, lean-command

#show: simple-theme.with(
  aspect-ratio: "16-9",
  footer: [Simple slides],
)

#title-slide[
  = What is Lean : Why Trust It?
  Trust is a complicated business
  #v(2em)

  Sebastian Brandt #footnote[CISPA] <cispa> #h(1em)
  Henrik Lievonen #footnote(<cispa>) #h(1em)
  Shreyas Srinivas #footnote[MPI SWS] #h(1em)
  Chiara Piombi #footnote(<cispa>) #h(1em)

  Nov 4, 2026
]

== Hi I'm Shreyas

#focus-slide[
#set align(left)
== First Some Organisational Matters

- Last Lecture of Part I

- Next Module : Algorithms - Functional Correctness

- Deadline for CMS registration : Nov 13, 2026

- No lecture next week.

Registration on #link("https://lsf.uni-saarland.de")[HISPOS] is different.
]

= A Lean Recap

== Lean: The Programming Language (PL)

When learning a PL, one must ask two questions:

#only(1)[
- How to construct data
- How to process data
]

#only(2)[
  - How to construct data
    - `inductive` types
    - `structure`s
]



#only(3)[
  - How to process data
    - `def`s
  #lean-quote("incr")
    - `theorem`s (How ???)

]

== Inductive Types

For e.g:
#lean-quote("BinaryTree")

== Declarations
  #lean-quote("incr")
  #lean-command("#check incr")


== Propositions
  #lean-quote("isEven")



== Theorems : A special kind of definition

#lean-state("isEven_iff")


== Theorems : Term based proofs

#lean-quote("isEven_iff")


== Theorems : Simple Tactic Proofs
#lean-quote("isEven_iff_with_tactics")




== Theorems : Tacticals (or) Tactic Combinators
  #lean-quote("isEven_iff_with_tactics₂")


= About Lean : What's actually happening

== Lean's Abstract Expression Type

#text(size: 20pt)[#lean-quote("Lean.Expr", first: 1, last : 36)]

= Trust Issues

== Example 1 : What a spec

== Example 2 : What a spec

== Example 3 : What an instance

Typeclass Synthesis Being Weird

==
