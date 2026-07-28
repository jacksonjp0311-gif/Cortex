# Deterministic Semantic Replay alpha.14

Alpha.14 proves continuity of meaning without repeating execution.

`aria replay create <request.json> --json` binds the handshake, repository
baseline, intent, interpretation, proposal, consent, policy, evidence, and
terminal semantic state into `aria.semantic-replay/1`.

Two replay records are compared in causal order. The verdict is either
`coherent` or `drift`, with the first exact divergent boundary:

```text
handshake → baseline → intent → interpretation → proposal
→ consent → policy → evidence → state
```

Replay mode is always `verify-only`. It cannot repeat an external effect,
activate a capability, or grant authority.
