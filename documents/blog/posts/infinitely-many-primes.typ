// Copyright 2026 Shreyas Srinivas
// SPDX-License-Identifier: Apache-2.0

#import "../../../typst/blog.typ": blog-date, blog-post, theorem, proof
#import "../../../typst/lean.typ": lean-quote

#let post = blog-post(title: [There are infinitely many primes], date: blog-date(2026, 11, 5))[
  _Note : This is a demo post_

  Here's a theorem that everyone knows.
  #theorem("Euclid")[
    There are infinitely many prime numbers.
  ]

  #proof[
    Suppose there were only finitely many primes, $p_1, dots, p_k$. The number
    $N = p_1 dots.c p_k + 1$ is greater than one, so it has a prime divisor $q$.
    None of the listed primes divides $N$: each leaves remainder one.
    Thus $q$ is a prime missing from the list, a contradiction.
  ]

  == The Lean formalization

  The formalization first constructs a prime $p ≥ n$ for any bound $n$.
  It takes $p$ to be the least prime factor of $n! + 1$. If $p ≤ n$, then $p$
  divides both $n!$ and $n! + 1$, so it divides $1$, contradicting its primality.

  #lean-quote("Demo.prime_above")

  Choosing the bound one greater than any proposed largest prime rules out
  a largest prime.

  Finally, `Demo.infinitely_many_primes` uses this construction to rule out
  a finite set of primes: a finite set would have an upper bound, and
  `Demo.prime_above` supplies a prime beyond it.

  #lean-quote("Demo.infinitely_many_primes")
]
