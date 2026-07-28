# Portable Session Handoff alpha.15

Alpha.15 lets a different AI resume from a verified semantic boundary without
receiving the whole conversation.

`aria handoff create <request.json> --json` carries only typed references to
intent, interpretation, proposal, consent, evidence, or replay artifacts. Raw
prompts, secrets, credentials, private payloads, and unrelated history are
explicitly excluded.

The source and destination participants must differ. The handoff transfers
continuity, not consent, capability, trust, or authority.
