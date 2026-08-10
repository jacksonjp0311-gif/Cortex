"""v9.0 model-agnostic cognitive circulation.

This module is deliberately small and provider-neutral.  A ``ModelAdapter``
is temporary cognition; Cortex owns the request, public proposal, independent
evaluation, observed outcome, witness, and trajectory receipts.  No adapter
output can grant execution, host mutation, learning, or memory authority.

Only public artifacts are retained.  Unknown adapter fields (including hidden
reasoning or provider-native response objects) are discarded at the boundary.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from . import __version__
from .evaluation import (
    TASK_GATE_FAIL,
    TASK_GATE_PASS,
    TASK_GATE_UNKNOWN,
    TaskContractError,
    TaskEvaluationContract,
    evaluate_task_result,
)
from .witness import ensure_witness_tables, get_witness_result, _result_hash

SCHEMA = "cortex-model-circulation/1.0"
VERSION = "9.0.0"
GLYPH = "◎"
CLAIM_BOUNDARY = (
    "v9.0 model circulation binds a replaceable provider-neutral adapter to a "
    "task context, public proposal, independently selected evaluation, observed "
    "outcome, witness, and trajectory. It is not competence, consciousness, "
    "authority, host mutation, or durable memory admission."
)
RECEIPT_KINDS = (
    "model_invocation",
    "model_proposal",
    "model_evaluation",
    "model_outcome",
    "model_witness",
    "model_trajectory",
)
FORBIDDEN_AUTHORITY = (
    "host_mutate_authorized",
    "execution_authorized",
    "memory_admission_authorized",
    "policy_mutation_authorized",
)


class ModelAdapterError(ValueError):
    """Raised when an adapter violates the provider-neutral contract."""


class ModelAdapter(Protocol):
    """Minimal provider-neutral adapter contract.

    Implementations may use any provider internally, but the core sees only
    these identity fields and a mapping of public response fields.
    """

    provider_family: str
    model_id: str
    model_version: str
    adapter_id: str
    adapter_version: str

    def invoke(self, request: "ModelInvocationRequest") -> Mapping[str, Any]:
        ...


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _json_safe(value: Any) -> Any:
    """Return only JSON-compatible public data, rejecting non-finite values."""

    try:
        encoded = _canonical(value)
        return json.loads(encoded)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ModelAdapterError("adapter output is not finite JSON") from exc


def _nonempty(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ModelAdapterError(f"{field} is required")
    return text


def _adapter_identity(adapter: ModelAdapter) -> dict[str, str]:
    return {
        "provider_family": _nonempty(
            getattr(adapter, "provider_family", ""), "provider_family"
        ),
        "model_id": _nonempty(getattr(adapter, "model_id", ""), "model_id"),
        "model_version": str(getattr(adapter, "model_version", "") or "undeclared"),
        "adapter_id": _nonempty(getattr(adapter, "adapter_id", ""), "adapter_id"),
        "adapter_version": _nonempty(
            getattr(adapter, "adapter_version", ""), "adapter_version"
        ),
    }


def project_task_context(context: Mapping[str, Any]) -> dict[str, Any]:
    """Project a context receipt into a bounded, hashable public view."""

    if not isinstance(context, Mapping):
        raise ModelAdapterError("context receipt must be a mapping")
    for key in ("repo", "repository_id", "session_id", "body_epoch_id"):
        if not str(context.get(key) or "").strip():
            raise ModelAdapterError(f"context missing {key}")
    projection = {
        "schema_version": "cortex-task-context-projection/1.0",
        "repo": str(context["repo"]),
        "repository_id": str(context["repository_id"]),
        "session_id": str(context["session_id"]),
        "turn_id": int(context.get("turn_id") or 0),
        "body_epoch_id": str(context["body_epoch_id"]),
        "context_receipt_hash": str(context.get("receipt_hash") or ""),
        "evidence_digests": [str(x) for x in context.get("evidence_digests") or ()],
        "memory_episode_digests": [
            str(x) for x in context.get("memory_episode_digests") or ()
        ],
        "predictions": _json_safe(dict(context.get("predictions") or {})),
        "unresolved_contradictions": [
            str(x) for x in context.get("unresolved_contradictions") or ()
        ],
        "operating_regime": _json_safe(dict(context.get("operating_regime") or {})),
        "confidence": _json_safe(dict(context.get("confidence") or {})),
        "constitutional_restrictions": [
            str(x) for x in context.get("constitutional_restrictions") or ()
        ],
    }
    projection["projection_hash"] = _sha(
        {key: value for key, value in projection.items() if key != "projection_hash"}
    )
    return projection


@dataclass(frozen=True)
class ModelInvocationRequest:
    """Canonical provider-neutral request identity."""

    repo: str
    repository_id: str
    session_id: str
    turn_id: int
    body_epoch_id: str
    invocation_id: str
    task_contract_hash: str
    context_projection: Mapping[str, Any]
    context_projection_hash: str
    tool_scopes: tuple[str, ...]
    provider_family: str
    model_id: str
    model_version: str
    adapter_id: str
    adapter_version: str
    configuration: Mapping[str, Any]
    requested_at: float

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA,
            "repo": self.repo,
            "repository_id": self.repository_id,
            "session_id": self.session_id,
            "turn_id": int(self.turn_id),
            "body_epoch_id": self.body_epoch_id,
            "invocation_id": self.invocation_id,
            "task_contract_hash": self.task_contract_hash,
            "context_projection": _json_safe(dict(self.context_projection)),
            "context_projection_hash": self.context_projection_hash,
            "tool_scopes": sorted({str(x) for x in self.tool_scopes}),
            "provider_family": self.provider_family,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "configuration": _json_safe(dict(self.configuration)),
            "requested_at": float(self.requested_at),
        }

    @property
    def request_hash(self) -> str:
        return _sha(self.material())

    def to_dict(self) -> dict[str, Any]:
        return {**self.material(), "request_hash": self.request_hash}

    def verify(self) -> dict[str, Any]:
        projection = dict(self.context_projection)
        expected_projection_hash = str(projection.get("projection_hash") or "")
        recomputed_projection_hash = _sha(
            {key: value for key, value in projection.items() if key != "projection_hash"}
        )
        errors: list[str] = []
        if expected_projection_hash != recomputed_projection_hash:
            errors.append("context_projection_content_mismatch")
        if self.context_projection_hash != recomputed_projection_hash:
            errors.append("context_projection_hash_mismatch")
        if self.request_hash != str(self.to_dict().get("request_hash")):
            errors.append("request_hash_mismatch")
        return {
            "valid": not errors,
            "context_hash_valid": not any("context" in e for e in errors),
            "request_hash_valid": "request_hash_mismatch" not in errors,
            "errors": errors,
        }


@dataclass(frozen=True)
class ModelInvocationResult:
    """Sanitized public adapter result; hidden/provider-native fields are absent."""

    request_hash: str
    public_output: Mapping[str, Any]
    proposal: Mapping[str, Any]
    declared_uncertainty: Any
    evidence_citations: tuple[str, ...]
    tool_call_intents: tuple[Mapping[str, Any], ...]
    rationale_public: str
    token_usage: Mapping[str, Any]
    cost: Mapping[str, Any]
    completed_at: float

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA,
            "request_hash": self.request_hash,
            "public_output": _json_safe(dict(self.public_output)),
            "proposal": _json_safe(dict(self.proposal)),
            "declared_uncertainty": _json_safe(self.declared_uncertainty),
            "evidence_citations": list(self.evidence_citations),
            "tool_call_intents": [_json_safe(dict(item)) for item in self.tool_call_intents],
            "rationale_public": self.rationale_public,
            "token_usage": _json_safe(dict(self.token_usage)),
            "cost": _json_safe(dict(self.cost)),
            "completed_at": float(self.completed_at),
        }

    @property
    def response_hash(self) -> str:
        return _sha(self.material())

    def to_dict(self) -> dict[str, Any]:
        return {**self.material(), "response_hash": self.response_hash}

    @classmethod
    def from_adapter(
        cls, request: ModelInvocationRequest, raw: Mapping[str, Any]
    ) -> "ModelInvocationResult":
        if not isinstance(raw, Mapping):
            raise ModelAdapterError("adapter result must be a mapping")
        declared_request_hash = str(raw.get("request_hash") or "")
        if declared_request_hash and declared_request_hash != request.request_hash:
            raise ModelAdapterError("adapter response is bound to a different request")
        public = raw.get("public_output")
        if isinstance(public, str):
            public_output: dict[str, Any] = {"text": public}
        elif isinstance(public, Mapping):
            # Only public, provider-neutral fields cross the boundary.
            public_output = {}
            if "text" in public:
                public_output["text"] = str(public.get("text") or "")
            if "value" in public:
                public_output["value"] = _json_safe(public.get("value"))
            if "data" in public:
                public_output["data"] = _json_safe(public.get("data"))
        else:
            public_output = {}
        if not public_output:
            raise ModelAdapterError("adapter public_output must expose text, value, or data")

        proposal_raw = raw.get("proposal")
        if not isinstance(proposal_raw, Mapping):
            raise ModelAdapterError("adapter proposal must be a mapping")
        action = str(
            proposal_raw.get("proposed_action")
            or proposal_raw.get("action")
            or ""
        ).strip()
        if not action:
            raise ModelAdapterError("adapter proposal requires proposed_action")
        proposal = {
            "interpreted_objective": str(proposal_raw.get("interpreted_objective") or ""),
            "proposed_action": action,
            "requested_permissions": [
                str(x) for x in proposal_raw.get("requested_permissions") or ()
            ],
            "predicted_state_transition": _json_safe(
                dict(proposal_raw.get("predicted_state_transition") or {})
            ),
        }
        uncertainty = raw.get("declared_uncertainty", 1.0)
        uncertainty = _json_safe(uncertainty)
        citations = tuple(str(x) for x in raw.get("evidence_citations") or ())
        intents: list[Mapping[str, Any]] = []
        for intent in raw.get("tool_call_intents") or ():
            if not isinstance(intent, Mapping):
                raise ModelAdapterError("tool_call_intents must contain mappings")
            # Keep only the canonical intent surface; arguments are declarative.
            intents.append(
                {
                    "name": str(intent.get("name") or ""),
                    "arguments": _json_safe(dict(intent.get("arguments") or {})),
                }
            )
        return cls(
            request_hash=request.request_hash,
            public_output=public_output,
            proposal=proposal,
            declared_uncertainty=uncertainty,
            evidence_citations=citations,
            tool_call_intents=tuple(intents),
            rationale_public=str(
                raw.get("rationale_public")
                or "public proposal rationale not supplied; hidden reasoning is not requested"
            ),
            token_usage=_json_safe(dict(raw.get("token_usage") or {})),
            cost=_json_safe(dict(raw.get("cost") or {})),
            completed_at=float(raw.get("completed_at") or time.time()),
        )


class FixtureAdapter:
    """Deterministic adapter used by tests and local integration checks."""

    provider_family = "fixture"
    adapter_id = "cortex.fixture"
    adapter_version = "1"

    def __init__(
        self,
        *,
        model_id: str = "fixture-a",
        model_version: str = "1",
        text: str = "fixture observation",
        action: str = "report the observed fixture result",
    ) -> None:
        self.model_id = _nonempty(model_id, "model_id")
        self.model_version = str(model_version)
        self.text = str(text)
        self.action = _nonempty(action, "action")

    def invoke(self, request: ModelInvocationRequest) -> Mapping[str, Any]:
        if not isinstance(request, ModelInvocationRequest):
            raise ModelAdapterError("fixture requires ModelInvocationRequest")
        return {
            "public_output": {"text": self.text},
            "proposal": {
                "interpreted_objective": "fixture task",
                "proposed_action": self.action,
                "requested_permissions": [],
            },
            "declared_uncertainty": {"overall": 0.0},
            "evidence_citations": [],
            "tool_call_intents": [],
            "rationale_public": "deterministic fixture output",
            "token_usage": {"input": 0, "output": len(self.text)},
            "cost": {"currency": "none", "amount": 0.0},
            "completed_at": time.time(),
            # Deliberately ignored by the core sanitizer.  It is not persisted.
            "provider_specific_payload": {"fixture_internal": True},
            "chain_of_thought": "must never cross the adapter boundary",
        }


def _receipt(
    *,
    kind: str,
    repo: str,
    repository_id: str,
    session_id: str,
    turn_id: int,
    body_epoch_id: str,
    invocation_id: str,
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    created_at = float(time.time())
    body = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "glyph": GLYPH,
        "kind": kind,
        "repo": repo,
        "repository_id": repository_id,
        "session_id": session_id,
        "turn_id": int(turn_id),
        "body_epoch_id": body_epoch_id,
        "invocation_id": invocation_id,
        "event_id": f"evt_{_sha({'kind': kind, 'invocation_id': invocation_id})[:24]}",
        "status": kind,
        "created_at": created_at,
        "advisory_only": True,
        "policy_effect": False,
        "update_authorized": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_mutation_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
        **dict(fields),
    }
    # The symbiotic ledger assigns its own canonical append timestamp.  Keep
    # that storage timestamp in the receipt, but exclude it from the scientific
    # content identity so ledger persistence cannot alter the identity.
    body["content_hash"] = _sha(
        {key: value for key, value in body.items() if key != "created_at"}
    )
    return body


def _verify_receipt_content(receipt: Mapping[str, Any]) -> bool:
    content_hash = str(receipt.get("content_hash") or "")
    ledger_fields = {
        "receipt_hash",
        "subject_receipt_hash",
        "previous_receipt_hash",
        "chain_sequence",
        "ledger_schema_version",
        "inserted",
        "duplicate",
        "chain_valid",
        "created_at",
    }
    material = {
        key: value
        for key, value in receipt.items()
        if key not in ledger_fields and key != "content_hash"
    }
    return bool(content_hash) and _sha(material) == content_hash


def _task_case_commitment(contract: TaskEvaluationContract, case_id: str) -> str:
    return _sha(
        {
            "case_id": str(case_id),
            "contract_hash": contract.contract_hash,
            "evaluator_id": contract.evaluator_id,
        }
    )


def _commit_task_witness(
    store: Any,
    repo: str,
    *,
    contract: TaskEvaluationContract,
    session_id: str,
    body_epoch_id: str,
    case_id: str,
) -> dict[str, Any]:
    """Commit evaluator identity before model invocation/reveal."""

    ensure_witness_tables(store)
    case_commitment = _task_case_commitment(contract, case_id)
    public_cases = [{"id": case_id, "commitment": case_commitment}]
    root = _sha(public_cases)
    witness_id = f"wit_task_{root[:20]}"
    created_at = time.time()
    repository = store.repo(repo)
    repository_id = str(repository["repository_id"] or "") if repository else ""
    if not repository_id:
        raise ModelAdapterError("repository identity is required for witness commitment")
    commitment = {
        "schema_version": "cortex-task-witness/1.0",
        "witness_id": witness_id,
        "case_commitment_hash": root,
        "case_commitments": public_cases,
        "evaluator_identity": contract.evaluator_id,
        "allowed_controller": "model_adapter",
        "created_at": created_at,
        "revealed_at": None,
        "repository_snapshot_hash": None,
        "cortex_commit_hash": __version__,
        "body_epoch_id": body_epoch_id,
        "session_id": session_id,
        "task_contract_hash": contract.contract_hash,
        "repo": repo,
        "repository_id": repository_id,
    }
    existing = store.db.execute(
        "SELECT * FROM witness_commitments WHERE witness_id=?", (witness_id,)
    ).fetchone()
    if existing is not None:
        if str(existing["commitment_root"]) != root:
            raise ModelAdapterError("task witness commitment collision")
        commitment["created_at"] = float(existing["created_at"])
        commitment["revealed_at"] = existing["revealed_at"]
        return commitment
    store.db.execute(
        """INSERT INTO witness_commitments(
             witness_id, commitment_root, case_commitments_json, evaluator_identity,
             created_at, allowed_controller, repository_snapshot_hash,
             cortex_commit_hash, metadata_json
           ) VALUES(?,?,?,?,?,?,?,?,?)""",
        (
            witness_id,
            root,
            _canonical(public_cases),
            contract.evaluator_id,
            created_at,
            "model_adapter",
            None,
            __version__,
            _canonical(
                {
                    "body_epoch_id": body_epoch_id,
                    "session_id": session_id,
                    "task_contract_hash": contract.contract_hash,
                }
            ),
        ),
    )
    store.db.commit()
    return commitment


def _persist_task_witness_result(
    store: Any,
    repo: str,
    *,
    commitment: Mapping[str, Any],
    contract: TaskEvaluationContract,
    outcome: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    invocation_id: str,
) -> dict[str, Any]:
    success = evaluation.get("success")
    state = str(evaluation.get("state") or TASK_GATE_UNKNOWN)
    case_id = str((commitment.get("case_commitments") or [{}])[0].get("id") or "")
    case_hash = str((commitment.get("case_commitments") or [{}])[0].get("commitment") or "")
    repository_id = str(commitment.get("repository_id") or "")
    result = {
        "schema_version": "cortex-task-witness/1.0",
        "glyph": GLYPH,
        "repo": repo,
        "repository_id": repository_id,
        "witness_id": str(commitment["witness_id"]),
        "case_commitment_hash": str(commitment["case_commitment_hash"]),
        "commitment_created_at": float(commitment.get("created_at") or 0.0),
        "evaluator_identity": contract.evaluator_id,
        "body_epoch_id": str(outcome.get("body_epoch_id") or ""),
        "session_id": str(outcome.get("session_id") or ""),
        "task_family": contract.task_type,
        "task_contract_hash": contract.contract_hash,
        "outcome_hash": str(outcome.get("content_hash") or ""),
        "invocation_id": invocation_id,
        "controller": "model_adapter",
        "cases": 1,
        "hits": 1 if state in {TASK_GATE_PASS, TASK_GATE_FAIL} else 0,
        "score": 1.0 if state in {TASK_GATE_PASS, TASK_GATE_FAIL} else 0.0,
        "recall": 1.0 if state in {TASK_GATE_PASS, TASK_GATE_FAIL} else 0.0,
        "success": bool(success is True),
        "chronology_ok": float(commitment.get("created_at") or 0.0) <= time.time(),
        "repository_snapshot_hash": None,
        "cortex_commit_hash": __version__,
        "results": [
            {
                "id": case_id,
                "commitment": case_hash,
                "evaluation_state": state,
            }
        ],
        "created_at": time.time(),
        "revealed_at": time.time(),
        "result_state": (
            "verified_success"
            if state == TASK_GATE_PASS
            else "verified_failure"
            if state == TASK_GATE_FAIL
            else "unknown"
        ),
        "independent": True,
        "claim_boundary": CLAIM_BOUNDARY,
        "version": VERSION,
    }
    result_hash = _result_hash(result)
    result["result_hash"] = result_hash
    result["witness_result_hash"] = result_hash
    existing = store.db.execute(
        "SELECT result_json FROM witness_results WHERE repo=? AND witness_result_hash=?",
        (repo, result_hash),
    ).fetchone()
    if existing is None:
        store.db.execute(
            """INSERT INTO witness_results(
                 witness_result_hash, witness_id, repo, repository_id,
                 body_epoch_id, session_id, task_family, commitment_root,
                 evaluator_identity, controller, cases, hits, score, recall,
                 success, chronology_ok, repository_snapshot_hash,
                 cortex_commit_hash, result_json, created_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                result_hash,
                result["witness_id"],
                repo,
                repository_id,
                result["body_epoch_id"],
                result["session_id"],
                result["task_family"],
                result["case_commitment_hash"],
                result["evaluator_identity"],
                result["controller"],
                result["cases"],
                result["hits"],
                result["score"],
                result["recall"],
                1 if result["success"] else 0,
                1 if result["chronology_ok"] else 0,
                None,
                result["cortex_commit_hash"],
                _canonical(result),
                result["created_at"],
            ),
        )
        store.db.execute(
            "UPDATE witness_commitments SET revealed_at=? WHERE witness_id=?",
            (result["revealed_at"], result["witness_id"]),
        )
        store.db.commit()
        result["canonical_persistence"] = "committed"
    else:
        result["canonical_persistence"] = "duplicate"
    return result


