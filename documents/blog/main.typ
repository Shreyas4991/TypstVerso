// Copyright 2026 Shreyas Srinivas
// SPDX-License-Identifier: Apache-2.0

#import "../../typst/blog.typ": blog
#import "posts/addition.typ" as addition
#import "posts/even-doubles.typ" as even-doubles
#import "posts/infinitely-many-primes.typ" as infinitely-many-primes

// Add imported posts here in any order. Their dates determine the reading order.
#blog((
  addition.post,
  even-doubles.post,
  infinitely-many-primes.post,
))
