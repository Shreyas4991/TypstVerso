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
