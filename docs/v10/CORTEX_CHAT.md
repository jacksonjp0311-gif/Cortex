# Cortex Chat

A conversation has a stable local Cortex session identity. Each turn uses the
current reasoning engine but circulates through `NativeAgentRuntime`, projects
Cortex context, emits public events, and seals a canonical trajectory.

The provider-neutral request includes a public Cortex runtime context in the
system message: Cortex identity, repository identity, the canonical task
projection, constitutional restrictions, and the exact bounded capabilities
granted for the turn. The reasoning engine can therefore describe its real
Cortex attachment and inspect the repository when read tools are enabled; a
context hash is never mistaken for delivery of the context body.

Changing from one model or provider to another records a provenance event and
preserves the Cortex session. Provider conversation storage is not Cortex
memory and is not used for continuity.

SSE carries the alpha.1 event vocabulary plus `model.delta` and interruption
events. The UI renders only public output. The stop action sets the same
cancellation token observed by the model adapter and agent loop; it does not
merely hide output.

Conversation messages are local session records. They do not automatically
become admitted memory, competence, evidence truth, preferences, or policy.
The Memory and Competence panels therefore show explicit zero/inactive states
until those governed projection paths actually participate.

Context utilization is an explicitly labeled estimate derived from the
serialized canonical projection. It is not provider-reported token usage.

Archive closes the mutable conversation projection while retaining immutable
trajectory evidence. Resuming or switching models never rewrites prior
receipts.
