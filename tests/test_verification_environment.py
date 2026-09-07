"""Environment coordinates are bounded provenance, not full applicability proof."""
import subprocess
from unittest.mock import patch

from cortex.coding_workspace import verification_environment, run_host_verification_step


def git_failure(error):
    real_run = subprocess.run
    def run(argv, *args, **kwargs):
        if argv == ["git", "--version"]:
            raise error
        return real_run(argv, *args, **kwargs)
    return run


def test_environment_identity_changes_with_runtime_coordinate():
    with patch("cortex.coding_workspace.platform.python_version", return_value="3.10.20"):
        first = verification_environment()
    with patch("cortex.coding_workspace.platform.python_version", return_value="3.12.2"):
        second = verification_environment()
    assert first["environment_hash"] != second["environment_hash"]
    assert first["authority_effect"] is False
    assert "dependency_state" in first["unresolved"]


def test_missing_git_remains_unknown():
    with patch("cortex.coding_workspace.subprocess.run", side_effect=git_failure(FileNotFoundError())):
        environment = verification_environment()
    assert environment["git_version"] is None
    assert set(environment) == {
        "schema_version", "os_family", "os_release", "architecture",
        "python_implementation", "python_version", "git_version", "execution_policy",
        "unresolved", "authority_effect", "environment_hash",
    }


def test_observation_binds_environment_without_persisting_host_path(tmp_path):
    result = run_host_verification_step(tmp_path, {"argv": ["{python}", "-c", "print('ok')"]})
    assert result["passed"]
    assert result["raw_observation"]["environment_hash"] == result["environment"]["environment_hash"]
    assert str(tmp_path) not in str(result["environment"])


def test_git_timeout_does_not_claim_tool_identity():
    with patch("cortex.coding_workspace.subprocess.run", side_effect=git_failure(subprocess.TimeoutExpired("git", 5))):
        assert verification_environment()["git_version"] is None
