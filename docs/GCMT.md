# Governed Continuation Memory Theory in Cortex

**Theory:** Governed Continuation Memory Theory (GCMT v1.0)

**Author:** James Paul Jackson
**Implementation:** Cortex v3

GCMT treats memory as regulated transformation with recoverable origin. Cortex
v3 implements that theory as a software architecture without claiming
sentience, consciousness, biological identity, human-memory equivalence,
clinical validity, autonomous self-improvement, or universal optimality.

## Canonical chain

```text
bound
-> select
-> correct
-> write candidate
-> re-anchor
-> verify
-> authorize
-> promote
-> receipt
-> rollback when required
```

## Three state planes

| GCMT plane | Cortex representation | Authority |
|---|---|---|
| Operational state | Bounded task context and sparse active graph | Temporary and advisory |
| Evidence state | Indexed source, tests, documentation, Git telemetry, runtime evidence, provenance | Addressable support |
| Canonical state | Explicitly promoted Cortex-owned durable memory | Requires every promotion lock |

The planes are intentionally non-interchangeable. A retrieved or learned value
does not become canonical merely because it is relevant, fluent, repeated, or
high-confidence. Cortex canonical memory is also distinct from repository
source: promotion never edits source, configuration, deployments, or external
systems.

## Verified continuation packet

`cortex continuation` emits `cortex-continuation/1.0` with the GCMT packet
fields:

- origin identity, repository identity, manifest, and Cortex version;
- bounded operational task state;
- evidence references and hashes;
- canonical-memory references;
- drift and uncertainty telemetry;
- contradictions, wounds, and unresolved unknowns;
- authority scope and Governor mode;
- verification checks;
- promotion receipts and rollback availability;
- expiry and re-anchoring conditions.

The packet is stored in Cortex's SQLite substrate. `continuation-verify`
recomputes its state hash, checks origin and evidence addressability, validates
expiry, and requires a declared rollback path.

```bash
cortex continuation --repo MyProject --task "Continue the release investigation" --json
cortex continuation-verify --repo MyProject --packet-id vcp_... --json
```

## Promotion gates and rollback

Cortex v3 separates adaptation from promotion. A candidate enters Cortex
canonical memory only when:

1. source evidence is present and content-addressed;
2. every declared verification check passes;
3. explicit promotion authority is supplied;
4. the declared quality product meets its threshold;
5. a receipt can be written;
6. a rollback path exists.

Rejected candidates remain operational. Accepted candidates receive a
hash-chained receipt containing previous state, candidate state, evidence,
verification, authority, and state hashes.

```bash
cortex promote \
  --repo MyProject \
  --key architecture.auth-owner \
  --value '{"path":"src/auth.py"}' \
  --evidence-memory 42 \
  --verification tests=true \
  --verification repeatable=true \
  --authorize \
  --json

cortex rollback --repo MyProject --receipt-id rcp_... --authorize --json
```

The `--authorize` flags represent explicit invocation authority for
Cortex-owned memory only. Host rules and human authorization still control
repository mutation.

## Selective retention and effective age

`cortex lifecycle` implements GCMT's complementarity of decay and correction.
Outcome learning performs localized correction when evidence is actively
verified. Lifecycle processing retires learned routing deviation that may no
longer be activated.

Decay moves a learned synapse weight toward its evidence-backed structural
prior. It never deletes repository evidence or graph topology. Relation types
receive different retention factors, recently activated associations receive a
grace period, and each proposal reports chronological age, survival, and
effective age.

```bash
cortex lifecycle --repo MyProject --json
cortex lifecycle --repo MyProject --grace-hours 48 --decay-per-day 0.03 --apply --json
```

Application requires explicit `--apply` plus `normal` or `constrained`
Governor mode. Applied transitions are recorded in the neural ledger.

## Global re-anchoring

Continuation packets request broader evidence re-anchoring when any of these
conditions hold:

- repository origin or manifest trust is degraded;
- retrieval confidence falls below the declared threshold;
- active contradiction or insufficient evidence is present;
- the packet expires.

Re-anchoring is therefore state-dependent, not only timer-dependent.

## Boundary-preserving federation

`cortex federated-query` searches multiple attached repositories while keeping
repository identity on every result. Scores are normalized within each
repository before deterministic federation. Near-tied evidence from different
repositories is surfaced as an ambiguous boundary and recommends a source
check; it is never silently merged.

```bash
cortex federated-query "Where is token refresh owned?" \
  --repos Frontend Backend SharedAuth --json
```

## Scalable semantic candidate selection

Cortex's dependency-free semantic search now stores a 16-bit deterministic
locality-sensitive vector bucket in SQLite. Query processing evaluates:

1. exact lexical candidates;
2. the matching semantic bucket;
3. one-bit neighboring buckets;
4. a bounded deterministic fallback sample;
5. exact cosine similarity over the resulting candidate set.

Existing databases backfill buckets lazily. This is a bounded approximate
candidate index, not a claim of universal nearest-neighbor optimality.

## Replay evaluation and falsification

`cortex evaluate` runs the same declared corpus twice:

- structural baseline weights;
- learned outcome-adjusted weights.

It reports recall, mean reciprocal rank, boundary separation, abstention
accuracy, improved cases, regressed cases, and promotion gates. Evaluation
activations are observational and do not write learning state.

```bash
cortex evaluate examples/evaluation_corpus.json --repo MyProject --json
```

The corpus supports GCMT failure classes through:

- expected paths for source recall and localized correction;
- forbidden paths for interference and boundary contamination;
- insufficient-evidence cases for abstention;
- base-versus-learned comparison for regression detection.

Results are benchmark evidence only for the declared corpus and configuration.
They are not universal answer-quality evidence.

## Agent-native access and observability

`cortex-mcp` exposes read-oriented MCP tools over stdio:

- `cortex_status`
- `cortex_query`
- `cortex_federated_query`
- `cortex_context`
- `cortex_continuation`
- `cortex_lifecycle_plan`
- `cortex_evaluate`

Canonical promotion and lifecycle application are deliberately absent from MCP
tools so an agent transport cannot silently convert relevance into authority.

`cortex dashboard --repo MyProject --json` summarizes repository inventory,
Governor state, learning events, outcomes, continuation packets, canonical
states, receipts, lifecycle eligibility, and supported protocols.

## Evidence and claim boundary

Cortex distinguishes theory, simulation, implementation, benchmark,
robustness, and independent evidence. A lower class is never presented as a
higher one. Version 3 provides an executable implementation, test coverage, and
a repository-native benchmark harness. Cross-domain robustness and independent
reproduction remain future evidence requirements.
