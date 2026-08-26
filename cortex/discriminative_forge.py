"""Deterministic, model-neutral development corpus for task calibration.

The forge creates exact-evaluator cases across multiple software-agent task
families.  Cases are calibration material and are permanently excluded from
confirmatory evidence.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
from collections.abc import Mapping
from typing import Any

from .information_calibration import verify_difficulty_calibration


SCHEMA_VERSION = "cortex-discriminative-forge/1.1"
VERSION = "9.8.4"
TASK_FAMILIES = (
    "repository_bug_localization",
    "multi_step_code_repair",
    "stale_state_detection",
    "api_migration",
    "architecture_reconstruction",
)
COUPLED_FAMILIES = tuple(family for family in TASK_FAMILIES if family != "api_migration")
LATENT_CAUSE_FAMILIES = COUPLED_FAMILIES


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _case(family: str, variant: int, prompt: str, answer: str) -> dict[str, Any]:
    material = {
        "family": family,
        "variant": int(variant),
        "difficulty_band": "development_calibration",
        "prompt": prompt,
        "evaluator": "normalized_exact_public_output",
        "expected_public_output": answer,
    }
    return {**material, "case_id": _sha(material), "answer_hash": _sha(answer)}


def build_discriminative_corpus(*, seed: str = "cortex-v981", variants_per_family: int = 4) -> dict[str, Any]:
    """Build a stable disposable corpus without provider or model semantics."""
    if variants_per_family < 2:
        raise ValueError("variants_per_family must be at least two")
    rng = random.Random(int(_sha(seed)[:16], 16))
    cases: list[dict[str, Any]] = []
    for variant in range(variants_per_family):
        modulus = rng.choice([97, 101, 127, 131])
        wrong_line = 4 + variant
        files = [f"module_{index}.py" for index in range(4)]
        target = files[(variant * 3 + 1) % len(files)]
        cases.append(_case(
            "repository_bug_localization", variant,
            f"Four modules implement x=(x*7+value) mod {modulus}. Only {target} line {wrong_line} uses *5. Return the unique defect as file:line.",
            f"{target}:{wrong_line}",
        ))

        start = rng.randrange(11, 40)
        values = [rng.randrange(2, 30) for _ in range(5 + variant)]
        expected = start
        for index, value in enumerate(values):
            expected = (expected + value * (index + 2)) % modulus
        cases.append(_case(
            "multi_step_code_repair", variant,
            f"Repair the accumulator conceptually: start={start}; for values={values}, update x=(x+value*(index+2)) mod {modulus}. Return the final decimal value.",
            str(expected),
        ))

        epoch = 6 + variant + rng.randrange(0, 7)
        suffix = rng.randrange(10, 99)
        names = [f"m{index}_{suffix}" for index in range(1, 4)]
        rows = [(names[0], epoch - 1, "active"), (names[1], epoch, "active"), (names[0], epoch, "contested"), (names[2], epoch, "active"), (names[1], epoch + 1, "superseded")]
        active = sorted(identifier for identifier in {row[0] for row in rows} if next(row for row in reversed(rows) if row[0] == identifier)[1:] == (epoch, "active"))
        cases.append(_case(
            "stale_state_detection", variant,
            f"Ledger rows arrive in order {rows}. Latest row per ID wins. At current epoch {epoch}, return sorted comma-separated IDs whose latest row is exactly current and active.",
            ",".join(active) if active else "NONE",
        ))

        timeout = 20 + variant * 5 + rng.randrange(1, 10)
        retries = rng.randrange(1, 5)
        endpoint = f"/health/{rng.randrange(100, 999)}"
        cases.append(_case(
            "api_migration", variant,
            "Old API fetch(url, timeout, retries) became request(*, endpoint, retry_limit, timeout_ms). "
            f"Migrate fetch('{endpoint}', {timeout}, {retries}) and return only the new call, converting seconds to milliseconds.",
            f"request(endpoint='{endpoint}', retry_limit={retries}, timeout_ms={timeout * 1000})",
        ))

        tag = rng.randrange(10, 99)
        node = {name: f"{name}{tag}" for name in "abcdef"}
        dependencies = {node["a"]: [], node["b"]: [node["a"]], node["c"]: [node["a"]], node["d"]: [node["b"], node["c"]], node["e"]: [node["c"]], node["f"]: [node["d"], node["e"]]}
        order: list[str] = []
        remaining = set(dependencies)
        while remaining:
            ready = sorted(node for node in remaining if all(parent in order for parent in dependencies[node]))
            chosen = ready[-1] if (len(order) + variant) % 2 else ready[0]
            order.append(chosen)
            remaining.remove(chosen)
        cases.append(_case(
            "architecture_reconstruction", variant,
            f"Dependencies are {dependencies}. Repeatedly sort ready nodes; choose last when (output_position+{variant}) is odd, otherwise first. Return the concatenated order.",
            "".join(order),
        ))

    cases.sort(key=lambda row: (row["family"], row["variant"]))
    material = {
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
        "seed_commitment": _sha(seed),
        "task_families": list(TASK_FAMILIES),
        "cases": cases,
        "development_only": True,
        "held_out": False,
        "confirmatory_eligible": False,
        "model_identity_in_ontology": False,
        "authority": {
            "host_mutate_authorized": False,
            "execution_authorized": False,
            "memory_admission_authorized": False,
            "policy_effect": False,
        },
    }
    return {**material, "corpus_hash": _sha(material)}


def evaluate_case(case: dict[str, Any], public_output: str) -> bool:
    """Evaluate only the public answer; hidden reasoning is neither needed nor stored."""
    expected = " ".join(str(case["expected_public_output"]).strip().split())
    observed = " ".join(str(public_output).strip().split())
    return observed == expected


def build_difficulty_ladder_corpus(
    *,
    seed: str = "cortex-v982-development",
    maximum_level: int = 4,
    variants_per_level: int = 4,
) -> dict[str, Any]:
    """Create increasingly composed development tasks for empirical calibration."""
    if maximum_level < 1 or variants_per_level < 2:
        raise ValueError("difficulty ladder requires at least one level and two variants")
    cases: list[dict[str, Any]] = []
    for level in range(1, maximum_level + 1):
        for variant in range(variants_per_level):
            components: dict[str, list[dict[str, Any]]] = {family: [] for family in TASK_FAMILIES}
            for part in range(level):
                component_corpus = build_discriminative_corpus(
                    seed=f"{seed}:level={level}:variant={variant}:part={part}",
                    variants_per_family=max(2, variant + 2),
                )
                for family in TASK_FAMILIES:
                    family_cases = [row for row in component_corpus["cases"] if row["family"] == family]
                    components[family].append(family_cases[variant % len(family_cases)])
            for family, rows in components.items():
                prompt = " Solve each independent subcase and return answers joined by | in order. ".join(
                    f"Subcase {index + 1}: {row['prompt']}" for index, row in enumerate(rows)
                )
                answer = "|".join(str(row["expected_public_output"]) for row in rows)
                material = {
                    "family": family,
                    "difficulty_level": level,
                    "variant": variant,
                    "difficulty_mechanism": "composed_exact_subcases",
                    "component_case_ids": [row["case_id"] for row in rows],
                    "prompt": prompt,
                    "evaluator": "normalized_exact_public_output",
                    "expected_public_output": answer,
                }
                cases.append({**material, "case_id": _sha(material), "answer_hash": _sha(answer)})
    cases.sort(key=lambda row: (row["family"], row["difficulty_level"], row["variant"]))
    material = {
        "schema_version": "cortex-difficulty-ladder-corpus/1.0",
        "version": "9.8.2",
        "seed_commitment": _sha(seed),
        "task_families": list(TASK_FAMILIES),
        "maximum_level": int(maximum_level),
        "variants_per_level": int(variants_per_level),
        "cases": cases,
        "development_only": True,
        "held_out": False,
        "confirmatory_eligible": False,
        "model_identity_in_ontology": False,
    }
    return {**material, "corpus_hash": _sha(material)}


def build_coupled_dependency_corpus(
    *, seed: str = "cortex-v984-coupled-development", maximum_level: int = 4,
    variants_per_level: int = 8,
) -> dict[str, Any]:
    """Forge state-coupled tasks for families that saturated additive composition."""
    if maximum_level < 1 or variants_per_level < 2:
        raise ValueError("coupled corpus requires levels and at least two variants")
    cases: list[dict[str, Any]] = []
    for level in range(1, maximum_level + 1):
        for variant in range(variants_per_level):
            rng = random.Random(int(_sha(f"{seed}:{level}:{variant}")[:16], 16))
            depth = 8 + level * 5

            # The intended multiplier depends on the incoming state. One module
            # violates that rule, so later expected operations depend on earlier state.
            primes = (3, 5, 7, 11)
            state = rng.randrange(10, 90)
            initial = state
            defect = rng.randrange(2, depth - 1)
            modules = []
            for index in range(depth):
                intended = primes[(state + index) % len(primes)]
                multiplier = primes[(primes.index(intended) + 1) % len(primes)] if index == defect else intended
                offset = rng.randrange(1, 40)
                modules.append((f"module_{index:02d}.py", 10 + index, multiplier, offset))
                state = (state * multiplier + offset) % 997
            bug_material = {
                "family": "repository_bug_localization", "difficulty_level": level,
                "variant": variant, "difficulty_mechanism": "state_dependent_invariant_violation",
                "dependency_depth": depth,
                "prompt": (
                    f"Start x={initial}. Process modules in order {modules}. Before module i, its intended multiplier is "
                    f"{primes}[(x+i) mod 4]. Then update x=(x*listed_multiplier+offset) mod 997. Exactly one module's "
                    "listed multiplier violates the rule; its changed state affects every later rule evaluation. "
                    "Return the first violation as file:line."
                ),
                "evaluator": "normalized_exact_public_output",
                "expected_public_output": f"module_{defect:02d}.py:{10 + defect}",
            }
            cases.append({**bug_material, "case_id": _sha(bug_material), "answer_hash": _sha(bug_material["expected_public_output"])})

            # Both registers feed every following branch and transition.
            values = [rng.randrange(2, 80) for _ in range(depth + level)]
            x, y = rng.randrange(5, 80), rng.randrange(5, 80)
            start_x, start_y = x, y
            for index, value in enumerate(values):
                old_x, old_y = x, y
                if (old_x + old_y + index) % 3 == 0:
                    x = (old_x + value * (index + 2) + old_y) % 997
                    y = (old_y * 3 + old_x + value) % 991
                else:
                    x = (old_x * 5 + old_y + value) % 997
                    y = (old_y + value * (index + 3) + old_x) % 991
                x, y = y % 983, (x + 2 * y + index) % 983
            repair_material = {
                "family": "multi_step_code_repair", "difficulty_level": level,
                "variant": variant, "difficulty_mechanism": "recurrent_branch_coupling",
                "dependency_depth": len(values),
                "prompt": (
                    f"Registers start x={start_x}, y={start_y}; values={values}. For zero-based i use old x,y. If "
                    "(old_x+old_y+i) mod 3=0 set x=(old_x+value*(i+2)+old_y) mod 997 and "
                    "y=(old_y*3+old_x+value) mod 991; otherwise set x=(old_x*5+old_y+value) mod 997 and "
                    "y=(old_y+value*(i+3)+old_x) mod 991. Then simultaneously set x=y mod 983 and "
                    "y=(x+2*y+i) mod 983 using the just-computed x,y. Return final x:y in decimal."
                ),
                "evaluator": "normalized_exact_public_output", "expected_public_output": f"{x}:{y}",
            }
            cases.append({**repair_material, "case_id": _sha(repair_material), "answer_hash": _sha(repair_material["expected_public_output"])})

            # Eligibility depends on canonical latest state and recursively on parent eligibility.
            count = 7 + level * 3
            epoch = 20 + level
            parents = {f"m{i}": (None if i < 2 else f"m{(i - 2) // 2}") for i in range(count)}
            events = []
            for index in range(count):
                ident = f"m{index}"
                events.append((ident, epoch - 1, "active"))
                status = "active" if rng.random() > 0.28 else rng.choice(("contested", "superseded", "revoked"))
                events.append((ident, epoch, status))
            rng.shuffle(events)
            latest = {}
            for sequence, (ident, row_epoch, status) in enumerate(events):
                prior = latest.get(ident)
                if prior is None or (row_epoch, sequence) > (prior[0], prior[1]):
                    latest[ident] = (row_epoch, sequence, status)
            eligible: set[str] = set()
            changed = True
            while changed:
                changed = False
                for ident in sorted(parents):
                    parent = parents[ident]
                    row = latest[ident]
                    if row[0] == epoch and row[2] == "active" and (parent is None or parent in eligible) and ident not in eligible:
                        eligible.add(ident); changed = True
            stale_material = {
                "family": "stale_state_detection", "difficulty_level": level,
                "variant": variant, "difficulty_mechanism": "recursive_lineage_eligibility",
                "dependency_depth": count,
                "prompt": (
                    f"Parent map is {parents}. Ledger events are {events}. For each ID choose the row with greatest "
                    f"epoch, breaking equal-epoch ties by later list position. At current epoch {epoch}, a memory is "
                    "eligible only if its canonical latest state is active and its parent is either null or itself "
                    "eligible. Compute to a fixed point. Return sorted comma-separated eligible IDs, or NONE."
                ),
                "evaluator": "normalized_exact_public_output",
                "expected_public_output": ",".join(sorted(eligible)) if eligible else "NONE",
            }
            cases.append({**stale_material, "case_id": _sha(stale_material), "answer_hash": _sha(stale_material["expected_public_output"])})

            # Ready-node choice changes a checksum which changes all future scores.
            node_count = 8 + level * 3
            names = [f"n{i:02d}" for i in range(node_count)]
            dependencies = {}
            weights = {}
            for index, name in enumerate(names):
                candidates = names[:index]
                parent_count = 0 if index < 3 else rng.choice((1, 1, 2))
                dependencies[name] = sorted(rng.sample(candidates, min(parent_count, len(candidates))))
                weights[name] = rng.randrange(3, 97)
            remaining, order, checksum = set(names), [], rng.randrange(1, 50)
            start_checksum = checksum
            while remaining:
                ready = [name for name in remaining if all(parent in order for parent in dependencies[name])]
                chosen = min(ready, key=lambda name: (((weights[name] + checksum * (names.index(name) + 1)) % 101), name))
                order.append(chosen); remaining.remove(chosen)
                checksum = (checksum * 7 + weights[chosen] + len(order)) % 103
            architecture_material = {
                "family": "architecture_reconstruction", "difficulty_level": level,
                "variant": variant, "difficulty_mechanism": "checksum_coupled_topological_schedule",
                "dependency_depth": node_count,
                "prompt": (
                    f"Nodes in fixed index order are {names}; dependencies={dependencies}; weights={weights}; start "
                    f"checksum={start_checksum}. Repeatedly find nodes whose dependencies are already output. Score "
                    "ready node j as (weight+checksum*(fixed_index+1)) mod 101; choose lowest (tie by name). Append it, "
                    "then checksum=(checksum*7+weight+output_count) mod 103. Return names joined by >."
                ),
                "evaluator": "normalized_exact_public_output", "expected_public_output": ">".join(order),
            }
            cases.append({**architecture_material, "case_id": _sha(architecture_material), "answer_hash": _sha(architecture_material["expected_public_output"])})

    cases.sort(key=lambda row: (row["family"], row["difficulty_level"], row["variant"]))
    material = {
        "schema_version": "cortex-coupled-dependency-corpus/1.0", "version": VERSION,
        "seed_commitment": _sha(seed), "task_families": list(COUPLED_FAMILIES),
        "maximum_level": int(maximum_level), "variants_per_level": int(variants_per_level),
        "cases": cases, "development_only": True, "held_out": False,
        "confirmatory_eligible": False, "model_identity_in_ontology": False,
        "difficulty_law": "dependency_depth_and_state_coupling_not_additive_prompt_length",
    }
    return {**material, "corpus_hash": _sha(material)}


def _conditional_hypothesis_entropy(signatures: list[tuple[Any, ...]], coordinate: int) -> float:
    """Return H(H|O_coordinate) under a uniform hypothesis prior."""
    groups: dict[str, int] = {}
    for signature in signatures:
        key = _canonical(signature[coordinate])
        groups[key] = groups.get(key, 0) + 1
    total = len(signatures)
    return sum((count / total) * math.log2(count) for count in groups.values()) if total else 0.0


def _minimum_resolving_coordinates(signatures: list[tuple[Any, ...]]) -> int | None:
    """Find the smallest observed-coordinate subset that separates every hypothesis."""
    if not signatures:
        return None
    width = len(signatures[0])
    for size in range(1, width + 1):
        for coordinates in itertools.combinations(range(width), size):
            projections = {
                tuple(_canonical(signature[index]) for index in coordinates)
                for signature in signatures
            }
            if len(projections) == len(signatures):
                return size
    return None


def _evidence_entanglement(hypothesis_signatures: Mapping[str, Any]) -> dict[str, Any]:
    """Measure how evidence coordinates factorize without consulting model outcomes."""
    signatures = [tuple(value) for _, value in sorted(hypothesis_signatures.items())]
    if not signatures or not signatures[0]:
        raise ValueError("evidence geometry requires non-empty, equally shaped signatures")
    width = len(signatures[0])
    if any(len(signature) != width for signature in signatures):
        raise ValueError("evidence signatures must have equal coordinate counts")
    prior_entropy = math.log2(len(signatures))
    conditional = [_conditional_hypothesis_entropy(signatures, index) for index in range(width)]
    pair_collisions = [
        sum(a == b for a, b in zip(left, right)) / width
        for left, right in itertools.combinations(signatures, 2)
    ]
    minimum = _minimum_resolving_coordinates(signatures)
    return {
        "evidence_coordinate_count": width,
        "mean_single_coordinate_conditional_entropy_bits": round(sum(conditional) / width, 9),
        "maximum_single_coordinate_information_bits": round(prior_entropy - min(conditional), 9),
        "evidence_entanglement_ratio": round(
            (sum(conditional) / width) / prior_entropy if prior_entropy else 0.0, 9
        ),
        "mean_pairwise_coordinate_collision_rate": round(
            sum(pair_collisions) / len(pair_collisions) if pair_collisions else 0.0, 9
        ),
        "minimum_resolving_coordinate_count": minimum,
        "resolving_coordinate_fraction": round(minimum / width, 9) if minimum is not None else None,
        "metric_scope": "structural_evidence_geometry_not_model_difficulty",
    }


def _latent_geometry(
    hypothesis_signatures: Mapping[str, Any], *, include_entanglement: bool = False
) -> dict[str, Any]:
    """Bind the discrete information geometry independently of model outcomes."""
    signature_hashes = {str(key): _sha(value) for key, value in sorted(hypothesis_signatures.items())}
    count = len(signature_hashes)
    unique_count = len(set(signature_hashes.values()))
    posterior_count = 1 if count > 1 and unique_count == count else max(1, count - unique_count + 1)
    prior_entropy = math.log2(count) if count else 0.0
    posterior_entropy = math.log2(posterior_count) if posterior_count else 0.0
    geometry = {
        "hypothesis_count": count,
        "local_hypothesis_entropy_bits": round(prior_entropy, 9),
        "posterior_hypothesis_count": posterior_count,
        "posterior_hypothesis_entropy_bits": round(posterior_entropy, 9),
        "resolved_information_bits": round(prior_entropy - posterior_entropy, 9),
        "hypothesis_evidence_hashes": signature_hashes,
        "evidence_signatures_unique": unique_count == count,
        "epistemic_coupling": True,
    }
    if include_entanglement:
        geometry.update(_evidence_entanglement(hypothesis_signatures))
    return geometry


def build_latent_cause_corpus(
    *, seed: str = "cortex-v985-latent-development", maximum_level: int = 4,
    variants_per_level: int = 8,
    include_evidence_entanglement: bool = False,
    architecture_signature_table: bool = False,
    repair_transfer_multiplier: int = 1,
    corpus_version: str = "9.8.5",
) -> dict[str, Any]:
    """Forge exact tasks where downstream evidence resolves symmetric causes."""
    if maximum_level < 1 or variants_per_level < 2 or repair_transfer_multiplier < 1:
        raise ValueError("latent-cause corpus requires levels and at least two variants")
    cases: list[dict[str, Any]] = []
    for level in range(1, maximum_level + 1):
        for variant in range(variants_per_level):
            rng = random.Random(int(_sha(f"{seed}:{level}:{variant}")[:16], 16))
            hypothesis_count = 4 + level * 3

            # Every candidate module is locally plausible. Only end-to-end probe
            # checksums distinguish which candidate carried its declared defect.
            module_count = hypothesis_count
            modules = [(rng.randrange(2, 17), rng.randrange(1, 53)) for _ in range(module_count)]
            faults = [(rng.randrange(1, 7), rng.randrange(1, 19)) for _ in range(module_count)]

            def bug_signature(candidate: int, starts: list[int]) -> tuple[int, ...]:
                result = []
                for start in starts:
                    value = start
                    for index, ((multiplier, offset), (dm, do)) in enumerate(zip(modules, faults)):
                        value = (value * (multiplier + (dm if index == candidate else 0)) + offset + (do if index == candidate else 0)) % 1009
                    result.append(value)
                return tuple(result)

            bug_starts: list[int] = []
            bug_signatures: dict[str, tuple[int, ...]] = {}
            while len(bug_starts) < 8:
                bug_starts.append(rng.randrange(2, 997))
                bug_signatures = {f"H{i:02d}": bug_signature(i, bug_starts) for i in range(module_count)}
                if len(set(bug_signatures.values())) == module_count and len(bug_starts) >= 2 + level:
                    break
            true_bug = rng.randrange(module_count)
            bug_hypotheses = [
                (f"H{i:02d}", f"module_{i:02d}.py", 20 + i, faults[i][0], faults[i][1])
                for i in range(module_count)
            ]
            bug_material = {
                "family": "repository_bug_localization", "difficulty_level": level, "variant": variant,
                "difficulty_mechanism": "latent_fault_from_end_to_end_probes",
                "dependency_depth": module_count, "hypotheses": bug_hypotheses,
                "prompt": (
                    f"Normal ordered modules are {modules}, each applying x=(x*multiplier+offset) mod 1009. "
                    f"Exactly one locally plausible hypothesis is true: {bug_hypotheses}. Under H, only that module "
                    "adds its listed multiplier_delta and offset_delta. End-to-end observations for starts "
                    f"{bug_starts} are {list(bug_signatures[f'H{true_bug:02d}'])}. Infer the unique hypothesis and "
                    "return H:file:line exactly."
                ),
                "evaluator": "normalized_exact_public_output",
                "expected_public_output": f"H{true_bug:02d}:module_{true_bug:02d}.py:{20 + true_bug}",
                **_latent_geometry(
                    bug_signatures, include_entanglement=include_evidence_entanglement
                ),
            }
            cases.append({**bug_material, "case_id": _sha(bug_material), "answer_hash": _sha(bug_material["expected_public_output"])})

            # Candidate patches share the same interface. Training traces identify
            # the recurrence; the requested answer applies it to a fresh input.
            patches: list[tuple[int, int, int]] = []
            while len(patches) < hypothesis_count:
                candidate = (rng.randrange(2, 19), rng.randrange(1, 29), rng.randrange(1, 31))
                if candidate not in patches:
                    patches.append(candidate)

            def run_patch(patch: tuple[int, int, int], start: int, values: list[int]) -> int:
                a, b, c = patch
                value = start
                for index, item in enumerate(values):
                    value = (a * value + b * item + c * index) % 1013
                return value

            repair_probes: list[tuple[int, list[int]]] = []
            repair_signatures: dict[str, tuple[int, ...]] = {}
            while len(repair_probes) < 7:
                repair_probes.append((rng.randrange(2, 100), [rng.randrange(2, 80) for _ in range(4 + level)]))
                repair_signatures = {
                    f"P{i:02d}": tuple(run_patch(patch, start, values) for start, values in repair_probes)
                    for i, patch in enumerate(patches)
                }
                if len(set(repair_signatures.values())) == hypothesis_count and len(repair_probes) >= 2 + level:
                    break
            true_patch = rng.randrange(hypothesis_count)
            held_start = rng.randrange(2, 100)
            held_values = [
                rng.randrange(2, 90)
                for _ in range(6 + level * 2 * repair_transfer_multiplier)
            ]
            repair_material = {
                "family": "multi_step_code_repair", "difficulty_level": level, "variant": variant,
                "difficulty_mechanism": "latent_patch_from_sparse_training_traces",
                "dependency_depth": len(held_values),
                "prompt": (
                    "Candidate patches P00.. apply x=(a*x+b*item+c*i) mod 1013 using tuples "
                    f"{list(enumerate(patches))}. Training inputs are {repair_probes}; their terminal outputs under "
                    f"the deployed patch are {list(repair_signatures[f'P{true_patch:02d}'])}. Infer the unique patch, "
                    f"then run held input start={held_start}, values={held_values}. Return P:final exactly."
                ),
                "evaluator": "normalized_exact_public_output",
                "expected_public_output": f"P{true_patch:02d}:{run_patch(patches[true_patch], held_start, held_values)}",
                **_latent_geometry(
                    repair_signatures, include_entanglement=include_evidence_entanglement
                ),
            }
            cases.append({**repair_material, "case_id": _sha(repair_material), "answer_hash": _sha(repair_material["expected_public_output"])})

            # Competing eligibility policies are all structurally valid. Historical
            # panels reveal the deployed policy before it is applied to a target.
            all_policies = [(window, support, parent) for window in range(4) for support in range(1, 5) for parent in (0, 1)]
            rng.shuffle(all_policies)
            policies = all_policies[:hypothesis_count]

            def eligible(policy: tuple[int, int, int], panel: list[tuple[str, int, str, int, str | None]], epoch: int) -> str:
                window, support_min, parent_required = policy
                accepted: set[str] = set()
                changed = True
                while changed:
                    changed = False
                    for ident, row_epoch, status, support, parent in panel:
                        ok_parent = not parent_required or parent is None or parent in accepted
                        if ident not in accepted and row_epoch >= epoch - window and status == "active" and support >= support_min and ok_parent:
                            accepted.add(ident); changed = True
                return ",".join(sorted(accepted)) if accepted else "NONE"

            diagnostic_epoch = 23
            stale_panels: list[tuple[int, list[tuple[str, int, str, int, str | None]]]] = [
                (diagnostic_epoch, [(f"age{age}", diagnostic_epoch - age, "active", 4, None)])
                for age in range(4)
            ]
            stale_panels.extend(
                (diagnostic_epoch, [(f"support{support}", diagnostic_epoch, "active", support, None)])
                for support in range(1, 5)
            )
            stale_panels.append((diagnostic_epoch, [
                ("blocked_parent", diagnostic_epoch, "contested", 4, None),
                ("dependent_child", diagnostic_epoch, "active", 4, "blocked_parent"),
            ]))
            stale_signatures = {
                f"S{i:02d}": tuple(eligible(policy, panel, epoch) for epoch, panel in stale_panels)
                for i, policy in enumerate(policies)
            }
            true_policy = rng.randrange(hypothesis_count)
            target_epoch = 25
            target_panel = [
                (f"t{i}", target_epoch - rng.randrange(4), rng.choice(("active", "active", "contested")), rng.randrange(1, 5), None if i < 2 else f"t{rng.randrange(i)}")
                for i in range(10 + level)
            ]
            stale_material = {
                "family": "stale_state_detection", "difficulty_level": level, "variant": variant,
                "difficulty_mechanism": "latent_eligibility_policy_from_history",
                "dependency_depth": len(target_panel),
                "prompt": (
                    "Candidate policies S00.. are (epoch_window,min_support,parent_required): "
                    f"{list(enumerate(policies))}. A row is eligible when active, inside the epoch window, has enough "
                    "support, and—when required—its parent is eligible. Historical (epoch,panel) cases are "
                    f"{stale_panels}; deployed outputs are {list(stale_signatures[f'S{true_policy:02d}'])}. Infer the "
                    f"unique policy and apply it to target epoch={target_epoch}, panel={target_panel}. Return S:IDs."
                ),
                "evaluator": "normalized_exact_public_output",
                "expected_public_output": f"S{true_policy:02d}:{eligible(policies[true_policy], target_panel, target_epoch)}",
                **_latent_geometry(
                    stale_signatures, include_entanglement=include_evidence_entanglement
                ),
            }
            cases.append({**stale_material, "case_id": _sha(stale_material), "answer_hash": _sha(stale_material["expected_public_output"])})

            # Candidate hidden edges are locally indistinguishable. Weighted build
            # traces reveal the edge; a new weight panel requests its schedule.
            node_count = 6 + level * 2
            nodes = [f"n{i:02d}" for i in range(node_count)]
            candidates = [(nodes[parent], nodes[child]) for child in range(2, node_count) for parent in range(child)]
            rng.shuffle(candidates)
            candidate_edges = candidates[:hypothesis_count]

            def schedule(edge: tuple[str, str], weights: Mapping[str, int]) -> str:
                parent, child = edge
                remaining, emitted = set(nodes), []
                while remaining:
                    ready = [node for node in remaining if node != child or parent in emitted]
                    chosen = min(ready, key=lambda node: (int(weights[node]), node))
                    emitted.append(chosen); remaining.remove(chosen)
                return ">".join(emitted)

            build_probes: list[dict[str, int]] = []
            architecture_signatures: dict[str, tuple[str, ...]] = {}
            while len(build_probes) < 14:
                order = list(range(1, node_count + 1)); rng.shuffle(order)
                build_probes.append({node: order[index] for index, node in enumerate(nodes)})
                architecture_signatures = {
                    f"E{i:02d}": tuple(schedule(edge, weights) for weights in build_probes)
                    for i, edge in enumerate(candidate_edges)
                }
                if len(set(architecture_signatures.values())) == hypothesis_count and len(build_probes) >= 3 + level:
                    break
            true_edge = rng.randrange(hypothesis_count)
            target_order = list(range(1, node_count + 1)); rng.shuffle(target_order)
            target_weights = {node: target_order[index] for index, node in enumerate(nodes)}
            signature_table = (
                f" Candidate historical signature table is {architecture_signatures}."
                if architecture_signature_table else ""
            )
            architecture_material = {
                "family": "architecture_reconstruction", "difficulty_level": level, "variant": variant,
                "difficulty_mechanism": "latent_dependency_from_build_traces",
                "dependency_depth": node_count,
                "prompt": (
                    f"Nodes are {nodes}. Exactly one candidate hidden edge parent->child is deployed: "
                    f"{list(enumerate(candidate_edges))}. For each weight map, repeatedly emit the ready node with "
                    f"lowest weight (tie by name). Historical weights are {build_probes}; observed schedules are "
                    f"{list(architecture_signatures[f'E{true_edge:02d}'])}.{signature_table} Infer the unique edge and schedule target "
                    f"weights {target_weights}. Return E:parent->child:schedule."
                ),
                "evaluator": "normalized_exact_public_output",
                "expected_public_output": f"E{true_edge:02d}:{candidate_edges[true_edge][0]}->{candidate_edges[true_edge][1]}:{schedule(candidate_edges[true_edge], target_weights)}",
                **_latent_geometry(
                    architecture_signatures, include_entanglement=include_evidence_entanglement
                ),
            }
            cases.append({**architecture_material, "case_id": _sha(architecture_material), "answer_hash": _sha(architecture_material["expected_public_output"])})

    cases.sort(key=lambda row: (row["family"], row["difficulty_level"], row["variant"]))
    material = {
        "schema_version": (
            "cortex-latent-cause-corpus/1.1"
            if include_evidence_entanglement else "cortex-latent-cause-corpus/1.0"
        ), "version": corpus_version,
        "seed_commitment": _sha(seed), "task_families": list(LATENT_CAUSE_FAMILIES),
        "maximum_level": int(maximum_level), "variants_per_level": int(variants_per_level),
        "cases": cases, "development_only": True, "held_out": False,
        "confirmatory_eligible": False, "model_identity_in_ontology": False,
        "difficulty_law": (
            "hypothesis_entropy_evidence_entanglement_transfer_burden_and_observed_cost"
            if include_evidence_entanglement
            else "residual_hypothesis_entropy_and_downstream_evidence_resolution"
        ),
    }
    return {**material, "corpus_hash": _sha(material)}


def build_cost_entanglement_corpus(
    *, seed: str = "cortex-v986-cost-entanglement-development", maximum_level: int = 4,
    variants_per_level: int = 8,
) -> dict[str, Any]:
    """Build v9.8.6 cases with structural evidence geometry and bounded rebalance."""
    return build_latent_cause_corpus(
        seed=seed,
        maximum_level=maximum_level,
        variants_per_level=variants_per_level,
        include_evidence_entanglement=True,
        architecture_signature_table=True,
        repair_transfer_multiplier=2,
        corpus_version="9.8.6",
    )


def build_held_out_bundle(
    calibration: Mapping[str, Any],
    development_corpus: Mapping[str, Any],
    *,
    secret_seed: str,
    cases_per_family: int = 8,
) -> dict[str, Any]:
    """Create a disjoint public manifest and private exact-evaluator key."""
    verification = verify_difficulty_calibration(calibration)
    if not verification["valid"]:
        raise ValueError(f"difficulty calibration is invalid: {verification['errors']}")
    selected = calibration.get("selected")
    if calibration.get("overall_state") != "pass" or not isinstance(selected, Mapping) or not selected:
        raise ValueError("every declared family must have an informative selected level")
    max_level = max(int(row["difficulty_level"]) for row in selected.values())
    generated = build_difficulty_ladder_corpus(
        seed=f"heldout:{secret_seed}", maximum_level=max_level, variants_per_level=cases_per_family
    )
    development_ids = {str(row["case_id"]) for row in development_corpus.get("cases") or []}
    chosen = [
        row for row in generated["cases"]
        if row["family"] in selected
        and int(row["difficulty_level"]) == int(selected[row["family"]]["difficulty_level"])
    ]
    if any(str(row["case_id"]) in development_ids for row in chosen):
        raise ValueError("held-out corpus overlaps development cases")
    answer_key = {str(row["case_id"]): str(row["expected_public_output"]) for row in chosen}
    public_cases = [
        {str(key): value for key, value in row.items() if str(key) != "expected_public_output"}
        for row in chosen
    ]
    key_material = {"answers": answer_key, "secret_seed_commitment": _sha(secret_seed)}
    public_material = {
        "schema_version": "cortex-heldout-corpus-seal/1.0",
        "version": "9.8.2",
        "source_calibration_hash": calibration["calibration_hash"],
        "development_corpus_hash": development_corpus.get("corpus_hash"),
        "secret_seed_commitment": _sha(secret_seed),
        "answer_key_commitment": _sha(key_material),
        "selected_levels": {str(name): str(row["difficulty_level"]) for name, row in sorted(selected.items())},
        "cases": public_cases,
        "case_count": len(public_cases),
        "held_out": True,
        "development_only": False,
        "eligible_for_preregistration": True,
        "confirmatory_evidence": False,
        "answers_present_in_public_manifest": False,
        "authority": {
            "host_mutate_authorized": False,
            "execution_authorized": False,
            "memory_admission_authorized": False,
            "policy_effect": False,
        },
    }
    manifest = {**public_material, "corpus_hash": _sha(public_material)}
    return {"manifest": manifest, "answer_key": key_material}


def verify_held_out_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    manifest = bundle.get("manifest")
    answer_key = bundle.get("answer_key")
    errors: list[str] = []
    if not isinstance(manifest, Mapping) or not isinstance(answer_key, Mapping):
        return {"valid": False, "state": "fail", "errors": ["bundle_shape_invalid"]}
    manifest_check = verify_held_out_manifest(manifest)
    errors.extend(manifest_check["errors"])
    if manifest.get("answer_key_commitment") != _sha(answer_key):
        errors.append("answer_key_commitment_invalid")
    public_cases = manifest.get("cases") or []
    if any("expected_public_output" in row for row in public_cases):
        errors.append("answer_leaked_into_public_manifest")
    public_ids = {str(row.get("case_id") or "") for row in public_cases}
    answer_ids = {str(key) for key in (answer_key.get("answers") or {})}
    if public_ids != answer_ids:
        errors.append("answer_key_case_binding_invalid")
    return {"valid": not errors, "state": "pass" if not errors else "fail", "errors": errors}


def verify_held_out_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Verify the public seal without revealing or requiring the private key."""
    errors: list[str] = []
    public_material = {str(key): value for key, value in manifest.items() if str(key) != "corpus_hash"}
    if manifest.get("schema_version") != "cortex-heldout-corpus-seal/1.0":
        errors.append("schema_version_invalid")
    if manifest.get("corpus_hash") != _sha(public_material):
        errors.append("corpus_hash_invalid")
    public_cases = manifest.get("cases") or []
    if any("expected_public_output" in row for row in public_cases):
        errors.append("answer_leaked_into_public_manifest")
    allowed_manifest_keys = {
        "schema_version", "version", "source_calibration_hash", "development_corpus_hash",
        "secret_seed_commitment", "answer_key_commitment", "selected_levels", "cases",
        "case_count", "held_out", "development_only", "eligible_for_preregistration",
        "confirmatory_evidence", "answers_present_in_public_manifest", "authority", "corpus_hash",
    }
    if set(str(key) for key in manifest) != allowed_manifest_keys:
        errors.append("manifest_schema_not_closed")
    allowed_case_keys = {
        "family", "difficulty_level", "variant", "difficulty_mechanism",
        "component_case_ids", "prompt", "evaluator", "case_id", "answer_hash",
    }
    if any(set(str(key) for key in row) != allowed_case_keys for row in public_cases):
        errors.append("public_case_schema_not_closed")
    if manifest.get("held_out") is not True or manifest.get("eligible_for_preregistration") is not True:
        errors.append("heldout_boundary_invalid")
    if manifest.get("confirmatory_evidence") is not False:
        errors.append("unexecuted_corpus_claim_invalid")
    return {"valid": not errors, "state": "pass" if not errors else "fail", "errors": errors}


__all__ = [
    "COUPLED_FAMILIES",
    "LATENT_CAUSE_FAMILIES",
    "SCHEMA_VERSION",
    "TASK_FAMILIES",
    "VERSION",
    "build_difficulty_ladder_corpus",
    "build_coupled_dependency_corpus",
    "build_cost_entanglement_corpus",
    "build_latent_cause_corpus",
    "build_discriminative_corpus",
    "build_held_out_bundle",
    "evaluate_case",
    "verify_held_out_bundle",
    "verify_held_out_manifest",
]
