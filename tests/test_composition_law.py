"""Noncompensatory composition and typed residual bundle tests."""

from __future__ import annotations

from cortex.math_net.composition import (
    geometric_mean,
    noncompensatory_compose,
    typed_residual_energy,
)


def test_geometric_mean_is_noncompensatory() -> None:
    # One missing essential factor (0) collapses the product.
    collapsed = geometric_mean({"relevance": 1.0, "bridge": 1.0, "novelty": 0.0})
    assert collapsed["value"] < 1e-6
    healthy = geometric_mean({"relevance": 0.8, "bridge": 0.8, "novelty": 0.8})
    assert 0.79 < healthy["value"] < 0.81


def test_hard_gate_zeros_phi_regardless_of_factors() -> None:
    blocked = noncompensatory_compose(
        gate=0,
        factors={"closure": 1.0, "surplus": 1.0, "coverage": 1.0},
        defects={"redundancy": 0.0},
    )
    assert blocked["phi"] == 0.0
    assert blocked["admissible"] is False
    open_gate = noncompensatory_compose(
        gate=1,
        factors={"closure": 1.0, "surplus": 1.0, "coverage": 1.0},
        defects={"redundancy": 0.0},
    )
    assert open_gate["phi"] == 1.0
    assert open_gate["admissible"] is True


def test_defect_penalty_multiplies_survival() -> None:
    report = noncompensatory_compose(
        gate=1,
        factors={"a": 1.0},
        defects={"concentration": 0.5},
    )
    assert abs(report["phi"] - 0.5) < 1e-9
    assert abs(report["defect_survival"] - 0.5) < 1e-9


def test_typed_residual_bundle_is_direct_sum() -> None:
    energy = typed_residual_energy(
        {
            "self": 0.1,
            "prediction": [0.2, 0.0],
            "operator": {"events": 0.0, "sessions": 0.3},
        }
    )
    assert energy["direct_sum"] is True
    assert energy["authority"] is False
    assert abs(energy["blocks"]["self"] - 0.01) < 1e-12
    assert abs(energy["blocks"]["prediction"] - 0.04) < 1e-12
    assert abs(energy["blocks"]["operator"] - 0.09) < 1e-12
    assert abs(energy["total_diagnostic_energy"] - 0.14) < 1e-12
