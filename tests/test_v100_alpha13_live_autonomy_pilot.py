from pathlib import Path

import pytest

from benchmarks.live_autonomy_pilot import DEFAULT_CORPUS, load_cases, resolve_engine
from cortex.evaluation import TaskEvaluationContract, evaluate_task_result


def test_pilot_corpus_is_small_frozen_and_independently_evaluable() -> None:
    cases = load_cases(Path(DEFAULT_CORPUS))
    assert len(cases) == 2
    for case in cases:
        contract = TaskEvaluationContract.from_mapping(case["evaluation_contract"])
        expected = str(contract.expected_value)
        result = evaluate_task_result(contract, {"text": expected})
        assert result["success"] is True
        assert result["independent"] is True


def test_engine_is_selected_at_runtime_without_a_coded_model_default() -> None:
    assert resolve_engine(
        {"selected_provider": "openai", "selected_model": "runtime-model"}
    ) == ("openai", "runtime-model")
    assert resolve_engine(
        {"selected_provider": "openai", "selected_model": "stored"},
        "xai",
        "operator-selected",
    ) == ("xai", "operator-selected")
    with pytest.raises(ValueError, match="select a provider/model"):
        resolve_engine({})
