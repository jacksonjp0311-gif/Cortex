# ADR 0001: PowerShell Bootstrap, Independent Language Identity

**Status:** Accepted

## Context

The target operator environment is Windows and already has Windows PowerShell 5.1. ARIA must become runnable without requiring Rust, Python, Node, or package installation.

## Decision

Implement the 0.1 reference compiler and VM in dependency-free PowerShell. Define ARIA source, semantic IR, bytecode, container, policy, and conformance behavior independently of PowerShell.

## Consequences

ARIA can run immediately in the target environment. PowerShell performance and ergonomics limit the bootstrap, so later VMs may be implemented elsewhere while preserving the same contracts.
