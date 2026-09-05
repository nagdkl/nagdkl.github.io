from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys

MODULE = Path(__file__).parents[1] / "scripts/run_pages_recovery_v4.py"


def load():
    spec = importlib.util.spec_from_file_location("pages_v4", MODULE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_source_has_no_recursive_windows_scan_or_shell_true():
    text = MODULE.read_text(encoding="utf-8")
    assert "/mnt/c/Users" not in text
    assert "shell=True" not in text
    assert "os.system" not in text


def test_invalid_expected_main_fails_closed(tmp_path):
    cp = subprocess.run(
        [sys.executable, str(MODULE), "--expected-main", "bad", "--state-root", str(tmp_path)],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=10,
    )
    assert cp.returncode == 78
    assert "invalid_expected_main" in cp.stderr


def test_missing_git_fails_closed(monkeypatch, tmp_path, capsys):
    mod = load()
    monkeypatch.setattr(mod.shutil, "which", lambda _: None)
    rc = mod.main(["--state-root", str(tmp_path)])
    assert rc == 78
    assert "missing_git" in capsys.readouterr().err


def test_clone_failure_is_typed(monkeypatch, tmp_path, capsys):
    mod = load()
    monkeypatch.setattr(mod.shutil, "which", lambda _: "/usr/bin/git")
    monkeypatch.setattr(mod, "run", lambda *a, **k: subprocess.CompletedProcess([], 1, "", "boom"))
    rc = mod.main(["--state-root", str(tmp_path), "--repo-url", "https://invalid.invalid/repo.git"])
    assert rc == 78
    assert "clone_failed" in capsys.readouterr().err


def test_run_from_arbitrary_dirty_repo_does_not_touch_cwd(tmp_path):
    dirty = tmp_path / "dirty"
    dirty.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=dirty, check=True)
    marker = dirty / "keep.txt"
    marker.write_text("original\ndirty\n", encoding="utf-8")
    before = marker.read_bytes()
    cp = subprocess.run(
        [sys.executable, str(MODULE), "--expected-main", "bad", "--state-root", str(tmp_path / "state")],
        cwd=dirty, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=10,
    )
    assert cp.returncode == 78
    assert marker.read_bytes() == before
