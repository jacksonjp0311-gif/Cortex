# Algorithm: Capability Resolution

For capability `c = (name, effect, scope)`:

1. locate `effect` in repository policy;
2. reject if missing or denied;
3. for scoped filesystem effects, require a permitted policy root containing `scope`;
4. compile `REQUIRE_CAP name` into bytecode;
5. at runtime, repeat policy validation before activation;
6. when an effect opcode executes, select an active capability with the matching effect;
7. canonicalize workspace, scope root, and target path;
8. reject targets outside the workspace or scope.

This is a bootstrap approximation of an object-capability system. Future versions should use unforgeable capability values rather than names in an active set.
