# ARIA Coreflow

Coreflow is the `0.3.0` executable language layer. It introduces typed values, expression trees, functions, lexical control flow, bounded iteration, module identity, and deterministic agent-dispatch events.

## Types

`Text`, `Number`, `Bool`, `Null`, and `Any` are the bootstrap scalar types. `Any` is an explicit escape hatch and should not be used where a narrower contract is possible.

## Evaluation

Expressions use the precedence order `not/negative`, multiplication/division, addition/subtraction, ordering, equality, `and`, then `or`. Function arguments evaluate left to right. The deterministic VM does not permit host-language expression evaluation.

## Scope

`let` defines a value in the current lexical scope. `set` mutates the nearest existing binding. Variables declared inside an `if`, `else`, or `repeat` block do not escape that block. A repeat iterator is a zero-based `Number` local to each iteration.

## Functions

Functions declare typed parameters and one return type. Non-`Null` functions must visibly return on every branch recognized by the bootstrap analyser. Calls are limited to 64 nested frames at runtime.

## Loops

`repeat` accepts an integer from 0 through 10,000. The semantic analyser rejects invalid literal bounds; the bytecode verifier and VM recheck the bound.

## Agent dispatch

`dispatch Architect <- "inspect graph"` emits a structured event after policy validation. It does not call an AI model or execute a process. A future ARIA Bridge may consume the event under separate capability and operator gates.
