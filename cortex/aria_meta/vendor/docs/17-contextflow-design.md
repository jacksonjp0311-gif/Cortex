# Contextflow alpha.6 design

Contextflow extends Connectflow with shared meaning before authority.

## Principle

Connection precedes integration. Context precedes authority.

A proposal may not gain executable authority unless ARIA can identify:

1. the intent it answers;
2. the typed context used;
3. the evidence supporting it;
4. its confidence and uncertainty;
5. its declared risks and requested capabilities;
6. explicit operator consent;
7. a deterministic provenance chain.

## Proposed ontology

```aria
context RepositoryReview {
  subject = "jacksonjp0311-gif/ARIA"
  revision = "current-main"
  purpose = "Improve ARIA using ARIA"
}

evidence CurrentSpec {
  source = "docs/16-connectflow.md"
  digest = "sha256:..."
}

proposal ContextflowAlpha6 {
  context = RepositoryReview
  evidence = [CurrentSpec]
  confidence = 0.86
  requires = []
  summary = "Add typed context and provenance before external model access."
}
```

## Runtime lifecycle

```text
connection open
→ intent
→ context opened
→ evidence attached and verified
→ proposal validated
→ confidence recorded
→ consent granted or withheld
→ provenance sealed
→ context closed
→ connection closed
```

Invalid ordering is rejected. Withheld consent closes safely and grants no authority.

## Operator surface

```powershell
.\aria.cmd context .\examples\contextflow.aria -Strict
```

## Acceptance gates

- Preserve all 42 Connectflow conformance gates.
- Add typed context, evidence, proposal, and provenance models.
- Verify evidence digests deterministically.
- Reject confidence outside the language-defined range.
- Prevent authority when context or evidence is incomplete.
- Preserve ontology and provenance through `.ariac` round-trip.
- Emit structured context events for tooling.
- Pass Windows PowerShell 5.1, strict doctor, manifest, and reproducibility gates.
- Do not call an external AI provider in this milestone.
