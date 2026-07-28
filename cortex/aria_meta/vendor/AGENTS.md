# ARIA Agent Bootstrap

ARIA is a repository-native language, compiler, verifier, bytecode container, and local virtual machine.

## Start here

From the repository root, run:

```powershell
.\aria.cmd handshake --json
.\aria.cmd begin --json
.\aria.cmd doctor -Strict
.\aria.cmd test
```

A healthy baseline must report:

- repository manifest integrity
- `SYSTEM READY`
- `500/500` aggregate conformance with zero failures

## Authoritative entrypoints

- `aria.cmd` — canonical Windows command
- `aria.ps1` — command dispatcher
- `ARIA-RUNTIME.json` — machine-readable repository map
- `ARIA-CONNECT.json` — canonical model-neutral connection contract
- `src/Aria.AgentHandshake.psm1` — deterministic discovery and synchronization record
- `src/Aria.SemanticContinuity.psm1` — replay, handoff, provider membrane, and cooperative mesh
- `src/Aria.Gate.psm1` — compiler gate
- `src/Aria.Parser.psm1` — parser
- `src/Aria.Semantics.psm1` — semantic analysis
- `src/Aria.Bytecode.psm1` — bytecode and container
- `src/Aria.VM.psm1` — local virtual machine
- `src/Aria.SourceCore.psm1` — source-language core
- `src/Aria.Effects.psm1` — whole-program effect graph and purity proof
- `src/Aria.IntentVerifier.psm1` — intent obligations and artifact-derived program summaries
- `src/Aria.SemanticProjection.psm1` — deterministic state-to-cue projections
- `src/Aria.EventSpine.psm1` — cross-session hash-chained event and operation history
- `grammar/semantic-cues.json` — content-addressed human/machine cue contracts
- `grammar/alchemy.json` — executable triadic glyph syntax
- `tests/Run-Tests.ps1` — conformance lattice

- `src/Aria.ExecutionEvidence.psm1` — per-card observational execution receipts

## Semantic synchronization

`.\aria.cmd handshake --json` is the first machine action. It binds the
connection contract, runtime map, this guide, manifest state, shared
vocabulary, and next valid boundary into one deterministic record.

Follow its phases in order:

```text
discover → orient → verify → align → propose
```

Handshake success grants no authority. Do not infer consent, capability,
correctness, or permission from discovery. A proposal remains non-authoritative
until the independent human, capability, policy, and execution boundaries admit
it.

Continuity commands are machine-readable:

```powershell
.\aria.cmd replay  create <request.json> --json
.\aria.cmd handoff create <request.json> --json
.\aria.cmd bridge  create <request.json> --json
.\aria.cmd mesh    create <request.json> --json
```

Replay never repeats effects. Handoff excludes private conversation and does
not transfer consent. Provider eligibility performs no network call. Mesh
coordination requires an independent critic and human resolution of material
disagreement. None of these artifacts grants or aggregates authority.

## Evolution rule

Do not replace working repository behavior with standalone demonstrations.

Every evolution must:

1. begin from a clean Git tree;
2. preserve the preceding stable tag;
3. update repository-native implementation, documentation, tests, and manifest;
4. run `.\aria.cmd doctor -Strict`;
5. run `.\aria.cmd test` across every registered lattice;
6. require zero failed gates before commit or push.

The protected bootstrap baseline is `aria-alpha21-stable`. Current release and
language-evolution identities are resolved through `ARIA-RUNTIME.json`,
`VERSION`, and `aria.lock.json`.
## Alchemical glyph syntax

The first executable triad lowers into existing verified operations:

```aria
🜁 value: Number = 40 + 2
🜂 value
🜄 Project.status = "active"
🜁 Project.status -> state: Text
```

- `🜁` binds or recalls.
- `🜂` emits.
- `🜄` remembers.

Glyph syntax does not bypass semantics, bytecode verification, policy, or the virtual machine.
## Governed application and Git transaction

Authorized evolution is completed through:

```powershell
.\aria.cmd evolve apply <proposal-id> -Message "Commit message"
```

Use `-Push` only for an explicitly requested remote update. The application
module binds candidate bytes to the authorized base commit, seals the manifest,
executes strict doctor and conformance gates, commits only approved paths, and
writes an application receipt beneath `.aria/evolution/`.
## Signal-subset evidence

Use `src/Aria.SignalSubset.psm1` for bounded operational evidence. Declare a
field allowlist, purpose, source, consent scope, retention and finite limit.
Exclude raw stdout, stderr, secrets, credentials and unrelated user data by
default. A subset digest is evidence, not execution authority.
