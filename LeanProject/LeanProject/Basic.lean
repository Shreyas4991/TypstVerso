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

#check SimpleGraph

end Demo
