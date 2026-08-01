from cortex.mirror import _aria_substrate_view


def test_mirror_reads_current_aria_surfaces() -> None:
    context = {
        "aria_materialization": {"mode": "active", "materialized": True},
        "efficiency": {
            "aria_substrate": {"eligible_nodes": 96, "deferred_remaining": 0}
        },
    }
    surface = _aria_substrate_view(context)
    assert surface["mode"] == "active"
    assert surface["materialized"] is True
    assert surface["eligible_nodes"] == 96


def test_mirror_retains_legacy_packet_compatibility() -> None:
    context = {
        "neural_interlink": {
            "metrics": {"aria_substrate": {"mode": "dormant", "eligible_nodes": 0}}
        }
    }
    surface = _aria_substrate_view(context)
    assert surface == {"mode": "dormant", "eligible_nodes": 0}
