from scripts.ci.version_gate import release_at_least


def test_historical_release_gate_accepts_newer_release() -> None:
    assert release_at_least("7.7.1", (7, 3, 0))
    assert release_at_least("8.0.0", (7, 7, 0))


def test_historical_release_gate_rejects_older_or_malformed_release() -> None:
    assert not release_at_least("7.6.9", (7, 7, 0))
    assert not release_at_least("development", (7, 3, 0))
