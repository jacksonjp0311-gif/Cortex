# Operatorflow alpha.6

Operatorflow is ARIA's adaptive operator and provider membrane. It does not trust raw terminal text as executable truth. External systems report facts; ARIA normalizes those facts into a typed transmission, verifies a canonical SHA-256 digest, compresses the record into an `.ariat` container, and only then presents it to the operator or another machine.

## Runtime profiles

`Get-AriaRuntimeProfile` selects one deterministic mode:

- `operator` for a wide interactive terminal;
- `compact` for a narrow interactive terminal;
- `ci` when `CI=true`;
- `machine` when output is redirected or `ARIA_OUTPUT=json`.

`ARIA_ASCII=1` declares that a consumer needs ASCII-safe rendering. `ARIA_VERBOSE=1` preserves provider diagnostics for explicit debugging. Animations remain disabled in CI.

## Transmission membrane

The canonical envelope is `aria.transmission` version 1. It contains a channel, event kind, normalized status, source identity, payload, and digest. The digest covers the canonical body rather than provider-specific formatting.

`.ariat` containers use:

1. eight-byte `ARIAT001` magic;
2. a 32-byte SHA-256 digest;
3. a four-byte uncompressed payload length;
4. bounded gzip-compressed canonical JSON.

The reader rejects bad magic, invalid lengths, decompression expansion beyond the limit, body digest mismatch, and header digest mismatch.

## Commands

```powershell
.\aria.cmd profile
.\aria.cmd transmit .\examples\github-transmission.json
```

`profile` explains the selected runtime mode. `transmit` normalizes JSON input, writes a verified `.ariat` record under `.aria/transmissions`, reads it back through the independent container boundary, and renders it according to the active profile.

This is infrastructure for future GitHub, Git, native runtime, and model-provider adapters. Provider content remains data; it never becomes authority merely because it arrived through a trusted brand.