def verify_task_witness_result(
    store: Any,
    repo: str,
    witness_result_hash: str,
    *,
    expected_contract_hash: str,
    expected_outcome_hash: str,
    expected_session_id: str,
    expected_body_epoch_id: str,
) -> dict[str, Any]:
    """Verify generic task witness identity/binding without retrieval semantics."""

    result = get_witness_result(store, repo, witness_result_hash)
    errors: list[str] = []
    if result is None:
        return {
            "valid": False,
            "state": TASK_GATE_UNKNOWN,
            "witness_result_present": False,
            "errors": ["witness_result_not_in_ledger"],
        }
    stored = str(result.get("witness_result_hash") or "")
    recomputed = _result_hash(result)
    if stored != str(witness_result_hash) or recomputed != stored:
        errors.append("witness_result_hash_mismatch")
    if str(result.get("repo") or "") != str(repo):
        errors.append("witness_repository_mismatch")
    commitment = store.db.execute(
        "SELECT * FROM witness_commitments WHERE witness_id=?",
        (str(result.get("witness_id") or ""),),
    ).fetchone()
    if commitment is None:
        errors.append("witness_commitment_missing")
    else:
        try:
            committed_cases = json.loads(str(commitment["case_commitments_json"] or "[]"))
        except (TypeError, ValueError, json.JSONDecodeError):
            committed_cases = []
        if str(commitment["commitment_root"]) != str(result.get("case_commitment_hash") or ""):
            errors.append("witness_commitment_root_mismatch")
        if not isinstance(committed_cases, list) or committed_cases != list(result.get("results") or []):
            # The result may add only the evaluator state to each committed
            # case; compare the immutable id/commitment pair explicitly.
            expected_pairs = [
                {"id": item.get("id"), "commitment": item.get("commitment")}
                for item in committed_cases
                if isinstance(item, Mapping)
            ]
            actual_pairs = [
                {"id": item.get("id"), "commitment": item.get("commitment")}
                for item in result.get("results") or ()
                if isinstance(item, Mapping)
            ]
            if expected_pairs != actual_pairs:
                errors.append("witness_case_binding_mismatch")
        created = float(commitment["created_at"] or 0.0)
        revealed = float(result.get("revealed_at") or 0.0)
        if not created or revealed < created:
            errors.append("witness_chronology_invalid")
        if str(commitment["evaluator_identity"] or "") != str(result.get("evaluator_identity") or ""):
            errors.append("witness_evaluator_mismatch")
        if str(commitment["allowed_controller"] or "") != "model_adapter":
            errors.append("witness_controller_not_allowed")
    if str(result.get("task_contract_hash") or "") != str(expected_contract_hash):
        errors.append("witness_contract_mismatch")
    if str(result.get("outcome_hash") or "") != str(expected_outcome_hash):
        errors.append("witness_outcome_mismatch")
    if str(result.get("session_id") or "") != str(expected_session_id):
        errors.append("witness_session_mismatch")
    if str(result.get("body_epoch_id") or "") != str(expected_body_epoch_id):
        errors.append("witness_epoch_mismatch")
    state = str(result.get("result_state") or "unknown")
    if state not in {"verified_success", "verified_failure"}:
        errors.append("witness_result_semantics_unknown")
    if result.get("independent") is not True:
        errors.append("witness_not_independent")
    return {
        "valid": not errors,
        "state": TASK_GATE_PASS if not errors else TASK_GATE_FAIL,
        "witness_result_present": True,
        "witness_result_hash": stored,
        "errors": sorted(set(errors)),
        "result": result,
    }


