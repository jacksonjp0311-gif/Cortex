# Security and Trust Boundary

## Local data

Cortex stores repository content, metadata, Git summaries, episodic events, environment profiles, and neural associations locally. Protect `CORTEX_HOME` as repository-sensitive data.

## Secrets

Exclude secret-bearing files before bootstrap. Do not record credentials, tokens, personal data, or raw confidential logs as episodic events.

## Generated inference

Environment profiles, Discovery Cards, relationship resolution, and neural association weights may be incomplete or wrong. They are routing evidence, not authority.

## Neural plasticity

Plasticity can only update bounded internal association weights and, under Governor
gates, create weak reversible **G_learned** edges (e.g. coactivation invent). It
cannot change source files (**G_host**), invent host topology, or operate in
`read_only` mode. See `docs/intelligence/TOPOLOGY_LAW.md`.

## Authority

Cortex never authorizes durable repository mutation. Current source, current tests, compiler/runtime evidence, host repository rules, and explicit human authorization control changes.

## Certificate boundary

A bootstrap certificate verifies the implemented inventory, integration, environment, neural compilation, and retrieval checks at a manifest. It is not a security audit or correctness proof.
