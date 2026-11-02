// A separate mechanism demo; the lecture slides and Lean sources are untouched.
#import "@preview/touying:0.7.4": *
#import themes.simple: *
#import "lean.typ": lean-quote, lean-command

#show: simple-theme.with(aspect-ratio: "16-9", footer: [Lean quotation demo])

== A declaration from Lec04.Basic

#lean-quote("hello")

The code above is extracted from the existing Lean module.
Hover over a name in the browser export to see its Lean signature.

== A command and its output

#lean-command("#check BinaryTree")

== Inspecting a declaration

#lean-command("#print BinaryTree", size: 14pt)
