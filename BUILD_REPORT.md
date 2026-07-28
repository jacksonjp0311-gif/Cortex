# Build Report

## Cortex v3.0.0 addendum

- Date: July 28, 2026
- Package: `cortex-memory`
- Python: 3.10+
- Source distribution: built
- Wheel: `cortex_memory-3.0.0-py3-none-any.whl`
- Clean-wheel install: passed
- Installed `cortex` and `cortex-mcp` entrypoints: passed
- Automated tests: 43 passed
- Ruff and Python compilation: passed
- Controlled benchmark gates: passed
- Nested-clone self-host lifecycle: passed
- External sealed-host bootstrap/activation: passed without host writes
- Self-contained INTERNAL ARIA subtree: packaged (298 tracked files)
- ARIA native manifest: 297/297 verified
- Bundled ARIA handshake, strict doctor, and conformance suite: passed
- Clean-wheel INTERNAL ARIA verification: passed with no external repository dependency
- ARIA meta-language descriptor/context/continuation integration: passed
- Native ARIA neural-region compilation: 292 internal / 110 repository nodes
- Generic Python task: ARIA dormant, 0 eligible / considered / fired nodes
- ARIA continuity/coordination task: 40 of 292 ARIA nodes eligible, 15
  considered, and 10 fired
- Dormant-region exclusion occurs in lexical and vector candidate SQL, before
  embedding comparison or neural propagation
- Native ARIA runtime: 7 typed purposes, 19 immutable core cues, maximum 32
  learned cues, 0.65 wake threshold, bounded confidence-only adaptation
- ARIA fluency evaluation: 20/20 passed; zero false wakes, missed wakes, or
  purpose misses
- Exact nested self-host after runtime fluency integration: verified
  certificate, ready activation, commit parity, tests passed, 1.413182 s

New v3 modules are `cortex.continuation`, `cortex.lifecycle`,
`cortex.federation`, `cortex.evaluation`, and `cortex.mcp`. GCMT is integrated
within Cortex's existing single-substrate and authority boundaries rather than
as a competing memory service. The internal self-host engine is explicitly
labeled and commit-verified. `--external` supports sealed repositories by
placing all configuration and runtime artifacts under Cortex home.
`cortex.aria_meta` contains the complete ARIA source snapshot as a squashed Git
subtree, including its Apache-2.0 license and notice. `cortex.meta_language`
uses this internal bundle by default and can integrate a host-local ARIA
repository when one is present. Cortex core remains implemented and executed
in Python; ARIA is not automatically executed and grants no mutation authority.

The release artifacts include the internal snapshot:

- wheel: 612,077 bytes;
- source distribution: 473,594 bytes;
- clean-wheel verification: 297 manifest entries checked, zero failures.

The original neural-edition report follows as release lineage.

## Release

- Name: Cortex Neural Interlink
- Version: 1.1.0
- Date: July 11, 2026
- Package: `cortex-memory`
- Python: 3.10+
- License: MIT

## Integration decision

The standalone Neuron repository was not copied into Cortex as a second independent memory service. Its useful capabilities were adapted into `cortex.neuron` and connected to Cortex's existing graph, SQLite store, hippocampal sessions, Bridge, Governor, and Nexus packet.

This preserves the original Cortex mission and prevents:

- duplicate databases;
- duplicate episodic memory;
- competing consolidation logic;
- conflicting governance modes;
- divergent provenance;
- ambiguous ownership between Cortex and Neuron.

## Added modules

- `cortex/environment.py`
- `cortex/neuron/models.py`
- `cortex/neuron/compiler.py`
- `cortex/neuron/engine.py`
- `cortex/neuron/plasticity.py`
- `cortex/neuron/__init__.py`
- `benchmarks/sparse_activation_benchmark.py`

## Main evolved behaviors

- environment learning during bootstrap;
- file nodes compiled from indexed surfaces;
- bounded synapses compiled from current graph evidence;
- sparse deterministic task activation;
- neural support-path expansion under the existing context budget;
- bounded plasticity in normal/constrained modes;
- hash-chained neural replay ledger;
- neural and environment fields in NexusGate packets;
- portable no-install all-one flow;
- automatic embedded-engine exclusion;
- repository-local wrapper binding that resists inherited Cortex-home and Python-engine redirection.

## Validation summary

- Python compile: passed
- Automated tests: 17 passed
- Bash syntax: passed
- Portable nested-folder smoke: passed
- Wheel build: passed
- Clean wheel install/bootstrap/activate: passed
- Database integrity: passed
- Neural ledger integrity: passed
- Deterministic benchmark repeat: passed

## Known boundaries

- PowerShell was statically reviewed but not executed in the Linux build environment.
- Environment commands are inferred and are not automatically executed during bootstrap.
- Neural relationships are limited by parser and graph quality.
- Sparse activation is an engineering routing mechanism, not a biological simulation.
