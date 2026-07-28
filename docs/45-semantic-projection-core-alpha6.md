# Semantic Projection Core alpha.6

ARIA now projects one verified event state into forms suited to both humans and
machines:

```text
S_t → (G_t, M_t, R_t, E_t)
```

The four outputs are carried by `aria.semantic-projection/1`, introduced inside
`aria.event` version 2 and retained by hash-chained version 3:

- `G_t` — a stable glyph, label, and color role;
- `M_t` — a motion and rhythm contract triggered by a recorded transition;
- `R_t` — the ordered phase, state, bounded signal lanes, metrics, provenance,
  identities, and digests;
- `E_t` — plain-language meaning and an explicit boundary saying what the cue
  does not establish.

They are projections of the same event, not separately authored claims. The
event digest binds the projection; the projection digest binds its cue identity,
transition, metrics, explanation, accessibility contract, and engagement
contract.

## Canonical cues

`grammar/semantic-cues.json` defines eight content-addressed cues:

| Cue | Human expression | Verified meaning |
|---|---|---|
| `signal.transmit` | 🜂 wave | information crossed a named bounded stage |
| `buffer.wait` | ⧖ calm pulse | work remains pending and observable |
| `authority.evaluate` | ⛨ clamp | authority is being evaluated, not granted |
| `verification.seal` | ◆ settle | the declared checks for this event passed |
| `invariant.fracture` | ⬗ fracture | a named invariant failed or was rejected |
| `boundary.warning` | ⬖ pulse | a bounded concern exists without asserting failure |
| `observation.info` | 🜁 pulse | bounded information was recorded |
| `execution.closure` | ◇ settle | a named lifecycle reached recorded closure |

Every cue declares permitted states and contexts, motion trigger, rhythm basis,
static fallback, meaning, prohibited interpretations, and SHA-256 identity.

## Truthful motion and timing

Motion is initiated by an event boundary. A projection records whether the
state identity changed, whether the event instead supplied new information in
the same state, and why the cue exists. It does not animate merely because wall
time passed.

Context banners and cue-discovery listings remain static. They orient the
operator but do not pretend that a computational transition occurred.

Timing is `measured-latency` only when the event contains a bounded numeric
`durationMs`. Otherwise timing is explicitly `event-boundary`; ARIA makes no
percentage or latency claim. Iteration, queue, byte, and obligation metrics are
included only when measured values are present.

## Accessibility equivalence

Reduced-motion and static profiles preserve:

```text
cue identity
glyph and label
state and phase
measured metrics
meaning
non-meaning boundary
digest
```

Color reinforces state but is never the sole carrier. Set
`ARIA_REDUCED_MOTION=1`, `ARIA_MOTION=off`, `ARIA_NO_ANIMATION=1`, or
`ARIA_ANIMATION=0` to suppress temporal frames.

## Privacy boundary

Before event detail is hashed or persisted, it is bounded to four levels,
32 items per level, and 512 characters per text value. Secret-, token-,
credential-, password-, private-key-, authorization-, raw-output-, and
payload-shaped fields are replaced with `[REDACTED]`.
Signal lanes also redact common bearer, provider-token, API-key, and private-key
shapes and truncate text beyond 512 characters.

This is a journal minimization boundary, not a claim that arbitrary prose can
never contain sensitive information. Callers must still provide purpose-built,
allowlisted event detail.

## Non-manipulation contract

The sealed registry prohibits variable rewards, fake urgency, artificial
scarcity, streak mechanics, surprise reinforcement, unbounded loops, and false
progress. Attention is justified only by truthful state change or new bounded
information.

## Self-teaching CLI

```powershell
.\aria.cmd cue list
.\aria.cmd cue explain verification.seal
.\aria.cmd cue explain authority.evaluate --json
.\aria.cmd cue verify
.\aria.cmd events
```

The explanation surface and JSON surface resolve to the same cue digest. Event
rendering consumes the projection stored in the journal, so pasted output names
the cue identity and its machine record retains the full bounded contract.

## Authority boundary

```text
symbol ≠ meaning ≠ implementation ≠ authority
```

A projection describes recorded state. It cannot grant capability, approve an
interpretation, manufacture verification evidence, or override policy.

## Next bounded evolution

Semantic Projection Core closes the human/machine representation gap at the
event layer. Signal Integrity Closure alpha.6.1 then applies it to chained
history, truthful waiting, VM events, and governance output before Verified Map
alpha.7.
