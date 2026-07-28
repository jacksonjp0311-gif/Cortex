# Per-Card Execution Evidence alpha.10

ARIA now produces one bounded, content-addressed receipt whenever verified
Map, Filter, or Reduce reaches completion or fracture.

## Shared event projection

```text
verified card + compiled program + policy
                    ↓
             algorithm executes
                    ↓
         terminal Event Spine event
                    ↓
   aria.card-execution-evidence/1
           ↙                    ↘
human cue and explanation   canonical machine record
```

Both views describe the same terminal event. The receipt does not infer success
from animation: `completed` requires a verified `PASS` terminal event and
`fractured` requires `FAIL`.

## Receipt identities

Each receipt binds:

```text
card
compiler + runtime
source + semantic IR
artifact + effect graph
policy
admission-test contract
operation + aggregate counts
terminal event + SignalSubset
authority boundary
```

The artifact identity is calculated from the exact `.ariac` container bytes
when the container is decoded. It is no longer necessary to trust a detached
build label during runtime.

## SignalSubset

The embedded subset selects exactly:

```text
sequence
operationId
operationSequence
domain
phase
state
digest
```

It explicitly records the exclusion of event data, projection, information,
coherence, energy, source, and other fields. This makes the privacy decision
inspectable instead of implicit.

## Aggregate evidence

Map records input, completed, and output counts. Filter additionally records
selected count. Reduce records input, completed, and one completed output.
Fractures report only work completed before failure. Values never enter the
receipt.

## Verification

`Test-AriaCardExecutionEvidence` rejects:

- unknown or changed card identities;
- altered source, IR, artifact, effect, policy, or test identities;
- malformed, negative, or non-aggregate counts;
- modified SignalSubset contents;
- receipt digest changes;
- any authority claim or capability grant.

The dedicated 20-gate lattice also proves exact Event Spine persistence and
replay, three-card composition, payload exclusion, deterministic canonical
identity, and unchanged program output.

## Boundary of meaning

A sealed receipt means:

> This exact verified card reached this recorded terminal state while this
> exact artifact ran under this policy, and the stated bounded observations
> verified.

It does not mean universal correctness, human-intent satisfaction, unlimited
authority, current release health, or absence of unknown defects.

## Next evolution

Semantic Proposal Bundles alpha.11 can use these receipts as exact evidence
references when proposing a new or revised semantic card. Proposal production
must remain separate from approval and admission.
