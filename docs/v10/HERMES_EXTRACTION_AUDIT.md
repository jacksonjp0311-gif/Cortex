# Hermes Extraction Audit

Audit date: 2026-08-27

Upstream: `NousResearch/hermes-agent`

Audited upstream commit: `6dcebea7fc5d0cc4f621eeaddf52b7d877a5f882`

Upstream license: MIT, Copyright (c) 2025 Nous Research

This audit inspected current upstream source before implementation. Cortex does
not vendor Hermes and Alpha 1 copies no Hermes source. The audit extracts
architectural lessons only.

| Subsystem | Upstream path(s) | Dependencies / Cortex equivalent | Disposition | License / coupling risk and reason |
|---|---|---|---|---|
| normalized provider response/tool call | `agent/transports/types.py`, `agent/transports/base.py` | Hermes transports / Cortex v9 `ModelAdapter` | ADAPT | MIT pattern only, low coupling. Cortex uses independent immutable dataclasses and hash laws. |
| conversational tool loop | `agent/conversation_loop.py`, `agent/tool_executor.py` | Hermes runtime helpers / Cortex symbiotic sessions | REIMPLEMENT | Copying would pull a large product graph. Cortex needs a small evidence-ledger loop. |
| tool call/result pairing | `agent/tool_executor.py` | tool schemas and message history / Cortex event chain | ADAPT | MIT behavior lesson, low coupling. Deterministic IDs and one-result-per-request become Cortex invariants. |
| iteration budget / stop | `agent/iteration_budget.py` | runtime configuration / Cortex host grant | ADAPT | MIT pattern only. A hard host-configured limit prevents unbounded circulation. |
| permissions/guardrails | `agent/tool_guardrails.py`, `acp_adapter/permissions.py` | Hermes policy/config / Cortex capability boundary | REIMPLEMENT | High authority coupling if copied. Cortex derives permission only from a host capability grant. |
| terminal/filesystem tools | `tools/terminal_tool.py`, `tools/file_tools.py`, `agent/file_safety.py` | PTY/tool stack / Cortex bounded subprocess + path containment | REIMPLEMENT | Upstream is feature-rich and dependency-heavy; Alpha 1 requires shell-free bounded primitives. |
| streaming/events | `agent/stream_single_writer.py`, `acp_adapter/events.py` | display/ACP / Cortex event sink | ADAPT | MIT concepts only. Alpha 1 emits versioned events; provider deltas remain deferred. |
| interruption/cancellation | `agent/interrupt_compat.py`, `agent/estop.py`, `agent/deadline.py` | UI/session integration / no current Cortex equivalent | DEFER | Requires resumable state and terminal cancellation contracts; unsafe as a partial copy. |
| context compression | `agent/context_compressor.py`, `agent/conversation_compression.py` | provider summarization and prompt cache / Cortex bounded context and memory projection | DEFER | Very high coupling. A second durable summarizer would split epistemic authority. |
| provider transports/SDKs | `agent/transports/*.py`, provider adapter modules | vendor SDKs / Cortex optional adapters | REJECT from core | Provider-specific dependencies must stay optional and outside ontology. |
| memory/learning/curation | `agent/memory_manager.py`, `agent/learning_graph.py`, `agent/curator.py` | Hermes persistence / Cortex memory, evidence, distillation, competence | REJECT | Duplicate durable authority is constitutionally incompatible. |
| skills/plugins | `agent/skill_*.py`, `hermes_cli/agent_plugins.py`, `plugins/` | Hermes extension system / future Cortex projection | DEFER | Must enter through Cortex governance, not persistent foreign learning. |
| delegation/subagents | `agent/subagent_lifecycle.py`, `agent/delegation_context.py` | parallel runtime/session infrastructure | DEFER | Needs child principals, capability attenuation, and lineage receipts first. |
| MCP | `tools/mcp_tool.py`, `tools/setup_mcp_tool.py`, `agent/transports/hermes_tools_mcp_server.py` | MCP libraries / existing Cortex MCP read surface | DEFER | Useful edge adapter after the tool protocol and interruption semantics seal. |
| gateway/messaging | `gateway/` | channel SDKs / future service client | DEFER | Product edge, unrelated to the first headless slice. |
| cron | `cron/` and gateway scheduler surfaces | `croniter`, gateway delivery / no agent-loop requirement | DEFER | Scheduling is authority-bearing and outside Alpha 1. |
| browser/computer use | browser providers, computer-use tools | browser services / future capability adapters | DEFER | External content and interactive mutation need dedicated trust policies. |
| TUI/desktop | `cli.py`, `tui/`, `apps/` | prompt-toolkit/Electron/Tauri / future Cortex Lattice | DEFER | UI must consume events and never own runtime state. |
| JSONL trajectory storage | `agent/trajectory.py` | filesystem JSONL / Cortex immutable SQLite receipt chain | REJECT | Cortex already has stronger canonical storage and reconstruction. |
| hidden reasoning persistence | response reasoning/provider-data surfaces | provider-specific replay state / public Cortex artifacts | REJECT | Cortex never requests or persists private chain-of-thought. |

## Lessons retained

1. Keep the model-facing core narrow; capabilities live at explicit edges.
2. Normalize provider responses before the agent loop sees them.
3. Preserve strict message and tool-result ordering.
4. Bound iterations and tool output.
5. Treat UI, gateway, provider, and plugin surfaces as replaceable consumers.

## No-copy statement

Alpha 1 is an architecture-native Cortex implementation. No upstream file,
function, or class was copied. The upstream repository remains acknowledged
because its mature operational architecture materially informed this design.
