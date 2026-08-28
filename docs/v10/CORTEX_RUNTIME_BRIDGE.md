# Cortex Runtime Bridge

The bridge is the only runtime component permitted to translate between the
agent loop and durable Cortex state.

At start it calls the existing symbiotic-session path, which projects current
epoch, governed memory, evidence digests, operating regime, confidence, and
constitutional restrictions. The model receives a bounded projection and its
hash, not unrestricted database access.

At completion the bridge appends one `native_agent_trajectory` to the existing
immutable symbiotic chain. Verification reloads the canonical receipt and
checks content identity, ordered event hashes, request/response binding,
tool-call/result pairing, context/session/epoch binding, final-answer binding,
closed authority flags, and ledger-chain validity.

The bridge does not admit memory, distill competence, declare an outcome,
create a witness, or infer task success. Those remain explicit downstream
evidence operations.
