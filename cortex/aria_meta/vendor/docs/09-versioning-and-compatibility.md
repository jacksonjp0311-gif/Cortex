# Versioning and Compatibility

ARIA versions three public contracts:

- **compiler version** in `VERSION`;
- **language specification version** in each source header;
- **container version** in `.ariac` byte zero after the magic.

Programs separately declare their own Semantic Version.

The alpha compiler accepts ARIA `0.1.x`. Future rules:

- patch releases clarify or fix behavior without changing accepted valid programs;
- minor releases add backward-compatible syntax or opcodes;
- major releases may change semantics or binary compatibility;
- container readers reject unknown major container versions;
- migrations must be explicit and testable.

`aria.lock.json` records the repository's expected compiler, spec, container, encoding, and compression contracts.
