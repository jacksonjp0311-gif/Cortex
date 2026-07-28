# Structured Control Verification

ARIA alpha bytecode uses nested instruction sequences rather than arbitrary numeric jumps.

## IF

1. Pop and require a `Bool` condition.
2. Verify `then` and `else` using copies of the current variable and capability tables.
3. Require each child sequence to finish with an empty operand stack.
4. Keep branch-local declarations and capability activation from leaking outward.

## REPEAT

1. Pop and require a `Number` count.
2. Add a child `Number` iterator binding.
3. Verify the body as a nested instruction sequence.
4. Enforce a runtime integral range of 0 through 10,000.
5. Create and remove a fresh lexical scope for every iteration.

## Termination

`RETURN` terminates a function sequence and validates its stack value against the function contract. `HALT` terminates only the entry flow. Instructions after visible termination are rejected.
