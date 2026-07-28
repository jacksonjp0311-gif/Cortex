# Provider Bridge Membrane alpha.16

Alpha.16 introduces a provider-neutral integration boundary.

`aria bridge create <request.json> --json` binds a handoff, declared provider
and model, operation, consent identity, requested capabilities, and an explicit
capability ceiling. Requests outside the ceiling are deterministically
rejected.

This milestone verifies transport eligibility only. The membrane performs no
network call, embeds no model payload, activates no capability, and grants no
authority. A future adapter must still cross a separately authorized transport
boundary.
