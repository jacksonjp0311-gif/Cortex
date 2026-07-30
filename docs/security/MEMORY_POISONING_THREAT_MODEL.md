# Memory Poisoning Threat Model

Attack path:

```text
malicious input → stored memory → coactivation → invented edges → later retrieval → agent action
```

Mitigations: lineage, quarantine of descendants, selective unlearning with snapshot/rollback, Evidence Kernel fallback, independent witness.
