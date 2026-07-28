# Coreflow Cross-Domain Discoveries

This note records design discoveries from compiler construction, capability security, workflow systems, AI-agent orchestration, and operator-interface design.

## 1. Visual execution needs structured events

A polished CLI cannot reliably infer meaning from arbitrary text. ARIA therefore carries `signal` and agent-dispatch events as typed VM output. The same event stream can drive a terminal, GUI, recorder, or agent bridge without scraping ANSI text.

## 2. Structured control improves both safety and visualization

Nested `IF` and `REPEAT` bytecode makes branch topology explicit. That simplifies stack verification, prevents malformed jump targets, and gives the future glyphic debugger a direct execution tree.

## 3. AI dispatch must begin as data, not authority

An agent task is first represented as a deterministic event. Model invocation, tool access, and mutation authority can be attached later through separate capabilities. This prevents an AI integration from becoming an implicit bypass around the language runtime.

## 4. Memory is part of the type boundary

Persisted state can outlive the compiler version that created it. Revalidating durable values against the compiled memory type table prevents stale or tampered state from silently entering execution.

## 5. Human-readable bytecode accelerates an experimental language

Canonical JSON is not the densest encoding, but it makes alpha artifacts inspectable, reproducible, diffable after decompression, and easier for alternate tooling to implement. Compression recovers much of the storage overhead while the instruction contract is still evolving.

## 6. A language and its operator CLI should co-evolve

The CLI is not merely decoration when it renders compiler gates and VM events that originate in the language. ARIA's operator stream is therefore treated as a projection of verified execution state, while raw diagnostics remain available for debugging.
