"""Raw capture identity is distinct from the bounded human preview."""
import hashlib
import subprocess
from unittest.mock import patch

from cortex.coding_workspace import run_host_verification_step


def observe(root, stdout, stderr=b""):
    with patch("cortex.coding_workspace.subprocess.run", return_value=
               subprocess.CompletedProcess(["fixture"], 0, stdout, stderr)):
        return run_host_verification_step(root, {"argv": ["fixture"]})


def test_lossy_preview_does_not_collapse_raw_identity(tmp_path):
    first = observe(tmp_path, b"\xff")
    second = observe(tmp_path, b"\xfe")
    assert first["output"] == second["output"]
    assert first["raw_observation"]["stdout_sha256"] != second["raw_observation"]["stdout_sha256"]


def test_truncation_and_stream_boundaries_do_not_collapse_identity(tmp_path):
    first = observe(tmp_path, b"a" + b"x" * 5000)
    second = observe(tmp_path, b"b" + b"x" * 5000)
    assert first["output"] == second["output"]
    assert first["raw_observation"]["stdout_sha256"] != second["raw_observation"]["stdout_sha256"]
    assert observe(tmp_path, b"a", b"b")["raw_observation"]["stdout_byte_length"] == 1


def test_real_subprocess_captures_exact_bytes(tmp_path):
    result = run_host_verification_step(tmp_path, {"argv": ["{python}", "-c",
        "import os; os.write(1, bytes([255,13,10])); os.write(2, b'error')"]})
    raw = result["raw_observation"]
    assert result["passed"] and raw["capture_complete"]
    assert raw["stdout_sha256"] == hashlib.sha256(b"\xff\r\n").hexdigest()
    assert raw["stderr_sha256"] == hashlib.sha256(b"error").hexdigest()


def test_timeout_retains_partial_identity_not_success(tmp_path):
    with patch("cortex.coding_workspace.subprocess.run", side_effect=
               subprocess.TimeoutExpired(["fixture"], 1, output=b"partial", stderr=b"err")):
        result = run_host_verification_step(tmp_path, {"argv": ["fixture"]})
    assert not result["passed"]
    assert not result["raw_observation"]["capture_complete"]
    assert result["raw_observation"]["stdout_sha256"] == hashlib.sha256(b"partial").hexdigest()
