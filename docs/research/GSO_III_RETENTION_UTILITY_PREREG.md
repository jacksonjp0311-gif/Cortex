# GSO-III — fresh retention utility (preregistered, not executed)

This experiment is **not authorized in GSO-II**.

## Question

Does independently verified retained structure improve future performance
relative to a matched sham prior?

## Frozen conditions (to be bound before any call)

- model identity and observable parameters
- provider
- tools
- context budget
- call budget
- task distribution
- stopping rule
- environment identity
- transduction policy
- evaluator / instrument
- scoring

## Arms

- A = no retained prior
- B = matched irrelevant/sham prior
- C = relevant independently verified retained prior

## Measures

- `G_context = U_B - U_A`
- `G_retention = U_C - U_B`
- `G_total = U_C - U_A`

Desired later pattern, not claimed now: `U_C > U_B ≈ U_A` on fresh
discriminative tasks.

Model-turnover heredity is not authorized until positive retention utility
itself replicates.
