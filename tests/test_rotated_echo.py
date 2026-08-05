"""v8.2.7 fixed perception-rotation tests."""

from cortex.rotated_echo import rotate_vector, rotated_echo_report


def test_quarter_turn_is_orthonormal() -> None:
    vector = [0.6, 0.8, 0.0, 0.0]
    rotated = rotate_vector(vector, "evidence_geometry", 1)
    assert rotated == [-0.8, 0.6, 0.0, 0.0]
    assert sum(value * value for value in rotated) == 1.0


def test_active_subspace_alignment_is_measured_not_mutated() -> None:
    report = rotated_echo_report({
        "state_vector": [0.6, 0.8, 0.0, 0.0],
        "active_axes": ["evidence", "geometry"],
    })
    assert report["status"] == "aligned_subspace"
    assert report["rotation_count"] == 19
    assert report["best"]["alignment"] == 1.0
    assert report["surgery"]["actions"] == ["collect_same_epoch_frames", "resolve_interlock_outcomes"]
    assert report["surgery"]["policy_effect"] is False


def test_cross_axis_rotation_loses_alignment() -> None:
    report = rotated_echo_report({
        "state_vector": [1.0, 0.0, 0.0, 0.0],
        "active_axes": ["evidence"],
    })
    cross = next(item for item in report["rotations"] if item["name"] == "evidence_temporal_90")
    assert cross["alignment"] == 0.0
    assert cross["reconstruction_error"] == 0.0
    # High identity alignment with high fragility is a coordinate-artifact risk.
    assert report["identity_alignment"] == 1.0
    assert report["active_subspace_fragility"] == 1.0
    assert report["fragility_interpretation"] == "coordinate_artifact_risk"

