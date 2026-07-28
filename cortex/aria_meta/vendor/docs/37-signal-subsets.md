# Signal Subsets alpha.26

```text
🜁 observe → 🜃 bound → 🜂 transmit → 🜄 retain → 🜍 attest → ∿ evolve
```

`aria.signal-subset/1` carries bounded operational evidence inside the existing
`aria.transmission/1` payload.

It records purpose, source, an explicit field allowlist, excluded field names,
source/emitted/limit counts, consent basis, scope, retention, selected items,
and a canonical SHA-256 digest.

```powershell
$subset=New-AriaSignalSubset `
  -Items $receipts `
  -Fields branch,coherence,durationMs,exitCode `
  -Purpose 'measure verified Git transport outcomes' `
  -Source 'github.push.receipts' `
  -ConsentBasis 'operator-approved repository telemetry' `
  -ConsentScope 'ARIA Git receipts only' `
  -Retention release `
  -Limit 32

$transmission=New-AriaSubsetTransmission -Subset $subset -Channel github -Status pass
```

A subset is evidence, never authority. It does not replace policy, capability,
human authorization, or intent verification. Raw stdout, stderr, credentials,
tokens, and unrelated user data remain excluded by default.