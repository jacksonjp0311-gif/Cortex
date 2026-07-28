# Intent Verification

Status: implemented in alpha.25 as the JSON-first `aria.intent/*` contract.

## The question this layer answers

ARIA can verify that a program is internally valid and still fail the human if
the semantic model misunderstood the request. Intent verification therefore
does not ask the producing model to assert that it understood. It separates
the human declaration, the model's interpretation, human approval, independent
challenge, program effects, execution outcomes, and evidence into
content-addressed artifacts.

The verifier derives the final verdict from those artifacts:

```text
canonical intent
  -> separate interpretation
  -> exact human approval
  -> independent challenge
  -> authority ceiling
  -> required and forbidden outcomes
  -> acceptance evidence
  -> derived intent proof
```

There is no `intentSatisfied` input field.

## Artifact model

### Canonical intent

`aria.intent/0.9` records:

- objective and assumptions;
- required and forbidden outcomes;
- the maximum allowed effects;
- acceptance criteria and required evidence kinds;
- explicit ambiguities and their severity;
- whether an independent challenge is mandatory.

Its SHA-256 identity changes if any declared term changes.

### Interpretation

`aria.intent-interpretation/0.9` is produced before implementation approval. It
binds to the exact intent identity and states the understood objective,
assumptions, expected effects, claimed obligations, unresolved ambiguities, and
implementation identity.

The human approves this interpretation identity, not merely a source diff.

### Approval and ambiguity resolution

`aria.intent-approval/0.9` binds the intent and interpretation identities to a
trusted human principal. Every material ambiguity needs an explicit resolution.
Changing a resolution changes the approval identity.

### Independent challenge

`aria.intent-challenge/0.9` must come from a principal different from the
interpretation producer. It can identify alternative readings, hidden
assumptions, missing criteria, excess authority, or counterexamples. Material
issues stop satisfaction until a human resolution is bound into the approval.

Principal inequality establishes separation in the artifact model. Production
deployments still need an external identity system to establish that two
principal names correspond to genuinely independent actors.

### Program summary and evidence

`aria.intent-program-summary/0.9` declares the implementation artifact,
requested effects, measured outcomes, and observed forbidden outcomes.
`aria.intent-evidence/0.9` binds passing evidence to a criterion, evidence kind,
and program artifact.

Evidence digests are identities, not a claim that ARIA generated the underlying
test or semantic-diff report. Evidence producers remain part of the trusted
computing base until attestation and proof adapters are added.

Alpha.5.1 adds `aria.intent-program-summary/1.0`. The
`New-AriaIntentProgramSummaryFromArtifact` constructor accepts verified
container bytes and derives the artifact identity, admitted effect-graph
identity, and requested effects from independently verified bytecode. These
fields are no longer supplied by the producer. Behavioral outcomes and their
evidence producers remain an explicit trust boundary.

### Derived proof

`aria.intent-proof/0.9` is emitted by the deterministic verifier. It records:

- the exact input artifact identities;
- each derived obligation and its result;
- stable rejection reason codes;
- `satisfied` or `rejected`;
- its own canonical SHA-256 identity.

The proof is stored beneath `.aria/intent/<intent-digest>/`.

## Verification rules

The verifier rejects when:

1. any content-addressed artifact has been altered;
2. the interpretation or approval references a different identity;
3. the approver is absent from the explicit verification policy;
4. the interpretation omits a declared obligation;
5. expected or requested effects exceed the intent's allowed effects;
6. a required outcome is absent or differs from its expected value;
7. a forbidden outcome was observed;
8. acceptance evidence is missing, failing, the wrong kind, or bound to another program;
9. a material ambiguity lacks human resolution;
10. a required challenge is absent or produced by the interpreter;
11. a material critic issue lacks human resolution.

## CLI

Run the complete example:

```powershell
.\aria.cmd intent verify .\examples\intent\publish-verified-release.json
```

The command writes a proof whether the verdict is satisfied or rejected, and
returns a non-zero exit code for rejection.

## Honest boundary

This layer cannot prove that a natural-language objective has one objectively
correct meaning. No system can extract unstated intent deterministically.
Alpha.25 instead makes silent misreading harder to hide and easier to stop:

- interpretations are separate and reviewable;
- assumptions and ambiguities are explicit;
- approval binds exact content;
- independent challenges surface alternate readings;
- authority is capped by the human declaration;
- outcomes and evidence, not model confidence, determine the verdict.

Native `.aria` intent syntax, cryptographic principal authentication,
attested evidence adapters, model diversity policy, and automatic obligation
generation remain future work.
