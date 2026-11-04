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

#check SimpleGraph

end Demo
