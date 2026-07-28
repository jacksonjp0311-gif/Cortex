# Verified Reduce alpha.9

Verified Reduce completes ARIA's first bounded sequence-algorithm vocabulary:

```aria
let total: Number = Σ(values, Add, 0)
```

Its exact contract is:

```text
Sequence<T> × PureFunction<A,T,A> × A → A
```

## Governed interpretation

This evolution used both ARIA governance layers before compiler mutation:

- `plans/verified-reduce-alpha9.aria` passed the language gate;
- `plans/verified-reduce-alpha9-intent.json` binds the canonical intent,
  interpretation, explicit human approval, independent challenge, ambiguity
  resolutions, authority ceiling, and acceptance evidence;
- ARIA derived satisfied proof
  `sha256:35f94e739b1c0609bd02bbd319942d85cf620aef8db43ad99bd2a58467998b27`.

The proof authorizes this bounded implementation scope. It does not claim that
the completed implementation passed its later conformance and remote gates.

## Compiler and verifier

The parser creates a dedicated `reduce` AST node containing the sequence,
compile-time reducer identity, and initial expression. Semantic analysis
requires:

- input `Sequence<T>`;
- exactly two reducer parameters ordered `(A,T)`;
- exact initial/first-parameter type agreement;
- exact element/second-parameter type agreement;
- exact reducer return continuity to `A`;
- a verified transitive pure effect summary.

The compiler emits:

```text
REDUCE reducer=<name> sequenceType=Sequence<T> accumulatorType=A
```

The independent bytecode verifier reconstructs all of those obligations. The
instruction pops the explicit initial accumulator and sequence and pushes one
value of type `A`.

## Runtime

The VM executes:

```text
accumulator = initial
for element in sequence, left to right:
    accumulator = Reducer(accumulator, element)
return accumulator
```

Empty input returns the explicit initial value with zero reducer calls. ARIA
does not infer an identity. A non-associative subtraction fixture proves the
execution order rather than relying only on associative addition.

`A` may differ from `T`; the admission lattice counts a `Sequence<Text>` into a
`Number` accumulator while preserving exact types.

## Evidence and privacy

Reduce projects:

```text
algorithm.reduce.start      ACTIVE
algorithm.reduce.iteration  INFO × completed reducer calls
algorithm.reduce.complete   PASS
algorithm.reduce.fracture   FAIL
```

Records contain reducer identity, input count, completed count, measured
duration, source line, and event identities. They exclude elements, the
initial value, and every accumulator value.

## Use-discovered performance closure

The required 256-element benchmark initially took about 79 seconds even
without persistent journaling. The cause was repeated semantic-cue registry
validation and duplicate verification of events freshly sealed inside Event
Spine.

ARIA now:

- caches one fully verified content-addressed cue registry per module process;
- preserves full validation for explicitly supplied registries and public
  events;
- avoids verifying an internally constructed event twice;
- persists iterable events in exact 32-record hash-chained chunks.

The persistent benchmark after closure:

```text
input elements       256
iteration events     256
total reduce events  258
result               32896
elapsed              approximately 17.3 seconds on Windows PowerShell 5.1
journal              258 replayed events, approximately 565 KB
```

Batch tests prove exact replay and rejection when ledger bytes change before a
flush. No event identity, sequence, digest link, or truthful iteration was
removed to gain speed.

## Admission evidence

The dedicated 27-gate lattice proves source semantics, independent verifier
tamper rejection, exact left-fold order, empty and single inputs, cross-type
accumulation, privacy, fracture behavior, determinism, and complete
Map-Filter-Reduce composition. Signal Integrity adds a batch replay and
tamper-rejection gate.

Aggregate conformance is `396/396`.

## Next boundary

Per-Card Execution Evidence alpha.10 should bind each exercised semantic card
to source, semantic IR, artifact, effect graph, policy, operation, and test
evidence identities. Evidence remains observational and grants no authority.
