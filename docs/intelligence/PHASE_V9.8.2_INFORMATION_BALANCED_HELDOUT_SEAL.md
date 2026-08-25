# Cortex v9.8.2 — Information-Balanced Calibration & Held-Out Corpus Seal

## Purpose

v9.8.2 evolves Cortex from detecting an uninformative experiment to constructing
a falsifiable one. It calibrates task difficulty using development-only
observations, selects the most informative admissible level, and generates a
cryptographically bound but answer-free held-out corpus before model execution.

This release implements and verifies the experiment-design mechanism. It does
not execute a new frontier calibration or confirmatory competence trial.

## Mathematical surface

For measured runtime ability `theta` and task difficulty `beta`:

```text
p = P(success | theta, beta) = sigma(theta - beta)
I(theta, beta) = p(1-p)
```

Item information is maximal at `p=0.5`, when ability and difficulty meet. It
approaches zero at a floor or ceiling. Cortex estimates difficulty from binary
development outcomes using a Jeffreys-smoothed logit:

```text
p_hat = (successes + 1/2) / (n + 1)
beta_hat = theta - log(p_hat / (1-p_hat))
```

Smoothing keeps floor and ceiling estimates finite; it does not turn those
levels into admissible tasks. The existing hard 30–70% success window remains
noncompensatory.

For the future matched causal trial:

```text
b = count(control=0, treatment=1)
c = count(control=1, treatment=0)
effective causal sample = b+c
delta = (b-c)/n
```

Difficulty information and paired discordance are distinct. High `p(1-p)`
helps construct a useful task panel; only observed matched discordance informs
the treatment effect.

## Difficulty ladder

`cortex/information_calibration.py` provides:

- stable Rasch success probability;
- item information;
- finite difficulty estimates;
- per-family ladder calibration;
- explicit `increase_difficulty`, `decrease_difficulty`, or
  `collect_or_rebalance_development_cases` recommendations;
- hash-bound verification with no model/provider scoring inputs.

`cortex/discriminative_forge.py` composes one through four exact subcases per
task. Composition creates a deterministic increasing-work ladder across:

- repository bug localization;
- multi-step code repair;
- stale-state detection;
- API migration;
- architecture reconstruction.

The generated development corpus contains 80 cases: five families, four levels,
and four variants per level. It is explicitly non-confirmatory.

## Leakage wound and repair

The first held-out adversarial test failed correctly. Different corpus seeds
could still produce identical stale-state, API-migration, and architecture
tasks because those families did not consume the random stream in their
semantic body.

v9.8.2 repairs the generator so each family's identifiers, parameters, endpoint
material, or dependency names vary with the partition seed. Held-out overlap is
checked by canonical case identity and fails closed.

Changing only a receipt ID would not have been sufficient. The task itself must
be different.

## Held-out seal

After every declared family has an informative selected level, Cortex may build:

```text
public manifest
  - prompts
  - case IDs
  - difficulty levels
  - evaluator type
  - answer hashes
  - answer-key commitment
  - secret-seed commitment
  - source calibration hash

private answer key
  - exact case ID -> public answer mapping
  - secret-seed commitment
```

The public manifest contains neither exact answers nor the secret seed. The
private key is written only when an operator explicitly supplies both a seed
file and a private output path. Nothing is persisted automatically.

The public manifest states:

```text
held_out = true
eligible_for_preregistration = true
confirmatory_evidence = false
```

An unexecuted corpus is a design object, never empirical evidence.

## Causal preregistration binding

`cortex/causal_trial.py` now verifies:

- difficulty-calibration receipt integrity;
- selected task families equal declared strata;
- held-out public-manifest integrity;
- held-out calibration hash equals the selected calibration;
- preregistered task-corpus hash equals the held-out corpus hash;
- no answers are present in the public manifest.

Both `development_calibration_bound` and `heldout_corpus_sealed` are hard gates.
The existing power, live-evidence, semantic-witness, exact-effect, and negative-
transfer gates remain unchanged.

## Model neutrality

No model, provider, endpoint, or adapter is selected by the calibration module,
forge, benchmark runner, or causal scoring policy. External runtimes may supply
development observations. Their identity remains invocation provenance and
cannot affect task selection.

Hidden reasoning is neither required nor stored.

## Tests

Adversarial coverage includes:

- information peaks at the ability boundary;
- floor/ceiling difficulty estimates remain finite but inadmissible;
- the informative level is selected instead of the easiest level;
- all-ceiling ladders request harder tasks;
- ladder generation is deterministic and compositional;
- held-out cases are disjoint from development;
- public manifests contain no exact answers;
- answer-key, prompt, and manifest tampering fails;
- callers cannot mark an unexecuted corpus as evidence;
- preregistration stores no answer key or secret seed;
- all authority bits remain false.

## Claim boundary

v9.8.2 establishes a model-neutral information-balanced task-design and
held-out sealing mechanism. It does not establish positive competence lift,
semantic completeness, cross-model benefit, generalization, production
portability, or independent replication.

## Next evidence

1. Execute the 80 development cases using fresh runtime-selected frontier
   sessions or a preregistered batching design.
2. Preserve only public outputs, invocation provenance, exact evaluations, cost,
   and latency.
3. Calibrate each family and increase/decrease levels until all retained
   families enter the information window.
4. Generate a disjoint held-out seal using a host-secret seed stored outside the
   repository.
5. Calculate matched-trial sample size from preregistered effect and discordance
   assumptions.
6. Execute the frozen A–E and negative-control trial.
7. Replicate before making a causal transfer claim.
