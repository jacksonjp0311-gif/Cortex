# Counterfactual Source Improvement

Cortex 10.0.0-alpha.5 asks a narrower and more useful question than “did the
candidate pass?”:

> Did this exact candidate change a frozen outcome relative to the unchanged
> source from which it was created?

## The wound

Alpha.4 could prove that a proposed patch survived a host-selected verification
contract. If the unchanged repository already passed those checks, that result
was verified maintenance—not evidence that the patch repaired anything.

```text
candidate pass != measured repair
```

## Preregistered comparison

The host creates the comparison contract before either arm runs. It binds:

- the source Git HEAD;
- exact patch proposal and prior passing verification receipt;
- host-owned evaluator commands;
- runtime environment identity;
- primary metric and minimum effect;
- operator-only promotion and closed authority flags.

Neither the model nor an HTTP caller can supply evaluator commands or pass
states.

```text
                  same source HEAD
                   /             \
          unchanged baseline   exact candidate patch
                   \             /
                  same frozen evaluator
                           |
              Δ = I(candidate) - I(baseline)
```

## Result algebra

For the binary host outcome `Y`:

```text
baseline  candidate  delta  classification
FAIL      PASS       +1     REPAIR_MEASURED
PASS      PASS        0     VERIFIED_MAINTENANCE
PASS      FAIL       -1     REGRESSION_DETECTED
FAIL      FAIL        0     IMPROVEMENT_HELD
```

Regression and held results block promotion. A measured repair or verified
maintenance remains advisory until the operator makes a separate promotion
decision. Repository HEAD and target preimages are checked again at that edge.

## Read/write and authority boundary

Both experiment arms are detached disposable worktrees. The active checkout is
unchanged. The evaluator is allowed to execute only because the operator
explicitly requested verification; a Git worktree is isolation from repository
state, not an operating-system sandbox.

```text
host_mutate_authorized       = false
execution_authorized         = false
memory_admission_authorized  = false
policy_effect                = false
```

## Claim boundary

`REPAIR_MEASURED` means one exact patch changed one preregistered host outcome
from fail to pass under a matched source comparison. It does not establish:

- general source-code improvement;
- improved model cognition;
- autonomous recursive self-improvement;
- consciousness or subjective awareness;
- safety outside the tested contract;
- authority to apply the patch.

Repeated, held-out, independently replicated effects would be required for a
broader claim. Alpha.5 deliberately stops at the bounded engineering result.
