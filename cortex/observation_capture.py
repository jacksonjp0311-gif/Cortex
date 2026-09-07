"""Bounded streaming capture for host verification observations.

Raw evidence identity is the incremental digest of bytes actually read.
The human preview is a lossy bounded tail and never defines identity.
Direct-child termination does not prove process-tree cleanup.
"""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import threading
import time
from collections.abc import Mapping, Sequence
from typing import Any

OBSERVATION_SCHEMA_V11 = "cortex-host-raw-observation/1.1"
OBSERVATION_SCHEMA_V12 = "cortex-host-raw-observation/1.2"
PREVIEW_TAIL_BYTES = 4096
READ_CHUNK = 8192
DEFAULT_MAX_STDOUT = 1_048_576
DEFAULT_MAX_STDERR = 1_048_576
PROCESS_TREE_CLEANUP = "UNKNOWN"
ENV_ALLOWLIST = (
    "PATH", "PATHEXT", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "TEMP", "TMP",
    "HOME", "USER", "USERNAME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "LANG", "LC_ALL",
    "PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "NUMBER_OF_PROCESSORS",
)


def experiment_environment() -> dict[str, str]:
    env = {key: os.environ[key] for key in ENV_ALLOWLIST if key in os.environ}
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def environment_policy() -> dict[str, Any]:
    body = {
        "schema_version": "cortex-experiment-environment-policy/1.0",
        "mode": "explicit-allowlist",
        "allowlist": list(ENV_ALLOWLIST),
        "inherits_full_process_environment": False,
        "network_isolation": "UNENFORCED",
        "external_path_isolation": "DECLARATIVE_ONLY",
        "authority_effect": False,
    }
    return {**body, "environment_policy_hash": hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}


def _kill(proc: subprocess.Popen[bytes]) -> None:
    try:
        proc.kill()
    except OSError:
        return


def _terminate_tree(proc: subprocess.Popen[bytes]) -> str:
    if os.name == "nt":
        try:
            completed = subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                capture_output=True, timeout=5, check=False, shell=False,
            )
            if completed.returncode == 0:
                return "windows-taskkill-tree/attempted"
        except (OSError, subprocess.TimeoutExpired):
            pass
        _kill(proc)
        return "UNKNOWN"
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        return "posix-killpg/attempted"
    except OSError:
        _kill(proc)
        return "UNKNOWN"


def _reader(
    pipe: Any,
    hasher: hashlib._Hash,
    length: list[int],
    preview: bytearray,
    limit: int,
    exceeded: list[bool],
    eof: list[bool],
) -> None:
    try:
        while True:
            chunk = pipe.read(READ_CHUNK)
            if not chunk:
                eof[0] = True
                return
            hasher.update(chunk)
            length[0] += len(chunk)
            preview.extend(chunk)
            if len(preview) > PREVIEW_TAIL_BYTES * 2:
                del preview[:-PREVIEW_TAIL_BYTES]
            if length[0] > limit:
                exceeded[0] = True
                return
    except OSError:
        return


