// Copyright 2026 Shreyas Srinivas
// SPDX-License-Identifier: Apache-2.0

#import "../../../typst/blog.typ": blog-date, blog-post, theorem, proof
#import "../../../typst/lean.typ": lean-quote, lean-command

#let post = blog-post(title: [Swapping two summands], date: blog-date(2026, 10, 28))[
  _Note : This is a demo post_

  #theorem("Commutativity of addition")[
    For any natural numbers $m$ and $n$, we have $m + n = n + m$.
  ]

  This is the commutative law of addition: changing the order of the summands
  leaves their sum unchanged. For example, $3 + 5 = 5 + 3 = 8$.

  == The Lean formalization

  #proof[
    We prove the statement by induction on $n$. The zero case reduces to
    $m = m$. In the successor case, both sides reduce to the successor of
    the corresponding sum, so the induction hypothesis finishes the proof.
  ]

  #lean-quote("Demo.addition_commutes")

  We can also ask Lean to calculate a concrete example:

  #lean-command("#eval (3 + 5, 5 + 3)")
]
