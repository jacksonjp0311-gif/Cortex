# Sparse Activation Benchmark Report

**Release:** Cortex Neural Interlink v1.1.0  
**Date:** July 11, 2026

## Purpose

This benchmark checks whether activation work remains bounded below the full assimilated graph for a synthetic linked repository.

## Workload

- 250 generated Python modules
- one README
- ten generated test files
- 262 indexed neural nodes after repository-local integration files were included
- 280 compiled synapses
- deterministic feature-hash embeddings
- activation depth: 2
- activation node budget: 64
- plasticity disabled for repeatability

Run:

```bash
python benchmarks/sparse_activation_benchmark.py --files 250
```

## Observed result

Two clean benchmark runs produced identical activation metrics and state hash. Wall-clock timings varied slightly, as expected.

```json
{
  "indexed_nodes": 262,
  "synapses": 280,
  "bootstrap_seconds_run_1": 0.434194,
  "bootstrap_seconds_run_2": 0.428013,
  "activation_seconds_run_1": 0.003838,
  "activation_seconds_run_2": 0.003926,
  "nodes_considered": 42,
  "nodes_fired": 24,
  "propagation_steps": 30,
  "sparse_activation_ratio": 0.09160305,
  "considered_fraction": 0.16030534,
  "max_depth": 1
}
```

The activation considered 42 of 262 nodes, or about 16.0% of the compiled graph, and fired about 9.2% of all nodes.

Both runs produced this state hash:

```text
cd202d9dd4d7c8052a62fe391accf87dbaedc37390e5881a331dfc894172c4ba
```

## Interpretation

The result demonstrates bounded sparse routing for this synthetic workload. It does not establish universal performance, biological fidelity, or superiority over other retrieval systems. Repository shape, query quality, relation density, hardware, Python version, and storage state affect runtime and sparsity.
