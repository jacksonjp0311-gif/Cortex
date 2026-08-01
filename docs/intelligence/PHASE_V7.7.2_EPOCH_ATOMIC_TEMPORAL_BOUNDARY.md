# Phase v7.7.2 — Epoch-Atomic Temporal Boundary

**Tagline:** Time is observed only after the body and phase agree.

## The live discrepancy

v7.7.1 repaired body/phase identity, but advanced activation still sampled and sometimes closed a Resonant Frame before sealing its final adaptive epoch. Interconnect could therefore report a verified global binding while its newest frame belonged to the parent epoch.

The contradiction was measurable:

- `body_epoch_id == phase_epoch_id` after activation;
- Binding Field classified the regime as verified;
- the newest frame reported `epoch_current = false`;
- self-sensing inherited that stale temporal coordinate.

## Finalization law

Advanced activation now commits the boundary in this order:

1. Close any buffered parent-epoch samples.
2. Seal the final adaptive body epoch.
3. Bind runtime phase `QUIESCENT` to that epoch.
4. Sample and close one final-epoch boundary tick.
5. Observe self-sensing from the resulting frame state.

Let `e_b` be the final body epoch, `e_p` the phase epoch, and `e_f` the epoch named by the activation boundary frame. Successful finalization requires

`e_b = e_p = e_f`.

This is an identity constraint, not a score. Coherence, residual, and spectral mass are interpreted only after the identity boundary holds.

## Honest coldness

One activation supplies one temporal tick. When `W < W_min`, the boundary frame remains `INDETERMINATE`. Cortex does not duplicate that tick to simulate temporal support. Warmth still requires real observations accumulated through the normal field and Warm-In paths.

## Claim boundary

Epoch-atomic finalization improves attribution and observation order. It grants no authority, performs no automatic ARIA execution, and cannot turn a temporal metric into host mutation permission, constitutional witness, correctness, or consciousness.
