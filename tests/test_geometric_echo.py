"""v8.2.6 fixed-direction four-dimensional pulse/echo tests."""

from __future__ import annotations

from pathlib import Path

from cortex.geometric_echo import geometric_echo_report, operational_state, run_geometric_echo


class FakeStore:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get_setting(self, key, default=None):
        return self.values.get(key, default)

    def set_setting(self, key, value):
        self.values[key] = value


def _store():
    return FakeStore({
        "source_admission_latest:R": {
            "candidate_stage": {"source_reserve": {"recall": 0.67}},
            "final_stage": {"source_reserve": {"recall": 0.52}},
        },
        "bridge_shadow_latest:R": {
            "top_decile_degree_share": 0.7,
            "candidates": [{"bridge_potential": 0.8}, {"bridge_potential": 0.6}],
        },
        "resonance_sweep_latest:R": {
            "status": "no_stable_peak",
            "best": {"coherence": 0.9, "frequency": 0.5},
            "frame_count": 1,
            "all_frame_count": 10,
            "body_epoch_id": "epoch",
        },
        "interlock_shadow_latest:R": {
            "data_ready": False,
            "mean_alignment": 0.9,
            "counts": {"resolved": 0, "valid": 0, "candidates": 0},
        },
    })


def test_basis_echoes_reconstruct_the_state() -> None:
    state = {"vector": [0.2, 0.4, 0.6, 0.8], "values": {}}
    report = geometric_echo_report(state)
    assert report["pulse_count"] == 8
    assert report["axis_echoes"] == {
        "evidence": 0.2,
        "geometry": 0.4,
        "temporal": 0.6,
        "interlock": 0.8,
    }
    assert report["reconstruction_error"] == 0.0
    assert report["dominant_axis"] == "interlock"


def test_gated_axes_stay_silent() -> None:
    state = operational_state(_store(), "R")
    assert state["values"]["evidence"] == 0.67
    assert state["values"]["geometry"] == 0.5
    assert state["values"]["temporal"] == 0.0
    assert state["values"]["interlock"] == 0.0
    assert state["gate_mask"]["temporal"] == 0
    assert state["gate_mask"]["interlock"] == 0
    assert state["observability_rank"] == 2

    report = geometric_echo_report(state)
    assert "evidence" in report["active_axes"]
    assert "temporal" in report["silent_unmeasured_axes"]
    assert "interlock" in report["silent_unmeasured_axes"]
    assert report["tight_frame"]["holds"] is True
    assert report["claim_boundary"].startswith("Four-dimensional")


def test_missing_inputs_do_not_create_a_geometry_echo() -> None:
    state = operational_state(FakeStore(), "R")
    assert state["vector"] == [0.0, 0.0, 0.0, 0.0]
    assert state["observability_rank"] == 0
    report = geometric_echo_report(state)
    assert report["field_condition"] == "silent"
    assert report["silent_unmeasured_axes"] == [
        "evidence",
        "geometry",
        "temporal",
        "interlock",
    ]
    assert report["observability_rank"] == 0


def test_eight_probes_form_a_2_tight_frame() -> None:
    report = geometric_echo_report({"vector": [0.2, 0.4, 0.6, 0.8]})
    assert report["tight_frame"]["holds"] is True
    expected = 2.0 * sum(value * value for value in report["masked_state_vector"])
    assert abs(report["echo_energy"] - expected) < 1e-8
    assert report["reconstruction_error"] == 0.0


def test_run_is_read_only_unless_persistence_is_explicit(tmp_path: Path) -> None:
    store = _store()
    report = run_geometric_echo(store, "R", persist=False)
    assert "geometric_echo_latest:R" not in store.values
    assert report["body_epoch_id"] == "epoch"

    persisted = run_geometric_echo(store, "R", home=tmp_path, persist=True)
    assert store.values["geometric_echo_latest:R"]["repo"] == "R"
    assert Path(persisted["report_path"]).exists()
