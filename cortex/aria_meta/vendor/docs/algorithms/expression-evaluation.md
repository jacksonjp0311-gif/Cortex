# Typed Expression Evaluation

## Objective

Parse and execute expressions without evaluating ARIA source as PowerShell or another host language.

## Algorithm

1. Scan UTF-8 source into literals, identifiers, parentheses, commas, and a closed operator set.
2. Build an expression tree with recursive-descent precedence levels.
3. Resolve identifiers against lexical type scopes.
4. Resolve calls against the function signature table.
5. Annotate each node with an inferred scalar type.
6. Lower the tree in left-to-right postorder into stack instructions.
7. Independently replay the type stack in the bytecode verifier.
8. Recheck concrete runtime values in the VM.

## Invariants

- No host-language expression evaluator is invoked.
- Function arguments evaluate from left to right.
- Every operator has a closed input/output type contract.
- The compiler and verifier derive the same stack type result.
- Division by zero is a runtime fault with source-line provenance.
