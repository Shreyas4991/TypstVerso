// Copyright 2026 Shreyas Srinivas
// SPDX-License-Identifier: Apache-2.0

#import "../../../typst/blog.typ": blog-date, blog-post
#import "../../../typst/lean.typ": lean-quote

#let post = blog-post(title: [There are infinitely many primes], date: blog-date(2026, 11, 5))[
  _Note : This is a demo post_

  *Theorem (Euclid).* There are infinitely many prime numbers.

  Suppose there were only finitely many primes, $p_1, dots, p_k$. The number
  $N = p_1 dots.c p_k + 1$ is greater than one, so it has a prime divisor $q$.
  None of the listed primes divides $N$: each leaves remainder one.
  Thus $q$ is a prime missing from the list, a contradiction.

  == Primes have no upper bound

  We prove that for every natural-number bound $n$, there is a prime $p ≥ n$.
  Let $p$ be the least prime factor of $n! + 1$. If $p ≤ n$, then $p$ divides
  $n!$ as well as $n! + 1$, so it divides $1$, contradicting its primality.

  #lean-quote("Demo.prime_above")

  Choosing the bound one greater than any proposed largest prime rules out
  a largest prime.

  == The set of primes is infinite

  If the set of primes were finite, it would have an upper bound. Our previous
  theorem gives a prime beyond that bound, a contradiction:

  #lean-quote("Demo.infinitely_many_primes")
]
