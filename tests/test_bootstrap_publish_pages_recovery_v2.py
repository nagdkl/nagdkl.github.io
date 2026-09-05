from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

MODULE_PATH = Path(__file__).parents[1] / "scripts/bootstrap_publish_pages_recovery_v2.py"
spec = importlib.util.spec_from_file_location("bootstrap_v2", MODULE_PATH)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


def test_source_pathset_is_exact_and_no_main_write():
    assert "index.md" not in m.SOURCE_PATHS
    assert "_layouts/default.html" not in m.SOURCE_PATHS
    assert len(m.SOURCE_PATHS) == len(set(m.SOURCE_PATHS)) == 10
    assert m.BRANCH != "main"


def test_gitleaks_asset_is_pinned():
    assert m.GL_VERSION == "8.30.1"
    assert len(m.GL_ASSET_SHA256) == 64
    int(m.GL_ASSET_SHA256, 16)
    assert m.GL_ASSET_URL.startswith("https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/")


def test_safe_extract_rejects_traversal(tmp_path: Path):
    import io, tarfile
    archive = tmp_path / "bad.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        info = tarfile.TarInfo("../gitleaks")
        data = b"x"
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    try:
        m.safe_extract_gitleaks(archive, tmp_path / "out")
    except m.Blocked as exc:
        assert exc.reason == "unsafe_gitleaks_archive_member"
    else:
        raise AssertionError("unsafe archive accepted")


def test_remote_branch_sha_handles_absent(tmp_path: Path):
    repo = tmp_path / "repo"
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=repo, check=True)
    assert m.remote_branch_sha(repo, "missing") is None


def test_no_force_push_or_direct_main_ref_literal():
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "--force" not in source
    assert "refs/heads/main" not in source
    assert "git push origin main" not in source


def test_timeout_is_blocked_not_retry():
    try:
        m.cp(["/bin/sleep", "2"], timeout_s=1)
    except m.Blocked as exc:
        assert exc.reason == "command_timeout"
        assert exc.retry_safe is False
        assert exc.exit_code == 124
    else:
        raise AssertionError("timeout not blocked")


def test_fallback_git_identity_is_noreply_and_local_only():
    assert m.FALLBACK_GIT_NAME == "nagdkl"
    assert m.FALLBACK_GIT_EMAIL.endswith("+nagdkl@users.noreply.github.com")
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "--global" not in source


def test_hard_download_timeout_and_currentness_fences_present():
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "signal.setitimer(signal.ITIMER_REAL, timeout_s)" in source
    assert "prepush_remote_currentness_fence" in source
    assert "postpush_base_currentness_fence" in source
    assert "base_drift_after_branch_checkpoint" in source
