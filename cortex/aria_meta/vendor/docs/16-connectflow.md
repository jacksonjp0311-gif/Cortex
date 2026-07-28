# Connectflow

Connectflow is ARIA `0.1.0-alpha.5`, language specification `0.4.0`.

Its purpose is to establish connection before integration. ARIA now models a human and an agent as principals joined by a declared protocol rather than treating an AI provider as an unrestricted function call.

## Contract

```aria
connection HumanAI {
  operator = "human"
  agent = "Architect"
  protocol = "intent-proposal-consent"
}
```

The declaration is preserved in semantic IR, deterministic bytecode, and the `.ariac` container.

## Lifecycle

```aria
connect HumanAI
intent HumanAI <- "State the human goal."
propose HumanAI <- "State the agent proposal."
consent HumanAI <- true
disconnect HumanAI
```

The local VM enforces the lifecycle. Messages before `connect`, proposals before intent, consent before proposal, and termination without `disconnect` are rejected.

A consent value of `false` is not a runtime failure. It is rendered as `REJECT`, closes safely, and grants no authority.

## Operator surface

`aria connect` compiles, verifies, and executes the connection program through the normal ARIA pipeline. The CLI renders the relationship as a descending Traceflow tree while retaining deterministic structured events for tooling.

## Boundary

Connectflow does not call an AI model. It establishes the ontology and consent protocol that any future provider-neutral bridge must obey.
