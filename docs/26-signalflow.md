# Signalflow: projected operation receipts

Signalflow turns buffered work into measured semantic evidence.

```text
⧖ pending github.push · elapsed:1.8s
◆ operation.complete · github.push · 1842ms · 4281B · exit:0
```

The pending frame states only that the process remains alive. The terminal
receipt records:

- operation identity and operation-local order;
- authority membrane (`local`, `remote`, `verification`, or `runtime`);
- measured duration;
- stdout, stderr, and total byte counts;
- terminal exit code;
- heartbeat count;
- completion or fracture;
- cue, projection, previous-event, and event digests.

Raw stdout and stderr are not copied into the event journal.

## Per-item activation

`Invoke-AriaBufferedItem` applies the same contract to one logical item.
`Invoke-AriaBufferedSequence` starts a distinct event operation for every item,
so aggregate work cannot hide child identity or outcome.

## Signal theory

```text
source → pending while live → measured receipt
```

No timed carousel may insert unobserved semantic phases. A richer producer can
emit explicit events, but rendering remains a projection of those events.

CI and reduced-motion profiles suppress temporal frames while retaining
deterministic text and machine records.
