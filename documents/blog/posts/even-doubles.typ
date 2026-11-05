// Copyright 2026 Shreyas Srinivas
// SPDX-License-Identifier: Apache-2.0

#import "../../../typst/blog.typ": blog-date, blog-post, theorem, proof
#import "../../../typst/lean.typ": lean-quote, lean-state

#let post = blog-post(title: [Every double is even], date: blog-date(2026, 11, 2))[
  _Note : This is a demo post_

  #theorem[
    For every natural number $n$, the number $n + n$ is even.
  ]

  #proof[
    By definition, a number is even if it can be written as $k + k$ for some
    natural number $k$. Choose $k = n$ and the required equality is immediate.
  ]

  == A witness and an equality

  In Lean, `Even (n + n)` asks us to supply that witness and its equality.
  The pair below chooses `n`; `rfl` proves the equality by reflexivity:

  #lean-quote("Demo.double_is_even")

  Here is the goal before we give Lean the witness:

  #lean-state("Demo.double_is_even", index: 1)
]
