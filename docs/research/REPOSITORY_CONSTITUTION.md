# Repository constitution (recommended, not auto-enabled)

Internal Cortex constitution is not the same as GitHub repository settings.

**Internal constitution** is encoded in invariants, policies, receipts and tests.
It never grants host mutation.

**Repository constitution** is operator-controlled hosting policy.

Recommended, but **not silently enabled** by this pass:

- protected `main`
- required CI status checks on the declared Python matrix
- review before release tags
- no bypass for adaptation machinery or research metadata
- release evidence identity remains reconstructable
- deterministic `docs_check` / claim / invariant validation

Do not treat a passing test or a retained prior as permission to disable
branch protection. Host/operator authorization is required to change
repository settings.
