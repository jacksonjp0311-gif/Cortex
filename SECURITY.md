# Security

Report a suspected Cortex vulnerability privately to the repository owner
before publishing exploit details. Never place credentials, bearer tokens,
provider API keys, private keys, or host-vault material in an issue, log,
benchmark artifact, receipt, or commit.

## Secret storage boundary

Provider credentials are host secrets. Cortex resolves them from the operating
system credential store or the documented provider environment variables. They
must not enter ordinary configuration, Git history, event streams, model
context, evidence ledgers, trajectories, or benchmark artifacts.

## Public cryptographic commitments

Some answer-sealed benchmark artifacts contain SHA-256 commitments. A
commitment is a one-way public digest used to bind host-private evaluator
material; it is not the material itself and cannot authenticate to a provider.

GitGuardian reported two `Generic High Entropy Secret` findings in commit
`504ef3e` for the alpha.20 artifact. The repository audit established that both
values are 64-character SHA-256 commitments, not OpenAI, xAI, OpenRouter,
GitHub, AWS, or private-key credentials. The configured provider credential's
direct digest did not match either commitment, and a prompt-free provider
model-catalog validation remained connected. The two exact public digests are
allowlisted in `.gitguardian.yaml`; detectors and paths remain enabled.

The historical GitGuardian incidents should be marked **false positive** in
the dashboard. Do not mark them resolved as rotated credentials, because no
credential was present or rotated.