def capture_bounded_subprocess(
    argv: Sequence[str],
    *,
    cwd: str | os.PathLike[str],
    timeout_seconds: int,
    max_stdout_bytes: int = DEFAULT_MAX_STDOUT,
    max_stderr_bytes: int = DEFAULT_MAX_STDERR,
) -> dict[str, Any]:
    """Stream stdout and stderr independently. Never buffer unbounded RAM."""
    timeout_seconds = max(1, min(int(timeout_seconds), 1800))
    max_stdout_bytes = max(1, int(max_stdout_bytes))
    max_stderr_bytes = max(1, int(max_stderr_bytes))
    started = time.perf_counter()
    stdout_hash = hashlib.sha256()
    stderr_hash = hashlib.sha256()
    stdout_len = [0]
    stderr_len = [0]
    stdout_preview = bytearray()
    stderr_preview = bytearray()
    stdout_exceeded = [False]
    stderr_exceeded = [False]
    stdout_eof = [False]
    stderr_eof = [False]
    timed_out = False
    creationflags = 0
    popen_kwargs: dict[str, Any] = {}
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        popen_kwargs["start_new_session"] = True
    env_policy = environment_policy()
    proc = subprocess.Popen(
        list(argv),
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        env=experiment_environment(),
        creationflags=creationflags,
        **popen_kwargs,
    )
    tree_status = PROCESS_TREE_CLEANUP
    assert proc.stdout is not None and proc.stderr is not None
    threads = [
        threading.Thread(
            target=_reader,
            args=(proc.stdout, stdout_hash, stdout_len, stdout_preview, max_stdout_bytes, stdout_exceeded, stdout_eof),
            daemon=True,
        ),
        threading.Thread(
            target=_reader,
            args=(proc.stderr, stderr_hash, stderr_len, stderr_preview, max_stderr_bytes, stderr_exceeded, stderr_eof),
            daemon=True,
        ),
    ]
    for thread in threads:
        thread.start()
    deadline = time.monotonic() + timeout_seconds
    output_limit_exceeded = False
    try:
        while True:
            output_limit_exceeded = stdout_exceeded[0] or stderr_exceeded[0]
            if output_limit_exceeded:
                tree_status = _terminate_tree(proc)
                break
            if time.monotonic() >= deadline:
                timed_out = True
                tree_status = _terminate_tree(proc)
                break
            if proc.poll() is not None and not any(thread.is_alive() for thread in threads):
                break
            time.sleep(0.01)
        for thread in threads:
            thread.join(timeout=1.0)
        try:
            proc.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            tree_status = _terminate_tree(proc)
            proc.wait(timeout=1.0)
    finally:
        for stream in (proc.stdout, proc.stderr):
            try:
                stream.close()
            except OSError:
                pass
    output_limit_exceeded = stdout_exceeded[0] or stderr_exceeded[0]
    drain_finished = stdout_eof[0] and stderr_eof[0] and not timed_out and not output_limit_exceeded
    capture_complete = drain_finished and not timed_out and not output_limit_exceeded
    returncode = proc.returncode if proc.returncode is not None else -1
    if timed_out or output_limit_exceeded:
        returncode = -1 if timed_out else returncode
    failure = None
    if output_limit_exceeded:
        failure = "OUTPUT_LIMIT_EXCEEDED"
    elif timed_out:
        failure = "PROCESS_TIMEOUT" if stdout_len[0] + stderr_len[0] == 0 else "CAPTURE_INCOMPLETE"
    elif not capture_complete:
        failure = "CAPTURE_INCOMPLETE"
    preview = (bytes(stdout_preview[-PREVIEW_TAIL_BYTES:]) + bytes(stderr_preview[-PREVIEW_TAIL_BYTES:]))
    return {
        "argv": list(argv),
        "returncode": returncode,
        "timed_out": timed_out,
        "output_limit_exceeded": output_limit_exceeded,
        "drain_finished": drain_finished,
        "capture_complete": capture_complete,
        "stdout_sha256": stdout_hash.hexdigest(),
        "stderr_sha256": stderr_hash.hexdigest(),
        "stdout_byte_length": stdout_len[0],
        "stderr_byte_length": stderr_len[0],
        "max_stdout_bytes": max_stdout_bytes,
        "max_stderr_bytes": max_stderr_bytes,
        "duration_ms": round((time.perf_counter() - started) * 1000.0, 3),
        "process_tree_cleanup": tree_status,
        "environment_policy_hash": env_policy["environment_policy_hash"],
        "failure_attribution": failure,
        "preview_bytes": preview,
        "passed": returncode == 0 and capture_complete and not timed_out and not output_limit_exceeded,
    }


def observation_from_capture(
    capture: Mapping[str, Any],
    *,
    environment_hash: str,
    schema_version: str = OBSERVATION_SCHEMA_V12,
) -> dict[str, Any]:
    body = {
        "schema_version": schema_version,
        "stdout_sha256": capture["stdout_sha256"],
        "stderr_sha256": capture["stderr_sha256"],
        "stdout_byte_length": capture["stdout_byte_length"],
        "stderr_byte_length": capture["stderr_byte_length"],
        "returncode": capture["returncode"],
        "timed_out": capture["timed_out"],
        "capture_complete": capture["capture_complete"],
        "environment_hash": environment_hash,
        "duration_ms": capture["duration_ms"],
    }
    if schema_version == OBSERVATION_SCHEMA_V12:
        body.update({
            "output_limit_exceeded": capture["output_limit_exceeded"],
            "drain_finished": capture["drain_finished"],
            "max_stdout_bytes": capture["max_stdout_bytes"],
            "max_stderr_bytes": capture["max_stderr_bytes"],
            "process_tree_cleanup": capture["process_tree_cleanup"],
            "environment_policy_hash": capture.get("environment_policy_hash"),
            "preview_policy": "bounded-tail-4096/1.0",
        })
    return body


__all__ = [
    "DEFAULT_MAX_STDERR",
    "DEFAULT_MAX_STDOUT",
    "OBSERVATION_SCHEMA_V11",
    "OBSERVATION_SCHEMA_V12",
    "capture_bounded_subprocess",
    "environment_policy",
    "experiment_environment",
    "observation_from_capture",
]
