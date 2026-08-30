"""Governed multi-agent orchestration over the Cortex native runtime.

Storm does not create a second agent runtime and does not mint authority.  It
binds host-selected agent identities and attenuated grants to independent
native-agent trajectories, then returns child output as untrusted observation.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .native_agent import CapabilityGrant, NativeAgentRuntime, verify_native_agent_trajectory
from .store import Store
from .symbiosis import open_symbiotic_session


SCHEMA = "cortex-storm/1.0"
MANIFEST_SCHEMA = "cortex-storm-agent-manifest/1.0"
GRANT_SCHEMA = "cortex-storm-grant/1.0"
ZERO_HASH = "0" * 64
FORBIDDEN_TOOL_IDS = frozenset({"host.mutate", "source.edit", "deploy", "token.mint_self"})


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


def _required(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


def _closed_authority() -> dict[str, bool]:
    return {
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "competence_promotion_authorized": False,
        "policy_effect": False,
    }


@dataclass(frozen=True)
class AgentManifest:
    """Host-declared Storm identity. Model identity is runtime provenance only."""

    agent_id: str
    role: str
    purpose: str
    allowed_tool_ids: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()

    def material(self) -> dict[str, Any]:
        tools = sorted({_required(item, "allowed tool") for item in self.allowed_tool_ids})
        if FORBIDDEN_TOOL_IDS.intersection(tools):
            raise ValueError("agent manifest requests a forbidden authority surface")
        return {
            "schema_version": MANIFEST_SCHEMA,
            "agent_id": _required(self.agent_id, "agent_id"),
            "role": _required(self.role, "role"),
            "purpose": _required(self.purpose, "purpose"),
            "allowed_tool_ids": tools,
            "required_capabilities": sorted(
                {_required(item, "required capability") for item in self.required_capabilities}
            ),
            "model_binding": "runtime_provenance_only",
            "may_delegate": False,
            **_closed_authority(),
        }

    @property
    def manifest_hash(self) -> str:
        return _sha(self.material())


@dataclass(frozen=True)
class StormGrant:
    """Host-owned ceiling from which every child grant must be attenuated."""

    principal_id: str
    purpose: str
    allowed_agent_ids: tuple[str, ...]
    allowed_roles: tuple[str, ...]
    allowed_tool_ids: tuple[str, ...] = ()
    max_agents: int = 4
    max_concurrency: int = 2
    max_iterations_per_agent: int = 4
    max_tool_calls_per_agent: int = 8
    max_total_tool_seconds_per_agent: float = 120.0
    max_wall_seconds: float = 300.0
    issued_at: float = 0.0
    expires_at: float | None = None

    def material(self) -> dict[str, Any]:
        tools = sorted({_required(item, "allowed tool") for item in self.allowed_tool_ids})
        if FORBIDDEN_TOOL_IDS.intersection(tools):
            raise ValueError("Storm grant requests a forbidden authority surface")
        return {
            "schema_version": GRANT_SCHEMA,
            "principal_id": _required(self.principal_id, "principal_id"),
            "purpose": _required(self.purpose, "purpose"),
            "allowed_agent_ids": sorted(
                {_required(item, "allowed agent") for item in self.allowed_agent_ids}
            ),
            "allowed_roles": sorted({_required(item, "allowed role") for item in self.allowed_roles}),
            "allowed_tool_ids": tools,
            "max_agents": max(1, min(int(self.max_agents), 16)),
            "max_concurrency": max(1, min(int(self.max_concurrency), 8)),
            "max_iterations_per_agent": max(1, min(int(self.max_iterations_per_agent), 32)),
            "max_tool_calls_per_agent": max(0, min(int(self.max_tool_calls_per_agent), 128)),
            "max_total_tool_seconds_per_agent": max(
                0.0, min(float(self.max_total_tool_seconds_per_agent), 1800.0)
            ),
            "max_wall_seconds": max(0.1, min(float(self.max_wall_seconds), 3600.0)),
            "issued_at": float(self.issued_at),
            "expires_at": float(self.expires_at) if self.expires_at is not None else None,
            "host_issued": True,
            "delegable": False,
            **_closed_authority(),
        }

    @property
    def grant_hash(self) -> str:
        return _sha(self.material())

    def verify(self, *, now: float | None = None) -> dict[str, Any]:
        body = self.material()
        checked_at = float(time.time() if now is None else now)
        errors: list[str] = []
        if body["issued_at"] > 0 and checked_at < body["issued_at"]:
            errors.append("storm_grant_not_yet_current")
        if body["expires_at"] is not None and checked_at > body["expires_at"]:
            errors.append("storm_grant_expired")
        return {"valid": not errors, "errors": errors, "grant_hash": self.grant_hash}


@dataclass(frozen=True)
class DelegatedTask:
    task_id: str
    instruction: str
    agent: AgentManifest
    expected_evidence: tuple[str, ...] = ()

    def material(self, storm_grant_hash: str, child_grant_hash: str) -> dict[str, Any]:
        body = {
            "schema_version": SCHEMA,
            "task_id": _required(self.task_id, "task_id"),
            "instruction": _required(self.instruction, "instruction"),
            "instruction_hash": _sha(self.instruction),
            "agent_manifest": self.agent.material(),
            "agent_manifest_hash": self.agent.manifest_hash,
            "storm_grant_hash": _required(storm_grant_hash, "storm_grant_hash"),
            "child_grant_hash": _required(child_grant_hash, "child_grant_hash"),
            "expected_evidence": sorted(
                {_required(item, "expected evidence") for item in self.expected_evidence}
            ),
            "result_semantics": "untrusted_observation_pending_verification",
            "child_may_delegate": False,
            **_closed_authority(),
        }
        body["task_contract_hash"] = _sha(body)
        return body


@dataclass(frozen=True)
class StormAssignment:
    task: DelegatedTask
    adapter: Any
    grant: CapabilityGrant


class _StormEventStream:
    def __init__(self, sink: Callable[[Mapping[str, Any]], None] | None = None) -> None:
        self.sink = sink
        self.events: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def emit(self, event_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            previous = self.events[-1]["event_hash"] if self.events else ZERO_HASH
            event = {
                "schema_version": SCHEMA,
                "sequence": len(self.events) + 1,
                "event_type": str(event_type),
                "payload": json.loads(_canonical(dict(payload))),
                "previous_event_hash": previous,
                "emitted_at": time.time(),
            }
            event["event_hash"] = _sha(event)
            self.events.append(event)
        if self.sink:
            self.sink(dict(event))
        return event


class StormOrchestrator:
    """Dispatch host-selected child runs and seal their evidence relationship."""

    def __init__(
        self,
        store: Any,
        repo: str,
        *,
        event_sink: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> None:
        repository = store.repo(repo)
        if not repository:
            raise ValueError(f"Unknown repository: {repo}")
        self.store = store
        self.repo = repo
        self.repository_path = str(Path(repository["path"]).resolve())
        self.event_sink = event_sink

    def _validate_assignment(self, assignment: StormAssignment, grant: StormGrant) -> None:
        ceiling = grant.material()
        manifest = assignment.task.agent.material()
        child = assignment.grant.material()
        if manifest["agent_id"] not in ceiling["allowed_agent_ids"]:
            raise PermissionError("agent is outside the Storm grant")
        if manifest["role"] not in ceiling["allowed_roles"]:
            raise PermissionError("agent role is outside the Storm grant")
        if child["principal_id"] != manifest["agent_id"]:
            raise PermissionError("child grant principal does not match agent identity")
        child_tools = set(child["allowed_tools"])
        if not child_tools.issubset(set(manifest["allowed_tool_ids"])):
            raise PermissionError("child tool grant exceeds agent manifest")
        if not child_tools.issubset(set(ceiling["allowed_tool_ids"])):
            raise PermissionError("child tool grant exceeds Storm grant")
        if child["max_tool_calls"] > ceiling["max_tool_calls_per_agent"]:
            raise PermissionError("child call budget exceeds Storm grant")
        if child["max_total_tool_seconds"] > ceiling["max_total_tool_seconds_per_agent"]:
            raise PermissionError("child time budget exceeds Storm grant")
        if str(Path(child["workspace_root"]).resolve()) != self.repository_path:
            raise PermissionError("child workspace differs from the attached repository")
        child_check = assignment.grant.verify()
        if not child_check["valid"]:
            raise PermissionError("child grant is not current: " + ",".join(child_check["errors"]))

    @staticmethod
    def _receipt_body(body: Mapping[str, Any]) -> dict[str, Any]:
        result = dict(body)
        result["content_hash"] = _sha(result)
        return result

    def run(
        self,
        objective: str,
        assignments: Sequence[StormAssignment],
        *,
        grant: StormGrant,
        cancel_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        objective = _required(objective, "objective")
        items = tuple(assignments)
        grant_check = grant.verify()
        if not grant_check["valid"]:
            raise PermissionError("Storm grant is not current: " + ",".join(grant_check["errors"]))
        ceiling = grant.material()
        if not items:
            raise ValueError("Storm requires at least one delegated task")
        if len(items) > ceiling["max_agents"]:
            raise PermissionError("Storm agent budget exceeded")
        task_ids = [item.task.task_id for item in items]
        agent_ids = [item.task.agent.agent_id for item in items]
        if len(set(task_ids)) != len(task_ids):
            raise ValueError("Storm task IDs must be unique")
        if len(set(agent_ids)) != len(agent_ids):
            raise ValueError("Storm agent IDs must be unique within one run")
        for item in items:
            self._validate_assignment(item, grant)

        session = open_symbiotic_session(
            self.store,
            self.repo,
            task=objective,
            provider="storm",
            model_id="provider-neutral",
            capability_profile={"storm": True, "storm_grant_hash": grant.grant_hash},
            tool_scopes=ceiling["allowed_tool_ids"],
            persist=True,
        )
        stream = _StormEventStream(self.event_sink)
        contracts = [
            item.task.material(grant.grant_hash, item.grant.grant_hash) for item in items
        ]
        plan_body = self._receipt_body(
            {
                "schema_version": SCHEMA,
                "kind": "storm_plan",
                "status": "prepared",
                "session_id": session["session_id"],
                "turn_id": 0,
                "event_id": f"storm_plan_{_sha(contracts)[:24]}",
                "body_epoch_id": session["body_epoch_id"],
                "objective": objective,
                "objective_hash": _sha(objective),
                "storm_grant": ceiling,
                "storm_grant_hash": grant.grant_hash,
                "task_contracts": contracts,
                "orchestration_mode": "bounded_parallel",
                "result_semantics": "child_outputs_are_untrusted_observations",
                **_closed_authority(),
            }
        )
        plan = self.store.append_symbiotic_receipt(self.repo, plan_body)
        stream.emit(
            "storm.started",
            {
                "storm_session_id": session["session_id"],
                "agent_count": len(items),
                "max_concurrency": min(ceiling["max_concurrency"], len(items)),
                "plan_receipt_hash": plan["receipt_hash"],
            },
        )

        cancellation = cancel_event or threading.Event()
        timeout_reason = {"value": ""}

        def expire() -> None:
            timeout_reason["value"] = "storm_wall_budget_exhausted"
            cancellation.set()

        timer = threading.Timer(ceiling["max_wall_seconds"], expire)
        timer.daemon = True
        timer.start()

        def execute(index: int, assignment: StormAssignment) -> tuple[int, dict[str, Any]]:
            manifest = assignment.task.agent
            contract = contracts[index]
            if cancellation.is_set():
                return index, {
                    "task_id": assignment.task.task_id,
                    "task_contract_hash": contract["task_contract_hash"],
                    "agent_id": manifest.agent_id,
                    "agent_manifest_hash": manifest.manifest_hash,
                    "status": "cancelled",
                    "reason": timeout_reason["value"] or "operator_cancelled",
                    "trajectory_receipt_hash": "",
                    "trajectory_valid": False,
                    "observation": None,
                    "observation_hash": _sha(None),
                    "trusted": False,
                    "verification_required": True,
                    **_closed_authority(),
                }
            stream.emit(
                "agent.spawned",
                {
                    "agent_id": manifest.agent_id,
                    "role": manifest.role,
                    "task_id": assignment.task.task_id,
                    "agent_manifest_hash": manifest.manifest_hash,
                    "task_contract_hash": contract["task_contract_hash"],
                },
            )
            stream.emit(
                "agent.started",
                {"agent_id": manifest.agent_id, "task_id": assignment.task.task_id},
            )
            worker = Store(Path(self.store.path))
            try:
                def child_event(event: Mapping[str, Any]) -> None:
                    stream.emit(
                        "agent.child.event",
                        {
                            "agent_id": manifest.agent_id,
                            "task_id": assignment.task.task_id,
                            "child_event_type": str(event.get("event_type") or "agent.event"),
                            "child_event_hash": str(event.get("event_hash") or ""),
                            "child_sequence": int(event.get("sequence") or 0),
                        },
                    )

                result = NativeAgentRuntime(
                    worker,
                    self.repo,
                    max_iterations=ceiling["max_iterations_per_agent"],
                    event_sink=child_event,
                ).run(
                    assignment.task.instruction,
                    adapter=assignment.adapter,
                    grant=assignment.grant,
                    continuity_id=session["session_id"],
                    cancel_event=cancellation,
                )
                verification = verify_native_agent_trajectory(
                    worker, self.repo, result["trajectory_receipt_hash"]
                )
                observation = str(result.get("final_answer") or "")
                status = "observed" if verification["valid"] else "verification_failed"
                payload = {
                    "task_id": assignment.task.task_id,
                    "task_contract_hash": contract["task_contract_hash"],
                    "agent_id": manifest.agent_id,
                    "agent_manifest_hash": manifest.manifest_hash,
                    "status": status,
                    "reason": "",
                    "trajectory_receipt_hash": result["trajectory_receipt_hash"],
                    "trajectory_valid": bool(verification["valid"]),
                    "observation": observation,
                    "observation_hash": _sha(observation),
                    "trusted": False,
                    "verification_required": True,
                    "provider_identity_is_provenance_only": True,
                    **_closed_authority(),
                }
                stream.emit(
                    "agent.completed" if verification["valid"] else "agent.failed",
                    {
                        "agent_id": manifest.agent_id,
                        "task_id": assignment.task.task_id,
                        "status": status,
                        "trajectory_receipt_hash": result["trajectory_receipt_hash"],
                    },
                )
                return index, payload
            except Exception as exc:
                payload = {
                    "task_id": assignment.task.task_id,
                    "task_contract_hash": contract["task_contract_hash"],
                    "agent_id": manifest.agent_id,
                    "agent_manifest_hash": manifest.manifest_hash,
                    "status": "cancelled" if cancellation.is_set() else "failed",
                    "reason": timeout_reason["value"] or f"{type(exc).__name__}:{exc}",
                    "trajectory_receipt_hash": "",
                    "trajectory_valid": False,
                    "observation": None,
                    "observation_hash": _sha(None),
                    "trusted": False,
                    "verification_required": True,
                    **_closed_authority(),
                }
                stream.emit(
                    "agent.failed",
                    {
                        "agent_id": manifest.agent_id,
                        "task_id": assignment.task.task_id,
                        "status": payload["status"],
                        "reason": payload["reason"],
                    },
                )
                return index, payload
            finally:
                worker.close()

        observations: list[dict[str, Any] | None] = [None] * len(items)
        try:
            with ThreadPoolExecutor(
                max_workers=min(ceiling["max_concurrency"], len(items)),
                thread_name_prefix="cortex-storm",
            ) as executor:
                futures = [executor.submit(execute, index, item) for index, item in enumerate(items)]
                for future in as_completed(futures):
                    index, observation = future.result()
                    observations[index] = observation
        finally:
            timer.cancel()

        sealed_results: list[dict[str, Any]] = []
        for index, observation in enumerate(observations, 1):
            assert observation is not None
            body = self._receipt_body(
                {
                    "schema_version": SCHEMA,
                    "kind": "storm_agent_observation",
                    "status": observation["status"],
                    "session_id": session["session_id"],
                    "turn_id": index,
                    "event_id": f"storm_observation_{observation['task_id']}_{_sha(observation)[:16]}",
                    "body_epoch_id": session["body_epoch_id"],
                    **observation,
                }
            )
            sealed_results.append(self.store.append_symbiotic_receipt(self.repo, body))

        valid_count = sum(1 for item in sealed_results if item.get("trajectory_valid") is True)
        statuses = [str(item.get("status") or "") for item in sealed_results]
        summary_status = (
            "cancelled"
            if statuses and all(status == "cancelled" for status in statuses)
            else "completed"
            if valid_count == len(sealed_results)
            else "partial"
        )
        stream.emit(
            "storm.completed",
            {
                "storm_session_id": session["session_id"],
                "status": summary_status,
                "verified_trajectory_count": valid_count,
                "observation_count": len(sealed_results),
            },
        )
        summary_body = self._receipt_body(
            {
                "schema_version": SCHEMA,
                "kind": "storm_summary",
                "status": summary_status,
                "session_id": session["session_id"],
                "turn_id": len(items) + 1,
                "event_id": f"storm_summary_{_sha([item['receipt_hash'] for item in sealed_results])[:24]}",
                "body_epoch_id": session["body_epoch_id"],
                "plan_receipt_hash": plan["receipt_hash"],
                "observation_receipt_hashes": [item["receipt_hash"] for item in sealed_results],
                "verified_trajectory_count": valid_count,
                "observation_count": len(sealed_results),
                "events": stream.events,
                "event_tip_hash": stream.events[-1]["event_hash"] if stream.events else ZERO_HASH,
                "advisory_only": True,
                "claim_boundary": (
                    "Storm coordinates bounded model work. Child output remains untrusted "
                    "observation and cannot authorize host mutation, execution, memory, competence, or policy."
                ),
                **_closed_authority(),
            }
        )
        summary = self.store.append_symbiotic_receipt(self.repo, summary_body)
        verification = verify_storm_session(self.store, self.repo, summary["receipt_hash"])
        if not verification["valid"]:
            raise RuntimeError("Storm session failed canonical verification: " + ",".join(verification["errors"]))
        return {
            "schema_version": SCHEMA,
            "session_id": session["session_id"],
            "status": summary_status,
            "plan_receipt_hash": plan["receipt_hash"],
            "summary_receipt_hash": summary["receipt_hash"],
            "observations": [dict(item) for item in sealed_results],
            "verification": verification,
            "authority": _closed_authority(),
        }


def _verify_content_hash(receipt: Mapping[str, Any]) -> bool:
    excluded = {
        "receipt_hash",
        "subject_receipt_hash",
        "previous_receipt_hash",
        "chain_sequence",
        "repository_id",
        "repo",
        "created_at",
        "ledger_schema_version",
        "inserted",
        "duplicate",
        "chain_valid",
        "content_hash",
    }
    return str(receipt.get("content_hash") or "") == _sha(
        {key: value for key, value in receipt.items() if key not in excluded}
    )


def verify_storm_session(store: Any, repo: str, summary_receipt_hash: str) -> dict[str, Any]:
    """Reload and verify a complete Storm plan/result relationship."""

    summary = store.symbiotic_receipt(str(summary_receipt_hash), repo=repo)
    if not summary or summary.get("kind") != "storm_summary":
        return {"valid": False, "errors": ["storm_summary_missing"]}
    errors: list[str] = []
    session_id = str(summary.get("session_id") or "")
    chain = store.verify_symbiotic_session(repo, session_id)
    if not chain.get("valid"):
        errors.append("storm_ledger_chain_invalid")
    receipts = store.symbiotic_session_receipts(repo, session_id)
    by_hash = {str(item.get("receipt_hash") or ""): item for item in receipts}
    plan = by_hash.get(str(summary.get("plan_receipt_hash") or ""))
    if not plan or plan.get("kind") != "storm_plan":
        errors.append("storm_plan_missing")
        contracts: dict[str, Mapping[str, Any]] = {}
    else:
        if not _verify_content_hash(plan):
            errors.append("storm_plan_content_hash_invalid")
        grant_body = plan.get("storm_grant") if isinstance(plan.get("storm_grant"), Mapping) else {}
        if str(plan.get("storm_grant_hash") or "") != _sha(dict(grant_body)):
            errors.append("storm_grant_hash_invalid")
        contracts = {
            str(item.get("task_id") or ""): item
            for item in plan.get("task_contracts") or ()
            if isinstance(item, Mapping)
        }
        for task_id, contract in contracts.items():
            material = {key: value for key, value in contract.items() if key != "task_contract_hash"}
            if str(contract.get("task_contract_hash") or "") != _sha(material):
                errors.append(f"task_contract_hash_invalid:{task_id}")
            manifest = contract.get("agent_manifest") if isinstance(contract.get("agent_manifest"), Mapping) else {}
            if str(contract.get("agent_manifest_hash") or "") != _sha(dict(manifest)):
                errors.append(f"agent_manifest_hash_invalid:{task_id}")

    observation_hashes = [str(item) for item in summary.get("observation_receipt_hashes") or ()]
    if int(summary.get("observation_count") or 0) != len(observation_hashes):
        errors.append("storm_observation_count_invalid")
    verified_trajectories = 0
    for receipt_hash in observation_hashes:
        observation = by_hash.get(receipt_hash)
        if not observation or observation.get("kind") != "storm_agent_observation":
            errors.append(f"storm_observation_missing:{receipt_hash}")
            continue
        task_id = str(observation.get("task_id") or "")
        contract = contracts.get(task_id)
        if not contract:
            errors.append(f"storm_observation_contract_missing:{task_id}")
        elif str(observation.get("task_contract_hash") or "") != str(
            contract.get("task_contract_hash") or ""
        ):
            errors.append(f"storm_observation_contract_mismatch:{task_id}")
        if not _verify_content_hash(observation):
            errors.append(f"storm_observation_content_hash_invalid:{task_id}")
        if observation.get("trusted") is not False or observation.get("verification_required") is not True:
            errors.append(f"storm_observation_trust_invalid:{task_id}")
        trajectory_hash = str(observation.get("trajectory_receipt_hash") or "")
        if trajectory_hash:
            verified = verify_native_agent_trajectory(store, repo, trajectory_hash)
            if not verified.get("valid"):
                errors.append(f"child_trajectory_invalid:{task_id}")
            else:
                child = store.symbiotic_receipt(trajectory_hash, repo=repo) or {}
                if str(child.get("continuity_id") or "") != session_id:
                    errors.append(f"child_continuity_mismatch:{task_id}")
                if str(child.get("body_epoch_id") or "") != str(summary.get("body_epoch_id") or ""):
                    errors.append(f"child_epoch_mismatch:{task_id}")
                verified_trajectories += 1
    if int(summary.get("verified_trajectory_count") or 0) != verified_trajectories:
        errors.append("verified_trajectory_count_invalid")
    if not _verify_content_hash(summary):
        errors.append("storm_summary_content_hash_invalid")
    events = summary.get("events") or ()
    previous = ZERO_HASH
    for expected_sequence, event in enumerate(events, 1):
        if not isinstance(event, Mapping):
            errors.append("storm_event_invalid")
            break
        material = {key: value for key, value in event.items() if key != "event_hash"}
        if int(event.get("sequence") or 0) != expected_sequence:
            errors.append("storm_event_sequence_invalid")
        if str(event.get("previous_event_hash") or "") != previous:
            errors.append("storm_event_link_invalid")
        if str(event.get("event_hash") or "") != _sha(material):
            errors.append("storm_event_hash_invalid")
        previous = str(event.get("event_hash") or "")
    if str(summary.get("event_tip_hash") or ZERO_HASH) != previous:
        errors.append("storm_event_tip_invalid")
    for receipt in [summary, *(item for item in by_hash.values() if item.get("kind", "").startswith("storm_"))]:
        for field_name in _closed_authority():
            if receipt.get(field_name) is not False:
                errors.append(f"storm_authority_open:{field_name}")
    return {
        "valid": not errors,
        "errors": sorted(set(errors)),
        "session_id": session_id,
        "verified_trajectory_count": verified_trajectories,
        "observation_count": len(observation_hashes),
        "chain_valid": bool(chain.get("valid")),
    }
