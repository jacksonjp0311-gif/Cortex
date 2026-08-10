"""Repository-native replay and typed task evaluation.

The retrieval corpus evaluator below remains unchanged for the historical
GCMT suite.  v9.0 adds a small provider-neutral task contract at the bottom of
this module.  It evaluates an externally observed result, never a model's
self-reported success bit.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from .neuron import activate_interlink
from .retrieval import query


def load_corpus(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        payload = {"schema_version": "1.0", "cases": payload}
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        raise ValueError("Evaluation corpus must contain a cases list")
    return payload


def evaluate_retrieval_corpus(
    store: Any,
    corpus: dict[str, Any],
    *,
    default_repo: str | None = None,
    limit: int = 8,
    top_k: int = 3,
) -> dict[str, Any]:
    """Path-recall regression: expected paths must appear in top-k hits."""

    results: list[dict[str, Any]] = []
    hits_at_k = 0
    for index, case in enumerate(corpus.get("cases") or [], 1):
        repo = str(case.get("repo") or default_repo or "")
        if not repo or not store.repo(repo):
            raise ValueError(f"Retrieval case {index} has no attached repository")
        query_text = str(case.get("query") or case.get("task") or "").strip()
        expected = [str(path) for path in case.get("expected_paths", [])]
        if not query_text or not expected:
            raise ValueError(f"Retrieval case {index} needs query and expected_paths")
        hits = query(store, repo, query_text, limit=limit)
        paths = [hit.path.replace("\\", "/") for hit in hits[:top_k]]
        expected_norm = [path.replace("\\", "/") for path in expected]
        found = any(
            any(path == exp or path.endswith(exp) or exp.endswith(path) for exp in expected_norm)
            for path in paths
        )
        if found:
            hits_at_k += 1
        results.append(
            {
                "id": case.get("id") or f"case-{index}",
                "query": query_text,
                "expected_paths": expected_norm,
                "returned_paths": paths,
                "hit_at_k": found,
            }
        )
    total = max(1, len(results))
    recall = hits_at_k / total
    return {
        "schema_version": "cortex-retrieval-eval/1.0",
        "glyph": "⌖",
        "top_k": top_k,
        "cases": len(results),
        "hits_at_k": hits_at_k,
        "recall_at_k": round(recall, 6),
        "passed": recall >= float(corpus.get("minimum_recall_at_k", 0.5)),
        "results": results,
        "claim_boundary": (
            corpus.get("claim_boundary")
            or "Path-recall regression only; not universal answer quality."
        ),
    }


# ---------------------------------------------------------------------------
# v9.0 provider-neutral task contracts
# ---------------------------------------------------------------------------

TASK_CONTRACT_SCHEMA = "cortex-task-contract/1.0"
TASK_EVALUATION_SCHEMA = "cortex-task-evaluation/1.0"
TASK_GATE_PASS = "pass"
TASK_GATE_FAIL = "fail"
TASK_GATE_UNKNOWN = "unknown"
TASK_TYPES = frozenset({"text_contains", "field_equals", "field_contains"})


class TaskContractError(ValueError):
    """Raised when a task contract or observed result is not well typed."""


def _task_canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _task_sha(value: Any) -> str:
    return hashlib.sha256(_task_canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TaskEvaluationContract:
    """A serializable evaluator selected independently of model output.

    The contract contains no executable callback.  This keeps the canonical
    object provider-neutral and makes its semantics replayable from durable
    data.  ``expected_value`` is deliberately public task specification, not
    hidden reasoning or a model-provided metric.
    """

    contract_id: str
    task_type: str = "text_contains"
    target_field: str = "text"
    expected_value: Any = ""
    evaluator_id: str = "cortex.task.evaluator.v1"
    version: str = "1"

    def __post_init__(self) -> None:
        if not str(self.contract_id).strip():
            raise TaskContractError("contract_id is required")
        if str(self.task_type) not in TASK_TYPES:
            raise TaskContractError(f"unsupported task_type: {self.task_type}")
        if not str(self.target_field).strip():
            raise TaskContractError("target_field is required")
        if not str(self.evaluator_id).strip():
            raise TaskContractError("evaluator_id is required")
        if self.task_type == "text_contains":
            expected_items = (
                list(self.expected_value)
                if isinstance(self.expected_value, (list, tuple))
                else [self.expected_value]
            )
            if not expected_items or any(str(item) == "" for item in expected_items):
                raise TaskContractError("text_contains requires a nonempty expected_value")
        # Reject non-JSON values at construction time.  In particular this
        # prevents an adapter from smuggling executable evaluator state.
        try:
            _task_canonical(self.expected_value)
        except (TypeError, ValueError) as exc:
            raise TaskContractError("expected_value must be JSON-compatible") from exc

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "TaskEvaluationContract":
        if not isinstance(value, Mapping):
            raise TaskContractError("task contract must be a mapping")
        return cls(
            contract_id=str(value.get("contract_id") or ""),
            task_type=str(value.get("task_type") or "text_contains"),
            target_field=str(value.get("target_field") or "text"),
            expected_value=value.get("expected_value", ""),
            evaluator_id=str(value.get("evaluator_id") or "cortex.task.evaluator.v1"),
            version=str(value.get("version") or "1"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": TASK_CONTRACT_SCHEMA,
            "contract_id": str(self.contract_id),
            "task_type": str(self.task_type),
            "target_field": str(self.target_field),
            "expected_value": self.expected_value,
            "evaluator_id": str(self.evaluator_id),
            "version": str(self.version),
        }

    @property
    def contract_hash(self) -> str:
        return _task_sha(self.to_dict())


def evaluate_task_result(
    contract: TaskEvaluationContract,
    observed_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate a public observed result under a predeclared contract.

    The result's ``success``/``verified``/``score`` fields are never read as
    authority.  Only the canonical contract and the supplied externally
    observed field are used.  Missing or malformed evidence is ``unknown``.
    """

    if not isinstance(contract, TaskEvaluationContract):
        raise TaskContractError("contract must be TaskEvaluationContract")
    if not isinstance(observed_result, Mapping):
        return {
            "schema_version": TASK_EVALUATION_SCHEMA,
            "state": TASK_GATE_UNKNOWN,
            "success": None,
            "criterion": "observed_result_mapping_required",
            "evaluator_id": contract.evaluator_id,
            "contract_hash": contract.contract_hash,
            "observed_result_hash": _task_sha({"invalid": True}),
            "independent": True,
        }

    field = observed_result.get(contract.target_field)
    expected = contract.expected_value
    criterion = f"{contract.task_type}:{contract.target_field}"
    success: bool | None
    if field is None:
        success = None
        state = TASK_GATE_UNKNOWN
        criterion = f"{criterion}:missing"
    elif contract.task_type == "text_contains":
        if not isinstance(field, str):
            success = None
            state = TASK_GATE_UNKNOWN
            criterion = f"{criterion}:text_required"
        else:
            expected_items = (
                list(expected)
                if isinstance(expected, (list, tuple))
                else [str(expected)]
            )
            success = all(str(item) in field for item in expected_items)
            state = TASK_GATE_PASS if success else TASK_GATE_FAIL
    elif contract.task_type == "field_equals":
        success = field == expected
        state = TASK_GATE_PASS if success else TASK_GATE_FAIL
    elif contract.task_type == "field_contains":
        try:
            success = expected in field
        except (TypeError, ValueError):
            success = None
        state = (
            TASK_GATE_UNKNOWN
            if success is None
            else TASK_GATE_PASS
            if success
            else TASK_GATE_FAIL
        )
    else:  # Defensive if a mutable/forged instance bypassed __post_init__.
        success = None
        state = TASK_GATE_UNKNOWN
        criterion = f"{criterion}:unsupported"

    return {
        "schema_version": TASK_EVALUATION_SCHEMA,
        "state": state,
        "success": success,
        "criterion": criterion,
        "evaluator_id": contract.evaluator_id,
        "contract_hash": contract.contract_hash,
        "observed_result_hash": _task_sha(dict(observed_result)),
        "independent": True,
        "model_self_report_ignored": True,
    }


