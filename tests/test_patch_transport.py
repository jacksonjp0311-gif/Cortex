"""Patch transport must not invent CR bytes or disable whitespace protection."""
import subprocess
from unittest.mock import patch

from cortex.coding_workspace import _git


def test_git_stdin_is_exact_utf8_bytes(tmp_path):
    text = "diff --git a/a b/a\n+é\n"
    with patch("cortex.coding_workspace.subprocess.run", return_value=subprocess.CompletedProcess([], 0, b"ok\n", b"")) as run:
        result = _git(tmp_path, ["apply", "--check", "-"], text)
    assert run.call_args.kwargs["input"] == text.encode("utf-8")
    assert not run.call_args.kwargs.get("text", False)
    assert result.stdout == "ok\n"


def test_added_leading_line_applies_without_weakening_whitespace(tmp_path):
    _git(tmp_path, ["init", "-q"])
    (tmp_path / "a.py").write_bytes(b"value = 1\n")
    clean = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1,2 @@\n+import copy\n value = 1\n"
    assert _git(tmp_path, ["apply", "--check", "--whitespace=error-all", "-"], clean).returncode == 0
    dirty = clean.replace("+import copy\n", "+import copy  \n")
    assert _git(tmp_path, ["apply", "--check", "--whitespace=error-all", "-"], dirty).returncode != 0
