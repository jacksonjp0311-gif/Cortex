# Capability Authority alpha.19

ARIA no longer treats a matching capability string as sufficient authority.

```text
A matching capability name is not authority.
A verified capability chain is authority.
```

## Token identity

A capability token binds:

- issuer;
- subject;
- resource;
- allowed effects;
- activation and expiration;
- delegation depth;
- parent capability identity;
- nonce;
- single-use semantics;
- reserved signature form;
- SHA-256 token identity.

The token schema is `aria.capability/0.5`.

## Local unsigned phase

Alpha.19 reserves the signature object but accepts only:

```json
{
  "algorithm": "none",
  "value": ""
}
```

This establishes deterministic authority semantics before external keys or certificate infrastructure are introduced.

## Trust policy

A content-addressed issuer policy declares:

```text
trusted root issuers
maximum delegation depth
```

Delegated issuers derive authority from their verified parent rather than appearing directly in the root trust list.

## Attenuation

Delegation may narrow authority. It may never broaden it.

A child token must preserve:

- the parent resource;
- an effect subset;
- an activation interval inside the parent interval;
- the exact parent identity;
- `child.depth = parent.depth + 1`;
- `child.issuer = parent.subject`.

## Time

Authority is evaluated at an explicit decision time.

The verifier rejects:

```text
decision < notBefore
decision >= expiresAt
```

There is no hidden dependency on the host clock in deterministic tests or historical replay.

## Revocation

The revocation ledger is immutable and content-addressed.

A capability is rejected when its revocation time is less than or equal to the authority decision time.

This preserves historical truth:

```text
decision before revocation → may remain valid
decision after revocation  → rejected
```

## Single-use authority

A single-use token is rejected when its nonce is already present in the supplied usage evidence.

Alpha.19 verifies reuse. A later execution ledger will persist nonce consumption as an Event Spine transaction.

## Authority decision

An authority decision records:

- capability identity;
- subject;
- resource;
- requested effects;
- decision time;
- approved or rejected outcome;
- structured reason codes;
- delegation-chain digest;
- issuer-policy identity;
- revocation-ledger identity;
- decision identity.

## Graph execution membrane

`Invoke-AriaAuthorizedGraphRewrite` converts graph-rule capability requirements into effects, verifies the token chain, and only then passes authority to GraphCore.

```text
guarded graph rule
  → requested effects
  → capability chain
  → issuer policy
  → time
  → revocation
  → nonce
  → authority decision
  → graph rewrite
```

A rejected authority decision preserves the original graph digest.

## Rejection codes

Alpha.19 introduces stable rejection categories including:

```text
E_CAP_IDENTITY
E_CAP_ISSUER_UNTRUSTED
E_CAP_SUBJECT
E_CAP_RESOURCE
E_CAP_EFFECT
E_CAP_NOT_ACTIVE
E_CAP_EXPIRED
E_CAP_DELEGATION_BROADEN
E_CAP_DELEGATION_DEPTH
E_CAP_PARENT_UNKNOWN
E_CAP_NONCE_REUSED
E_CAP_REVOKED
```

## Evolution invariant

AI, an operator, or an integration may propose an action. Only a verified authority chain can permit execution.