def _rank(paths: list[str], expected: set[str]) -> int | None:
    for index, path in enumerate(paths, 1):
        if path in expected:
            return index
    return None


def _metrics(results: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    eligible = [item for item in results if item["expected_paths"]]
    ranks = [item[mode]["rank"] for item in eligible]
    found = [rank for rank in ranks if rank is not None]
    recall = len(found) / max(1, len(eligible))
    mrr = mean([1.0 / rank if rank else 0.0 for rank in ranks]) if ranks else 0.0
    boundary_cases = [item for item in results if item["forbidden_paths"]]
    boundary_errors = sum(bool(item[mode]["forbidden_fired"]) for item in boundary_cases)
    abstention_cases = [item for item in results if item["should_abstain"]]
    abstention_correct = sum(item[mode]["abstained"] for item in abstention_cases)
    return {
        "cases": len(results),
        "recall_at_node_budget": round(recall, 6),
        "mean_reciprocal_rank": round(mrr, 6),
        "boundary_separation": round(
            1.0 - boundary_errors / max(1, len(boundary_cases)), 6
        ),
        "abstention_accuracy": round(
            abstention_correct / max(1, len(abstention_cases)), 6
        ),
    }


def evaluate_corpus(
    store: Any,
    corpus: dict[str, Any],
    *,
    default_repo: str | None = None,
    limit: int = 24,
    semantic_scan_limit: int = 5000,
) -> dict[str, Any]:
    """Compare structural priors with learned weights on identical replay cases."""
    results: list[dict[str, Any]] = []
    for index, case in enumerate(corpus["cases"], 1):
        repo = str(case.get("repo") or default_repo or "")
        if not repo or not store.repo(repo):
            raise ValueError(f"Case {index} has no attached repository")
        task = str(case.get("task") or case.get("query") or "").strip()
        if not task:
            raise ValueError(f"Case {index} has no task")
        expected = {str(path) for path in case.get("expected_paths", [])}
        forbidden = {str(path) for path in case.get("forbidden_paths", [])}
        should_abstain = bool(case.get("should_abstain", False))
        hits = query(
            store,
            repo,
            task,
            limit=limit,
            semantic_scan_limit=semantic_scan_limit,
        )
        confidence = max(
            (float(hit.metadata.get("semantic_similarity", 0.0)) for hit in hits),
            default=0.0,
        )
        modes: dict[str, Any] = {}
        for mode in ("base", "learned"):
            packet = activate_interlink(
                store,
                repo,
                task,
                hits,
                weight_mode=mode,
                record=False,
                plasticity_enabled=False,
                governance_mode="read_only",
            )
            fired = list(packet.fired_paths)
            modes[mode] = {
                "rank": _rank(fired, expected),
                "fired_paths": fired,
                "forbidden_fired": sorted(forbidden.intersection(fired)),
                "abstained": not hits or confidence < float(case.get("abstain_below", 0.05)),
                "state_hash": packet.state_hash,
            }
        results.append(
            {
                "case_id": str(case.get("id") or f"case-{index}"),
                "category": str(case.get("category") or "source_recall"),
                "repo": repo,
                "task": task,
                "expected_paths": sorted(expected),
                "forbidden_paths": sorted(forbidden),
                "should_abstain": should_abstain,
                "retrieval_confidence": round(confidence, 6),
                **modes,
            }
        )
    base = _metrics(results, "base")
    learned = _metrics(results, "learned")
    improved = sum(
        1
        for item in results
        if item["learned"]["rank"]
        and (
            not item["base"]["rank"]
            or item["learned"]["rank"] < item["base"]["rank"]
        )
    )
    regressed = sum(
        1
        for item in results
        if item["base"]["rank"]
        and (
            not item["learned"]["rank"]
            or item["learned"]["rank"] > item["base"]["rank"]
        )
    )
    return {
        "schema_version": "cortex-evaluation/1.0",
        "corpus": {
            "name": corpus.get("name", "unnamed"),
            "version": corpus.get("version", "1.0"),
            "cases": len(results),
        },
        "baseline": base,
        "learned": learned,
        "delta": {
            "recall": round(
                learned["recall_at_node_budget"] - base["recall_at_node_budget"], 6
            ),
            "mean_reciprocal_rank": round(
                learned["mean_reciprocal_rank"] - base["mean_reciprocal_rank"], 6
            ),
            "improved_cases": improved,
            "regressed_cases": regressed,
        },
        "gate": {
            "no_retrieval_regression": (
                learned["recall_at_node_budget"] >= base["recall_at_node_budget"]
                and learned["mean_reciprocal_rank"] >= base["mean_reciprocal_rank"]
            ),
            "boundary_preserved": learned["boundary_separation"] >= base["boundary_separation"],
            "promotion_ready": bool(results) and regressed == 0,
        },
        "results": results,
        "claim_class": "benchmark_evidence",
        "claim_boundary": (
            "Results apply only to this declared corpus and configuration; "
            "they are not universal answer-quality evidence."
        ),
    }
