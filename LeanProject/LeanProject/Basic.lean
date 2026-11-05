/-
Copyright 2026 Shreyas Srinivas

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-/

module

public import Mathlib

@[expose] public section

namespace Demo

/-- A small definition to quote from Typst. -/
def hello : String := "Hello from Lean!"

/-- A multiline proof with two branches and interactive proof states. -/
theorem identity_pair (p q : Prop) :
    (p → p) ∧ (q → q) := by
  constructor
  all_goals
    intro h
    exact h

/-- Swapping the order of two natural-number summands preserves their sum. -/
theorem addition_commutes (m n : Nat) : m + n = n + m := by
  induction n with
  | zero => simp
  | succ n ih => simp only [Nat.add_succ, Nat.succ_add, ih]

/-- Adding a natural number to itself gives an even number. -/
theorem double_is_even (n : Nat) : Even (n + n) := by
  exact ⟨n, rfl⟩

/-- Euclid's factorial-plus-one argument: primes have no upper bound. -/
theorem prime_above (n : Nat) : ∃ p, n ≤ p ∧ Nat.Prime p := by
  let p := (n.factorial + 1).minFac
  have hne : n.factorial + 1 ≠ 1 := by
    have hpos := Nat.factorial_pos n
    lia
  have hp : Nat.Prime p := Nat.minFac_prime hne
  refine ⟨p, ?_, hp⟩
  by_contra h
  have hsmall : p ≤ n := by lia
  have hfac : p ∣ n.factorial := Nat.dvd_factorial hp.pos hsmall
  have hnext : p ∣ n.factorial + 1 := Nat.minFac_dvd _
  have hone : p ∣ 1 := (Nat.dvd_add_iff_right hfac).mpr hnext
  exact hp.not_dvd_one hone

/-- Equivalently, the set of natural-number primes is infinite. -/
theorem infinitely_many_primes : {p : Nat | Nat.Prime p}.Infinite := by
  by_contra h
  have hfinite : {p : Nat | Nat.Prime p}.Finite := Set.not_infinite.mp h
  obtain ⟨bound, hbound⟩ := hfinite.bddAbove
  obtain ⟨p, hlarge, hp⟩ := prime_above (bound + 1)
  have hle : p ≤ bound := hbound hp
  lia

#check SimpleGraph

end Demo
