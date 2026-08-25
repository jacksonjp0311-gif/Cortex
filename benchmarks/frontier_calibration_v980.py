"""Disposable frontier-model ceiling calibration for the v9.8 causal trial.

This is provider-specific experiment glue, not Cortex ontology. The executable
and model are mandatory runtime arguments. Only structured public answers and
bounded invocation metadata are persisted; hidden/thought fields are dropped.
Calibration cases are permanently excluded from confirmatory evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def tasks() -> list[dict[str, str]]:
    panel: list[dict[str, str]] = []

    values = [31, 4, 88, 17, 52, 9, 73, 26, 61, 45, 2, 95, 38, 14, 67, 21, 83, 7, 56, 42, 19, 79, 11, 64]
    x = 17
    for index, value in enumerate(values):
        x = ((x * (7 if index % 3 else 11)) + value * (index + 1)) % 997
    panel.append({"id": "accumulator", "prompt": f"Start x=17. For values {values}, at zero-based index i update x=((x*(11 if i divisible by 3 else 7))+value*(i+1)) mod 997. Return final x as decimal.", "answer": str(x)})

    transitions = {"A": {"p": "C", "q": "B", "r": "D"}, "B": {"p": "A", "q": "D", "r": "C"}, "C": {"p": "D", "q": "A", "r": "B"}, "D": {"p": "B", "q": "C", "r": "A"}}
    stream = list("prqqrppqrprrqqppprqrqrrpqpqrprqqrppq")
    state, score = "B", 0
    for index, token in enumerate(stream):
        state = transitions[state][token]
        score = (score + ("ABCD".index(state) + 1) * (index + 3)) % 211
    panel.append({"id": "state_machine", "prompt": f"State starts B, score 0. Transition table {transitions}. Consume {''.join(stream)}. After each transition add (1-based position of new state in ABCD)*(stream index+3) to score mod 211. Return STATE:SCORE.", "answer": f"{state}:{score}"})

    deps = {"a": [], "b": ["a"], "c": ["a"], "d": ["b"], "e": ["b", "c"], "f": ["c"], "g": ["d", "e"], "h": ["e", "f"], "i": ["g", "h"], "j": ["d", "f"], "k": ["i", "j"]}
    remaining, order = set(deps), []
    while remaining:
        ready = sorted(node for node in remaining if all(dep in order for dep in deps[node]))
        chosen = ready[-1] if len(order) % 2 else ready[0]
        order.append(chosen); remaining.remove(chosen)
    panel.append({"id": "dependency_order", "prompt": f"Dependencies are {deps}. Repeatedly take ready nodes sorted alphabetically; on even output positions choose first, on odd positions choose last. Return the concatenated topological order.", "answer": "".join(order)})

    intervals = [(41, 48), (3, 9), (8, 15), (62, 70), (14, 19), (27, 33), (31, 44), (81, 87), (69, 76), (75, 82), (92, 95)]
    merged: list[list[int]] = []
    for left, right in sorted(intervals):
        if not merged or left > merged[-1][1] + 1: merged.append([left, right])
        else: merged[-1][1] = max(merged[-1][1], right)
    checksum = sum((i + 1) * (left * 3 + right * 5) for i, (left, right) in enumerate(merged)) % 1009
    panel.append({"id": "interval_checksum", "prompt": f"Sort and merge closed intervals {intervals}; touching or adjacent intervals merge. For merged intervals (l,r) in order compute sum((index+1)*(3*l+5*r)) mod 1009. Return count:checksum.", "answer": f"{len(merged)}:{checksum}"})

    events = [("m1",1,"active"),("m2",1,"active"),("m1",2,"superseded"),("m3",2,"active"),("m2",3,"contested"),("m4",3,"active"),("m3",4,"active"),("m2",4,"active"),("m4",5,"revoked"),("m5",5,"active"),("m3",5,"superseded"),("m6",5,"active")]
    latest: dict[str, tuple[int, str]] = {}
    for ident, epoch, status in events: latest[ident] = (epoch, status)
    active = sorted(ident for ident, (epoch, status) in latest.items() if epoch == 5 and status == "active")
    panel.append({"id": "epoch_ledger", "prompt": f"Process ledger rows in order {events}; latest row per memory wins. Select only memories whose latest epoch is exactly 5 and status active. Return comma-separated IDs sorted.", "answer": ",".join(active)})

    operations = list("ABCADEBBACDACEABBDACCEABDACB")
    cache: list[str] = []
    for item in operations:
        if item in cache: cache.remove(item)
        cache.append(item)
        if len(cache) > 3: cache.pop(0)
    panel.append({"id": "lru", "prompt": f"An empty LRU cache has capacity 3. Access this stream: {''.join(operations)}. Existing keys move to most-recent; overflow evicts least-recent. Return keys least-recent to most-recent.", "answer": "".join(cache)})

    word = "abca"
    for step in range(11):
        mapped = "".join({"a":"bc","b":"ca","c":"ab"}[ch] for ch in word)
        rotation = (step * 3 + 2) % len(mapped)
        word = (mapped[rotation:] + mapped[:rotation])[::2]
    panel.append({"id": "rewrite", "prompt": "Start word abca. For steps s=0..10: simultaneously map a->bc,b->ca,c->ab; rotate left by (3s+2) mod new length; retain characters at zero-based even positions. Return final word.", "answer": word})

    registers = {"a": 7, "b": 19, "c": 3}
    program = [("mul","a",5),("xor","b",12),("add","c",17),("mix","a","b"),("rot","c",3),("mix","b","c"),("add","a",29),("xor","c",41),("mix","a","c"),("rot","b",2),("mul","c",7),("mix","b","a")]
    for op, target, arg in program:
        if op == "mul": registers[target] = registers[target] * int(arg) % 256
        elif op == "add": registers[target] = (registers[target] + int(arg)) % 256
        elif op == "xor": registers[target] ^= int(arg)
        elif op == "rot":
            shift = int(arg); value = registers[target]
            registers[target] = ((value << shift) | (value >> (8-shift))) & 255
        else: registers[target] = (registers[target] + registers[str(arg)] * 3) % 256
    answer = "-".join(f"{registers[key]:02X}" for key in "abc")
    panel.append({"id": "bytecode", "prompt": f"8-bit registers start a=7,b=19,c=3. Execute {program}. mul/add mod256; xor bitwise; rot is 8-bit rotate-left; mix(target,source)=target+3*source mod256. Return a-b-c uppercase two-digit hex.", "answer": answer})

    return panel


def parse_cli_json(raw: str) -> dict[str, Any]:
    start = raw.find("{")
    if start < 0: raise ValueError("frontier CLI returned no JSON object")
    return json.loads(raw[start:])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--reasoning-effort", default="high")
    args = parser.parse_args()
    schema = canonical({"type":"object","properties":{"answer":{"type":"string"}},"required":["answer"],"additionalProperties":False})
    results = []
    started = time.time()
    for task in tasks():
        prompt = "This is a no-tools calibration problem. Follow the stated algorithm exactly. Return only the requested answer in the answer field. " + task["prompt"]
        before = time.perf_counter()
        completed = subprocess.run(
            [args.command, "--model", args.model, "--reasoning-effort", args.reasoning_effort, "--no-subagents", "--tools", "", "--output-format", "json", "--json-schema", schema, "--single", prompt],
            cwd=ROOT, text=True, capture_output=True, encoding="utf-8", errors="replace", timeout=180, check=False,
        )
        latency = time.perf_counter() - before
        envelope = parse_cli_json(completed.stdout)
        public = envelope.get("structuredOutput") if isinstance(envelope.get("structuredOutput"), dict) else {}
        observed = str(public.get("answer") or "").strip()
        results.append({
            "task_id": task["id"], "task_hash": sha(task), "expected_hash": sha(task["answer"]),
            "observed_hash": sha(observed), "success": observed == task["answer"], "latency_seconds": round(latency,6),
            "stop_reason": envelope.get("stopReason"), "session_id": envelope.get("sessionId"), "request_id": envelope.get("requestId"),
            "usage": envelope.get("usage"), "total_cost_usd": envelope.get("total_cost_usd"), "public_answer": observed,
            "hidden_reasoning_persisted": False, "raw_provider_envelope_persisted": False,
        })
    report = {
        "schema_version":"cortex-frontier-calibration/1.0", "cortex_commit": subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "model_selection_source":"runtime_argument", "model_id":args.model, "command_hash":sha(str(Path(args.command).resolve())),
        "evidence_class":"live_external_calibration", "confirmatory_eligible":False, "started_at":started, "completed_at":time.time(),
        "task_count":len(results), "success_count":sum(int(row["success"]) for row in results),
        "success_rate":sum(int(row["success"]) for row in results)/len(results), "results":results,
        "authority":{"host_mutate_authorized":False,"execution_authorized":False,"memory_admission_authorized":False,"policy_effect":False},
        "claim_boundary":"Calibration estimates task ceiling only. It is excluded from confirmation and does not establish competence transfer.",
    }
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({k:report[k] for k in ("task_count","success_count","success_rate","evidence_class","confirmatory_eligible")},indent=2))
    return 0


if __name__ == "__main__": raise SystemExit(main())
