"""v7.1 Constitutional Geometry — four-axis coordinate for consequential state.

q = (e, a, t, w) ∈ {0,1}^4
  e = evidence valid
  a = authority valid
  t = current epoch compatible
  w = independently witnessed

Planes (E/A/I/C/W) describe where an artifact belongs.
This coordinate describes whether it may participate in an operation.

Not consciousness. Not a physical tesseract. Not a universal law.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable, Sequence

SCHEMA = "cortex-constitutional-geometry/1.0"
GLYPH = "◆"

CLAIM = (
    "Cortex v7.1 implements an experimental four-axis constitutional state model "
    "for persistent adaptive software. The axes represent evidence validity, "
    "delegated authority, epoch compatibility, and independent witness. "
    "The model detects illegal composition and compiles lawful next steps. "
    "It is a falsifiable systems hypothesis, not evidence of consciousness, "
    "physical higher-dimensional structure, or a universal law of nature."
)

AXIS_ORDER: tuple[str, ...] = ("evidence", "authority", "epoch", "witness")


class ConstitutionalAxis(str, Enum):
    EVIDENCE = "evidence"
    AUTHORITY = "authority"
    EPOCH = "epoch"
    WITNESS = "witness"


@dataclass(frozen=True)
class AxisAssessment:
    valid: bool
    reason: str
    receipts: tuple[str, ...] = ()
    epoch_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConstitutionalCoordinate:
    evidence: AxisAssessment
    authority: AxisAssessment
    epoch: AxisAssessment
    witness: AxisAssessment

    def bits(self) -> tuple[int, int, int, int]:
        return (
            int(self.evidence.valid),
            int(self.authority.valid),
            int(self.epoch.valid),
            int(self.witness.valid),
        )

    def axis(self, name: str) -> AxisAssessment:
        n = name.casefold().strip()
        if n == "evidence":
            return self.evidence
        if n == "authority":
            return self.authority
        if n == "epoch":
            return self.epoch
        if n == "witness":
            return self.witness
        raise KeyError(f"unknown axis: {name}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA,
            "glyph": GLYPH,
            "bits": list(self.bits()),
            "evidence": self.evidence.to_dict(),
            "authority": self.authority.to_dict(),
            "epoch": self.epoch.to_dict(),
            "witness": self.witness.to_dict(),
            "claim_boundary": CLAIM,
        }


def hamming_distance(
    left: ConstitutionalCoordinate | Sequence[int],
    right: ConstitutionalCoordinate | Sequence[int],
) -> int:
    lb = left.bits() if isinstance(left, ConstitutionalCoordinate) else tuple(int(x) for x in left)
    rb = right.bits() if isinstance(right, ConstitutionalCoordinate) else tuple(int(x) for x in right)
    if len(lb) != 4 or len(rb) != 4:
        raise ValueError("coordinates must be length-4 bit tuples")
    return sum(int(a != b) for a, b in zip(lb, rb))


def changed_axes(
    left: ConstitutionalCoordinate | Sequence[int],
    right: ConstitutionalCoordinate | Sequence[int],
) -> tuple[str, ...]:
    lb = left.bits() if isinstance(left, ConstitutionalCoordinate) else tuple(int(x) for x in left)
    rb = right.bits() if isinstance(right, ConstitutionalCoordinate) else tuple(int(x) for x in right)
    return tuple(AXIS_ORDER[i] for i in range(4) if lb[i] != rb[i])


def coordinate_from_bits(
    bits: Sequence[int],
    *,
    reasons: Sequence[str] | None = None,
    epoch_id: str | None = None,
) -> ConstitutionalCoordinate:
    """Build a coordinate from four bits (0/1). Reasons optional per axis."""
    if len(bits) != 4:
        raise ValueError("bits must be length 4")
    b = tuple(1 if int(x) else 0 for x in bits)
    rs = list(reasons) if reasons else ["bit_set" if x else "bit_clear" for x in b]
    while len(rs) < 4:
        rs.append("unspecified")
    return ConstitutionalCoordinate(
        evidence=AxisAssessment(bool(b[0]), str(rs[0]), epoch_id=epoch_id),
        authority=AxisAssessment(bool(b[1]), str(rs[1]), epoch_id=epoch_id),
        epoch=AxisAssessment(bool(b[2]), str(rs[2]), epoch_id=epoch_id),
        witness=AxisAssessment(bool(b[3]), str(rs[3]), epoch_id=epoch_id),
    )


def enumerate_coordinates() -> list[dict[str, Any]]:
    """All 16 coordinates, deterministic order (0..15 as bit masks)."""
    out: list[dict[str, Any]] = []
    for i in range(16):
        bits = (
            (i >> 3) & 1,
            (i >> 2) & 1,
            (i >> 1) & 1,
            i & 1,
        )
        c = coordinate_from_bits(bits, reasons=[f"enum_{AXIS_ORDER[j]}" for j in range(4)])
        out.append(
            {
                "index": i,
                "bits": list(bits),
                "label": f"({bits[0]},{bits[1]},{bits[2]},{bits[3]})",
            }
        )
    return out


def enumerate_coordinates_hash() -> str:
    import hashlib
    import json

    material = json.dumps(enumerate_coordinates(), sort_keys=True)
    return hashlib.sha256(material.encode()).hexdigest()


def assess_axes(
    *,
    evidence_valid: bool,
    evidence_reason: str = "",
    evidence_receipts: Iterable[str] = (),
    authority_valid: bool,
    authority_reason: str = "",
    authority_receipts: Iterable[str] = (),
    epoch_valid: bool,
    epoch_reason: str = "",
    epoch_receipts: Iterable[str] = (),
    epoch_id: str | None = None,
    witness_valid: bool,
    witness_reason: str = "",
    witness_receipts: Iterable[str] = (),
) -> ConstitutionalCoordinate:
    """Compose independent axis assessments into a coordinate."""
    return ConstitutionalCoordinate(
        evidence=AxisAssessment(
            bool(evidence_valid),
            evidence_reason or ("evidence_ok" if evidence_valid else "evidence_invalid"),
            tuple(evidence_receipts),
            epoch_id=epoch_id,
        ),
        authority=AxisAssessment(
            bool(authority_valid),
            authority_reason or ("authority_ok" if authority_valid else "authority_invalid"),
            tuple(authority_receipts),
            epoch_id=epoch_id,
        ),
        epoch=AxisAssessment(
            bool(epoch_valid),
            epoch_reason or ("epoch_ok" if epoch_valid else "epoch_incompatible"),
            tuple(epoch_receipts),
            epoch_id=epoch_id,
        ),
        witness=AxisAssessment(
            bool(witness_valid),
            witness_reason or ("witness_ok" if witness_valid else "witness_missing"),
            tuple(witness_receipts),
            epoch_id=epoch_id,
        ),
    )


def assess_repo_coordinate(
    store: Any,
    repo: str,
    *,
    capability: Any | None = None,
    require_witness: bool = False,
    witness_ok: bool | None = None,
    authority_ok: bool | None = None,
) -> ConstitutionalCoordinate:
    """Observe-only assessment of a repository's four-axis state.

    Never seals epochs. Never issues capabilities. Never mutates.
    """
    from .epoch import observe_current_epoch, require_current_epoch

    epoch_id: str | None = None
    epoch_valid = False
    epoch_reason = "epoch_absent"
    epoch_receipts: tuple[str, ...] = ()
    try:
        ep = require_current_epoch(store, repo)
        epoch_id = ep.epoch_id
        epoch_valid = True
        epoch_reason = "epoch_verified"
        epoch_receipts = (ep.receipt_hash[:16],)
    except Exception as exc:
        # Fall back to observe for partial reporting
        obs = observe_current_epoch(store, repo)
        if obs.get("present") and obs.get("verified"):
            epoch_valid = True
            epoch_id = str(obs.get("epoch_id") or "")
            epoch_reason = "epoch_verified_observe"
            epoch_receipts = (str(obs.get("receipt_hash") or "")[:16],)
        else:
            epoch_valid = False
            epoch_reason = f"epoch_invalid:{type(exc).__name__}"
            epoch_id = obs.get("epoch_id")  # type: ignore[assignment]

    # Evidence: certificate/manifest present and epoch evidence root non-empty
    evidence_valid = False
    evidence_reason = "evidence_unknown"
    evidence_receipts: tuple[str, ...] = ()
    try:
        row = store.repo(repo)
        if row and (row["manifest_hash"] or ""):
            evidence_valid = True
            evidence_reason = "manifest_present"
            evidence_receipts = (str(row["manifest_hash"])[:16],)
        cert = None
        try:
            cert = store.latest_bootstrap(repo)
        except Exception:
            cert = None
        if cert and (cert.get("certificate") if isinstance(cert, dict) else True):
            if evidence_valid:
                evidence_reason = "manifest_and_certificate"
            else:
                evidence_valid = True
                evidence_reason = "certificate_present"
        if epoch_id and not evidence_valid:
            evidence_reason = "no_manifest_or_certificate"
    except Exception as exc:
        evidence_reason = f"evidence_error:{type(exc).__name__}"

    # Authority: explicit capability check or provided flag
    auth_valid = False
    auth_reason = "no_capability"
    auth_receipts: tuple[str, ...] = ()
    if authority_ok is not None:
        auth_valid = bool(authority_ok)
        auth_reason = "authority_flag" if auth_valid else "authority_flag_false"
    elif capability is not None:
        try:
            from .capabilities import ExecutionCapability, validate_epoch_capability

            cap = (
                capability
                if isinstance(capability, ExecutionCapability)
                else ExecutionCapability.from_dict(capability)
            )
            d = validate_epoch_capability(
                cap,
                repo=repo,
                operation="audit_append",
                body_epoch_id=epoch_id or "",
            )
            # capability present + epoch match for stable ops is weak authority signal
            if cap.repo == repo and (not cap.body_epoch_id or cap.body_epoch_id == epoch_id):
                auth_valid = True
                auth_reason = "capability_epoch_bound"
                auth_receipts = (cap.capability_id, cap.receipt_hash[:16])
            else:
                auth_valid = False
                auth_reason = d.reason or "capability_mismatch"
        except Exception as exc:
            auth_reason = f"authority_error:{type(exc).__name__}"
    else:
        # Without capability object: authority is not assumed valid
        auth_valid = False
        auth_reason = "capability_not_provided"

    # Witness: explicit flag, or check recent commitment for repo epoch
    wit_valid = False
    wit_reason = "witness_not_required"
    wit_receipts: tuple[str, ...] = ()
    if witness_ok is not None:
        wit_valid = bool(witness_ok)
        wit_reason = "witness_flag" if wit_valid else "witness_flag_false"
    elif require_witness:
        try:
            rows = store.db.execute(
                """
                SELECT commitment_root, created_at FROM witness_commitments
                ORDER BY created_at DESC LIMIT 1
                """
            ).fetchall()
            if rows:
                wit_valid = True
                wit_reason = "witness_commitment_present"
                wit_receipts = (str(rows[0]["commitment_root"])[:16],)
            else:
                wit_valid = False
                wit_reason = "witness_commitment_absent"
        except Exception:
            wit_valid = False
            wit_reason = "witness_table_unavailable"
    else:
        # Default: witness axis reports present commitment if any (informative)
        try:
            rows = store.db.execute(
                "SELECT commitment_root FROM witness_commitments ORDER BY created_at DESC LIMIT 1"
            ).fetchall()
            if rows:
                wit_valid = True
                wit_reason = "witness_commitment_present"
                wit_receipts = (str(rows[0]["commitment_root"])[:16],)
            else:
                wit_valid = False
                wit_reason = "witness_commitment_absent"
        except Exception:
            wit_valid = False
            wit_reason = "witness_unavailable"

    return assess_axes(
        evidence_valid=evidence_valid,
        evidence_reason=evidence_reason,
        evidence_receipts=evidence_receipts,
        authority_valid=auth_valid,
        authority_reason=auth_reason,
        authority_receipts=auth_receipts,
        epoch_valid=epoch_valid,
        epoch_reason=epoch_reason,
        epoch_receipts=epoch_receipts,
        epoch_id=epoch_id,
        witness_valid=wit_valid,
        witness_reason=wit_reason,
        witness_receipts=wit_receipts,
    )