def _sanitize_observed_result(observed_result: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(observed_result, Mapping):
        raise ModelAdapterError("observed_result must be a mapping")
    allowed = {
        "text",
        "value",
        "data",
        "status",
        "metrics",
        "external_reference",
        "tool_result",
        "executed",
    }
    sanitized = {
        str(key): _json_safe(value)
        for key, value in observed_result.items()
        if str(key) in allowed
    }
    return sanitized


def _session_context(session: Mapping[str, Any]) -> Mapping[str, Any]:
    receipts = session.get("receipts") if isinstance(session, Mapping) else None
    context = receipts.get("cortex_context") if isinstance(receipts, Mapping) else None
    if not isinstance(context, Mapping):
        raise ModelAdapterError("session has no canonical cortex_context receipt")
    return context


def _append_receipts(store: Any, repo: str, receipts: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    committed: list[dict[str, Any]] = []
    for receipt in receipts:
        committed.append(store.append_symbiotic_receipt(repo, dict(receipt)))
    return committed


def run_model_circulation(
    store: Any,
    repo: str,
    session: Mapping[str, Any],
    *,
    adapter: ModelAdapter,
    task_contract: TaskEvaluationContract,
    observed_result: Mapping[str, Any],
    tool_scopes: Sequence[str] | None = None,
    configuration: Mapping[str, Any] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Run one replaceable-model loop through canonical Cortex receipts."""

    if not isinstance(task_contract, TaskEvaluationContract):
        raise TaskContractError("task_contract must be TaskEvaluationContract")
    context = _session_context(session)
    # Prefer the canonical ledger projection when the session was persisted;
    # this binds the request to the durable context row rather than a caller's
    # mutable in-memory copy.
    try:
        canonical_contexts = [
            row
            for row in store.symbiotic_session_receipts(repo, str(session.get("session_id") or ""))
            if row.get("kind") == "cortex_context"
        ]
    except Exception:
        canonical_contexts = []
    if canonical_contexts:
        context = canonical_contexts[-1]
    projection = project_task_context(context)
    session_id = _nonempty(session.get("session_id"), "session_id")
    repository_id = _nonempty(session.get("repository_id"), "repository_id")
    body_epoch_id = _nonempty(session.get("body_epoch_id"), "body_epoch_id")
    identity = _adapter_identity(adapter)
    turn_id = int(session.get("current_turn_id") or 0) + 1
    invocation_id = f"model_{session_id}_{turn_id}_{_sha(identity)[:12]}"
    request = ModelInvocationRequest(
        repo=str(repo),
        repository_id=repository_id,
        session_id=session_id,
        turn_id=turn_id,
        body_epoch_id=body_epoch_id,
        invocation_id=invocation_id,
        task_contract_hash=task_contract.contract_hash,
        context_projection=projection,
        context_projection_hash=str(projection["projection_hash"]),
        tool_scopes=tuple(str(x) for x in tool_scopes or ()),
        configuration=dict(configuration or {}),
        requested_at=time.time(),
        **identity,
    )
    request_verification = request.verify()
    if not request_verification["valid"]:
        raise ModelAdapterError("invalid canonical model request")
    case_id = f"model_case_{session_id}_{turn_id}"
    commitment = (
        _commit_task_witness(
            store,
            repo,
            contract=task_contract,
            session_id=session_id,
            body_epoch_id=body_epoch_id,
            case_id=case_id,
        )
        if persist
        else {
            "witness_id": f"advisory_{_sha(case_id)[:16]}",
            "case_commitment_hash": _sha(
                [{"id": case_id, "commitment": _task_case_commitment(task_contract, case_id)}]
            ),
            "case_commitments": [
                {"id": case_id, "commitment": _task_case_commitment(task_contract, case_id)}
            ],
            "evaluator_identity": task_contract.evaluator_id,
            "allowed_controller": "model_adapter",
            "created_at": time.time(),
            "repository_id": repository_id,
        }
    )
    raw_result = adapter.invoke(request)
    invocation_result = ModelInvocationResult.from_adapter(request, raw_result)
    observed = _sanitize_observed_result(observed_result)
    evaluation = evaluate_task_result(task_contract, observed)
    proposal_fields = {
        "response_hash": invocation_result.response_hash,
        "request_hash": request.request_hash,
        "context_projection_hash": request.context_projection_hash,
        "task_contract_hash": task_contract.contract_hash,
        "proposal": dict(invocation_result.proposal),
        "declared_uncertainty": invocation_result.declared_uncertainty,
        "evidence_citations": list(invocation_result.evidence_citations),
        "tool_call_intents": [dict(item) for item in invocation_result.tool_call_intents],
        "rationale_public": invocation_result.rationale_public,
        "private_chain_of_thought_stored": False,
    }
    invocation = _receipt(
        kind="model_invocation",
        repo=str(repo),
        repository_id=repository_id,
        session_id=session_id,
        turn_id=turn_id,
        body_epoch_id=body_epoch_id,
        invocation_id=invocation_id,
        fields={
            "request": request.to_dict(),
            "request_hash": request.request_hash,
            "response": invocation_result.to_dict(),
            "response_hash": invocation_result.response_hash,
            "provider_family": identity["provider_family"],
            "model_id": identity["model_id"],
            "model_version": identity["model_version"],
            "adapter_id": identity["adapter_id"],
            "adapter_version": identity["adapter_version"],
            "configuration": dict(request.configuration),
            "context_projection_hash": request.context_projection_hash,
            "task_contract_hash": task_contract.contract_hash,
            "tool_scopes": list(request.tool_scopes),
            "requested_at": request.requested_at,
            "completed_at": invocation_result.completed_at,
            "token_usage": dict(invocation_result.token_usage),
            "cost": dict(invocation_result.cost),
        },
    )
    proposal = _receipt(
        kind="model_proposal",
        repo=str(repo),
        repository_id=repository_id,
        session_id=session_id,
        turn_id=turn_id,
        body_epoch_id=body_epoch_id,
        invocation_id=invocation_id,
        fields=proposal_fields,
    )
    outcome = _receipt(
        kind="model_outcome",
        repo=str(repo),
        repository_id=repository_id,
        session_id=session_id,
        turn_id=turn_id,
        body_epoch_id=body_epoch_id,
        invocation_id=invocation_id,
        fields={
            "observed_result": observed,
            "observed_result_hash": evaluation["observed_result_hash"],
            "evaluation_state": evaluation["state"],
            "success": evaluation["success"],
            "evaluation_criterion": evaluation["criterion"],
            "proposal_content_hash": proposal["content_hash"],
            "invocation_content_hash": invocation["content_hash"],
            "task_contract_hash": task_contract.contract_hash,
            "external_consequence": "observed_input_only",
            "status": (
                "verified_success"
                if evaluation["state"] == TASK_GATE_PASS
                else "verified_failure"
                if evaluation["state"] == TASK_GATE_FAIL
                else "unknown"
            ),
        },
    )
    evaluation_receipt = _receipt(
        kind="model_evaluation",
        repo=str(repo),
        repository_id=repository_id,
        session_id=session_id,
        turn_id=turn_id,
        body_epoch_id=body_epoch_id,
        invocation_id=invocation_id,
        fields={
            "task_contract": task_contract.to_dict(),
            "task_contract_hash": task_contract.contract_hash,
            "evaluator_id": task_contract.evaluator_id,
            "observed_result_hash": evaluation["observed_result_hash"],
            "evaluation": evaluation,
            "proposal_content_hash": proposal["content_hash"],
            "model_success_claim_ignored": True,
        },
    )
    witness_result = (
        _persist_task_witness_result(
            store,
            repo,
            commitment=commitment,
            contract=task_contract,
            outcome=outcome,
            evaluation=evaluation,
            invocation_id=invocation_id,
        )
        if persist
        else {
            "witness_result_hash": "",
            "result_state": "unknown",
            "canonical_persistence": "advisory_only",
        }
    )
    witness = _receipt(
        kind="model_witness",
        repo=str(repo),
        repository_id=repository_id,
        session_id=session_id,
        turn_id=turn_id,
        body_epoch_id=body_epoch_id,
        invocation_id=invocation_id,
        fields={
            "witness_id": commitment["witness_id"],
            "witness_result_hash": witness_result.get("witness_result_hash"),
            "evaluation_content_hash": evaluation_receipt["content_hash"],
            "outcome_content_hash": outcome["content_hash"],
            "task_contract_hash": task_contract.contract_hash,
            "witness_state": (
                TASK_GATE_PASS
                if witness_result.get("result_state") in {"verified_success", "verified_failure"}
                else TASK_GATE_UNKNOWN
            ),
            "independent": True,
        },
    )
    trajectory = _receipt(
        kind="model_trajectory",
        repo=str(repo),
        repository_id=repository_id,
        session_id=session_id,
        turn_id=turn_id,
        body_epoch_id=body_epoch_id,
        invocation_id=invocation_id,
        fields={
            "context_projection_hash": request.context_projection_hash,
            "invocation_content_hash": invocation["content_hash"],
            "proposal_content_hash": proposal["content_hash"],
            "evaluation_content_hash": evaluation_receipt["content_hash"],
            "outcome_content_hash": outcome["content_hash"],
            "witness_content_hash": witness["content_hash"],
            "transition_class": "model_circulation_observation",
            "evaluation_state": evaluation["state"],
        },
    )
    receipts = [invocation, proposal, evaluation_receipt, outcome, witness, trajectory]
    committed: list[dict[str, Any]] = []
    persistence_status = "advisory_only"
    persistence_error = None
    if persist:
        try:
            committed = _append_receipts(store, repo, receipts)
            persistence_status = "committed"
        except Exception as exc:
            persistence_status = "partial_or_failed"
            persistence_error = f"{type(exc).__name__}:{exc}"
    return {
        "schema_version": SCHEMA,
        "version": VERSION,
        "repo": repo,
        "repository_id": repository_id,
        "session_id": session_id,
        "turn_id": turn_id,
        "body_epoch_id": body_epoch_id,
        "invocation_id": invocation_id,
        "request": request.to_dict(),
        "invocation_result": invocation_result.to_dict(),
        "task_contract": task_contract.to_dict(),
        "commitment": commitment,
        "receipts": {
            "model_invocation": invocation,
            "model_proposal": proposal,
            "model_evaluation": evaluation_receipt,
            "model_outcome": outcome,
            "model_witness": witness,
            "model_trajectory": trajectory,
        },
        "witness_result": witness_result,
        "evaluation": evaluation,
        "ledger_receipts": committed,
        "persistence_status": persistence_status,
        "persistence_error": persistence_error,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_mutation_authorized": False,
        "advisory_only": True,
        "policy_effect": False,
        "update_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def verify_model_circulation(
    store: Any,
    repo: str,
    session_id: str,
    *,
    turn_id: int | None = None,
) -> dict[str, Any]:
    """Reload and independently verify one canonical model circulation."""

    rows = store.symbiotic_session_receipts(repo, session_id)
    model_rows = [
        row
        for row in rows
        if row.get("kind") in RECEIPT_KINDS
        and (turn_id is None or int(row.get("turn_id") or -1) == int(turn_id))
    ]
    errors: list[str] = []
    by_kind = {str(row.get("kind")): row for row in model_rows}
    missing = [kind for kind in RECEIPT_KINDS if kind not in by_kind]
    if missing:
        errors.extend(f"missing_{kind}" for kind in missing)
    chain = store.verify_symbiotic_session(repo, session_id)
    if not chain.get("valid"):
        errors.append("symbiotic_chain_invalid")
    for kind, row in by_kind.items():
        if not _verify_receipt_content(row):
            errors.append(f"{kind}_content_hash_invalid")
        if row.get("policy_effect") is not False or row.get("update_authorized") is not False:
            errors.append(f"{kind}_authority_flags_invalid")
        if row.get("host_mutate_authorized") is not False or row.get("execution_authorized") is not False:
            errors.append(f"{kind}_host_or_execution_authority_invalid")
    if missing:
        return {
            "valid": False,
            "errors": sorted(set(errors)),
            "chain": chain,
            "advisory_only": True,
            "policy_effect": False,
            "update_authorized": False,
        }
    invocation = by_kind["model_invocation"]
    proposal = by_kind["model_proposal"]
    evaluation_receipt = by_kind["model_evaluation"]
    outcome = by_kind["model_outcome"]
    witness = by_kind["model_witness"]
    trajectory = by_kind["model_trajectory"]
    try:
        request_fields = {
            "repo",
            "repository_id",
            "session_id",
            "turn_id",
            "body_epoch_id",
            "invocation_id",
            "task_contract_hash",
            "context_projection",
            "context_projection_hash",
            "tool_scopes",
            "provider_family",
            "model_id",
            "model_version",
            "adapter_id",
            "adapter_version",
            "configuration",
            "requested_at",
        }
        request = ModelInvocationRequest(
            **{
                key: value
                for key, value in invocation["request"].items()
                if key in request_fields
            }
        )
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"request_invalid:{type(exc).__name__}")
        request = None
    if request is not None:
        if request.verify()["valid"] is False:
            errors.extend(f"request_{error}" for error in request.verify()["errors"])
        if str(invocation.get("request_hash") or "") != request.request_hash:
            errors.append("invocation_request_binding_invalid")
        if str(request.repo) != str(repo) or str(request.session_id) != str(session_id):
            errors.append("request_identity_binding_invalid")
        response = invocation.get("response")
        if not isinstance(response, Mapping):
            errors.append("response_missing")
        else:
            stored_response_hash = str(response.get("response_hash") or "")
            response_material = {
                key: value for key, value in response.items() if key != "response_hash"
            }
            if not stored_response_hash or _sha(response_material) != stored_response_hash:
                errors.append("response_hash_invalid")
            if stored_response_hash != str(invocation.get("response_hash") or ""):
                errors.append("invocation_response_binding_invalid")
            if str(response.get("request_hash") or "") != request.request_hash:
                errors.append("response_request_binding_invalid")
    try:
        contract = TaskEvaluationContract.from_mapping(evaluation_receipt["task_contract"])
    except (KeyError, TaskContractError) as exc:
        errors.append(f"task_contract_invalid:{type(exc).__name__}")
        contract = None
    if contract is not None:
        if str(evaluation_receipt.get("task_contract_hash") or "") != contract.contract_hash:
            errors.append("task_contract_hash_invalid")
        recomputed = evaluate_task_result(contract, outcome.get("observed_result") or {})
        stored_eval = evaluation_receipt.get("evaluation") or {}
        for key in ("state", "success", "observed_result_hash", "contract_hash"):
            if recomputed.get(key) != stored_eval.get(key):
                errors.append(f"evaluation_{key}_mismatch")
        if str(outcome.get("evaluation_state") or "") != str(recomputed.get("state") or ""):
            errors.append("outcome_evaluation_state_mismatch")
        if outcome.get("success") != recomputed.get("success"):
            errors.append("outcome_success_not_derived")
        canonical_contexts = [
            row for row in rows if row.get("kind") == "cortex_context"
        ]
        if not canonical_contexts:
            errors.append("canonical_context_missing")
        else:
            try:
                canonical_projection = project_task_context(canonical_contexts[-1])
                if canonical_projection != dict(request.context_projection):
                    errors.append("context_projection_not_canonical")
            except ModelAdapterError as exc:
                errors.append(f"canonical_context_invalid:{type(exc).__name__}")
        witness_check = verify_task_witness_result(
            store,
            repo,
            str(witness.get("witness_result_hash") or ""),
            expected_contract_hash=contract.contract_hash,
            expected_outcome_hash=str(outcome.get("content_hash") or ""),
            expected_session_id=str(session_id),
            expected_body_epoch_id=str(outcome.get("body_epoch_id") or ""),
        )
        if not witness_check.get("valid"):
            errors.extend(f"witness_{error}" for error in witness_check.get("errors") or ())
        if str(witness.get("task_contract_hash") or "") != contract.contract_hash:
            errors.append("witness_contract_binding_invalid")
        if str(trajectory.get("witness_content_hash") or "") != str(witness.get("content_hash") or ""):
            errors.append("trajectory_witness_binding_invalid")
    refs = {
        "proposal_content_hash": proposal.get("content_hash"),
        "evaluation_content_hash": evaluation_receipt.get("content_hash"),
        "outcome_content_hash": outcome.get("content_hash"),
        "witness_content_hash": witness.get("content_hash"),
    }
    for key, value in refs.items():
        if trajectory.get(key) != value:
            errors.append(f"trajectory_{key}_invalid")
    if proposal.get("response_hash") != invocation.get("response_hash"):
        errors.append("proposal_response_binding_invalid")
    if outcome.get("proposal_content_hash") != proposal.get("content_hash"):
        errors.append("outcome_proposal_binding_invalid")
    if outcome.get("invocation_content_hash") != invocation.get("content_hash"):
        errors.append("outcome_invocation_binding_invalid")
    return {
        "valid": not errors,
        "errors": sorted(set(errors)),
        "chain": chain,
        "session_id": session_id,
        "turn_id": int(invocation.get("turn_id") or 0),
        "invocation_id": invocation.get("invocation_id"),
        "model_identity": {
            key: invocation.get(key)
            for key in (
                "provider_family",
                "model_id",
                "model_version",
                "adapter_id",
                "adapter_version",
            )
        },
        "witness": witness.get("witness_result_hash"),
        "policy_effect": False,
        "update_authorized": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "advisory_only": True,
    }


__all__ = [
    "CLAIM_BOUNDARY",
    "FixtureAdapter",
    "ModelAdapter",
    "ModelAdapterError",
    "ModelInvocationRequest",
    "ModelInvocationResult",
    "RECEIPT_KINDS",
    "SCHEMA",
    "VERSION",
    "project_task_context",
    "run_model_circulation",
    "verify_model_circulation",
    "verify_task_witness_result",
]
