# Cortex development and version control

This guide is for maintainers, contributors, and people who want to run the
Cortex engine from source. Most users should start with the human-first
installation in the [README](../README.md); you do not need to clone this
repository to attach Cortex to another project.

## Clone the engine

```bash
git clone https://github.com/jacksonjp0311-gif/Cortex.git
cd Cortex
```

Create an isolated environment and install the local checkout:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS / Linux:      source .venv/bin/activate
python -m pip install -e .
```

Optional semantic-model support is available with:

```bash
python -m pip install -e ".[semantic]"
```

## Verify a checkout

Run the same checks used during development before opening a change:

```bash
python -m compileall -q cortex tests
python -m pytest -q
```

For a narrower iteration, run the tests nearest to the code you changed first,
then run the full suite before publishing.

## Make a change safely

1. Start from an up-to-date `main` branch.
2. Read `AGENTS.md` and run the Cortex activation ritual for the task.
3. Keep source, tests, documentation, and release notes in the same change
   when behavior changes.
4. Treat repository source, tests, compiler output, and current runtime
   evidence as more authoritative than learned memory or telemetry.
5. Do not promote an advisory field, coherence score, or memory receipt into
   routing, learning, cadence, policy, or host mutation without a declared
   evidence gate.

Typical version-control flow:

```bash
git switch -c docs/clear-cortex-introduction
git diff --check
git add README.md docs/DEVELOPMENT.md
git commit -m "docs: make Cortex introduction human-first"
git push -u origin docs/clear-cortex-introduction
```

Direct pushes to `main` are reserved for explicitly authorized maintenance
work. Otherwise, open a pull request and wait for the required checks.

## Release discipline

- Update `cortex/__init__.py`, `pyproject.toml`, and `CHANGELOG.md` together.
- Add or update the relevant phase document under `docs/intelligence/`.
- Run the focused tests, the full suite, and any release receipt required by
  the phase.
- Inspect `git status --short --branch` before pushing so unrelated local files
  remain untouched.
- Never claim a green runtime or CI result while a required gate is pending.

The full project policies are in
[`CONTRIBUTING.md`](../CONTRIBUTING.md), [`AGENTS.md`](../AGENTS.md), and
[`docs/SECURITY.md`](SECURITY.md).
