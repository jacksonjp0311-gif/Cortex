# Cortex v10.0.0-alpha.18 — Live Semantic Calibration Screen

Alpha.18 crosses the alpha.17 calibration boundary with exactly four live
task-only calls. It calibrates task difficulty; it does not test a semantic
lesson.

## Frozen execution

- reasoning engine: `OpenAI / gpt-5.6-sol`;
- adapter evidence class: `live_empirical` from a host-controlled external API
  registration;
- cases: four level-two cache-coherence variants;
- tools: none;
- treatment: task only;
- evaluator: exact one-token option match;
- normalization: surrounding ASCII whitespace stripped;
- maximum calls: four.

The model, provider, and adapter identity are provenance. None participates in
the score.

## Result

| Quantity | Result |
|---|---:|
| Planned calls | 4 |
| Executed calls | 4 |
| Successful cases | 4 |
| Success rate | 1.00 |
| Screen state | `screening_ceiling` |
| Recommended action | `move_harder` |
| Calibration established | false |
| Semantic transfer established | false |

The complete public result is stored at
`benchmarks/results/v100_alpha18_live_semantic_calibration_screen.json`. Its
outcomes were rebuilt from four canonical native-agent trajectories. Caller
success fields were not accepted.

The commissioning ran from the alpha.17 source commit while the alpha.18
runner was still an uncommitted development change. The artifact therefore
records that dirty-tree boundary and pins SHA-256 digests for both executed
Python surfaces. This is acceptable for a development-only screen, but it is
not confirmatory reproducibility evidence.

## Interpretation

The level was too easy for this model. Formally, with the desired development
band

\[
0.30 \leq \hat p \leq 0.70,
\]

the observed

\[
\hat p = 4/4 = 1
\]

is a screening ceiling. Four cases are insufficient to establish calibration
under any result, and a ceiling supplies no discordance for a later causal
contrast.

This is not a failed runtime. It is a successful falsification of the claim
that level two is informative for this selected model.

## Next bounded step

The existing answer-sealed level-three panel is the next permitted development
candidate, but alpha.18 does not execute it. A separate operator action must
freeze and run that four-call screen. Only a mixed result may justify four
additional confirmation cases. Only after a non-ceiling band exists should
Cortex spend calls on:

\[
A=\text{task only},\quad
B=\text{verified irrelevant sham},\quad
C=\text{verified relevant lesson}.
\]

No authority opened. Host mutation, execution, memory admission, and policy
effect remain false. No credential or secret was committed.
