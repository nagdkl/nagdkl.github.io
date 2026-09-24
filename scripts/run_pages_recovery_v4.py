#!/usr/bin/env python3
"""Git-native Synergy Pages recovery launcher v4.

Runs from any directory. Creates an isolated checkout, verifies exact published
main, then invokes the checked-in read-only recovery verifier. No push, merge,
branch, release, or deployment mutation.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Sequence

REPO_URL = "https://github.com/nagdkl/nagdkl.github.io.git"
EXPECTED_BASE = "0e872af12b2aee39bc06df49bedf4e5a3179dbdc"
VERIFIER = Path("scripts/recover_pages_after_terminal_loss_v2.py")
STATE_ROOT = Path.home() / ".local/state/synergy-mesh/pages-recovery-v4/git-native"


def run(cmd: Sequence[str], *, cwd: Path | None = None, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(cmd), cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False, timeout=timeout, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("bounded_command_failed") from exc


def git(repo: Path, *args: str, timeout: int = 10) -> str:
    cp = run(["git", *args], cwd=repo, timeout=timeout)
    if cp.returncode != 0:
        raise RuntimeError("git_read_failed")
    return cp.stdout.strip()


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--expected-main", default=EXPECTED_BASE)
    p.add_argument("--repo-url", default=REPO_URL)
    p.add_argument("--state-root", type=Path, default=STATE_ROOT)
    p.add_argument("--clone-timeout", type=int, default=60)
    args = p.parse_args(argv)

    if shutil.which("git") is None:
        print("STOP reason=missing_git last_completed=0 next_safe_action=install_git retry_safe=true", file=sys.stderr)
        return 78
    if len(args.expected_main) != 40 or any(c not in "0123456789abcdef" for c in args.expected_main):
        print("STOP reason=invalid_expected_main last_completed=0 next_safe_action=use_exact_git_sha retry_safe=false", file=sys.stderr)
        return 78

    args.state_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(args.state_root, 0o700)
    run_dir = Path(tempfile.mkdtemp(prefix="run.", dir=args.state_root))
    os.chmod(run_dir, 0o700)
    repo = run_dir / "repo"
    print(f"RESUME last_confirmed=remote state=git_native_recovery run_dir={run_dir}", flush=True)

    try:
        print("STEP_START id=1 action=fresh_clone timeout=60s", flush=True)
        cp = run(["git", "clone", "--quiet", "--no-tags", args.repo_url, str(repo)], timeout=args.clone_timeout)
        if cp.returncode != 0:
            raise RuntimeError("clone_failed")
        print("STEP_OK id=1 result=fresh_clone_PASS last_confirmed=1", flush=True)

        print("STEP_START id=2 action=verify_exact_main timeout=10s", flush=True)
        head = git(repo, "rev-parse", "HEAD")
        if head != args.expected_main:
            print(f"STOP reason=canonical_main_drift observed={head} last_completed=1 next_safe_action=refresh_remote_evidence retry_safe=false", file=sys.stderr)
            return 78
        print(f"STEP_OK id=2 result=main_{head} last_confirmed=2", flush=True)

        verifier = repo / VERIFIER
        if not verifier.is_file():
            print("STOP reason=verifier_missing last_completed=2 next_safe_action=inspect_exact_remote_tree retry_safe=false", file=sys.stderr)
            return 78

        print("STEP_START id=3 action=execute_checked_in_read_only_verifier timeout=120s", flush=True)
        cp = run([sys.executable, str(verifier), "--expected-main", head], cwd=repo, timeout=120)
        sys.stdout.write(cp.stdout)
        sys.stderr.write(cp.stderr)
        if cp.returncode != 0:
            print(f"STOP reason=checked_in_verifier_exit_{cp.returncode} last_completed=2 next_safe_action=inspect_read_only_receipt retry_safe=true", file=sys.stderr)
            return cp.returncode
        print("STEP_OK id=3 result=git_native_recovery_PASS last_confirmed=3", flush=True)
        return 0
    except RuntimeError as exc:
        print(f"STOP reason={exc} last_completed=0 next_safe_action=inspect_bounded_local_evidence retry_safe=true", file=sys.stderr)
        return 78


if __name__ == "__main__":
    raise SystemExit(main())
