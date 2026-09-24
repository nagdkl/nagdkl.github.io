#!/usr/bin/env python3
"""Synergy terminal-loss-safe GitHub Pages recovery verifier v2.

Read-only by design. Verifies immutable Git identities and live HTTP rendering.
Uses only Python standard library plus the git executable.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import NoReturn, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_URL = "https://github.com/nagdkl/nagdkl.github.io.git"
LIVE_URL = "https://nagdkl.github.io/"
EXPECTED_MAIN_SHA = "0e872af12b2aee39bc06df49bedf4e5a3179dbdc"
EXPECTED_INDEX_BLOB = "2606d236549a1a43e9e5ba3684b888d784f18fe0"
EXPECTED_LAYOUT_BLOB = "0b4de0aa8242c2d533d86ba50d59b7a63dd8a097"
EXPECTED_MARKER = "День открытых дверей"
SCHEMA = "synergy.pages_terminal_loss_recovery_receipt/v2"


class Blocked(RuntimeError):
    def __init__(self, reason: str, next_safe_action: str, retry_safe: bool = False) -> None:
        super().__init__(reason)
        self.reason = reason
        self.next_safe_action = next_safe_action
        self.retry_safe = retry_safe


@dataclasses.dataclass(slots=True)
class StepLogger:
    evidence_dir: Path
    step_id: int = 0
    last_confirmed: int = 0

    @staticmethod
    def now() -> str:
        import datetime as dt
        return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")

    def start(self, action: str, timeout_s: int) -> None:
        self.step_id += 1
        msg = f"[{self.now()}] STEP_START id={self.step_id} action={action} timeout={timeout_s}s"
        print(msg, flush=True)
        self._append(msg)

    def ok(self, result: str) -> None:
        self.last_confirmed = self.step_id
        msg = f"[{self.now()}] STEP_OK id={self.step_id} result={result} last_confirmed={self.last_confirmed}"
        print(msg, flush=True)
        self._append(msg)

    def blocked(self, result: str, *, reason: str, next_safe_action: str, retry_safe: bool) -> NoReturn:
        msg = f"[{self.now()}] STEP_BLOCKED id={self.step_id} result={result} last_confirmed={self.last_confirmed}"
        print(msg, file=sys.stderr, flush=True)
        self._append(msg)
        stop = (
            f"STOP reason={reason} last_completed={self.last_confirmed} "
            f"next_safe_action={next_safe_action} retry_safe={str(retry_safe).lower()}"
        )
        print(stop, file=sys.stderr, flush=True)
        self._append(stop)
        raise SystemExit(78)

    def fail(self, result: str, *, reason: str, next_safe_action: str, retry_safe: bool, rc: int = 1) -> NoReturn:
        msg = f"[{self.now()}] STEP_FAIL id={self.step_id} result={result} last_confirmed={self.last_confirmed}"
        print(msg, file=sys.stderr, flush=True)
        self._append(msg)
        stop = (
            f"STOP reason={reason} last_completed={self.last_confirmed} "
            f"next_safe_action={next_safe_action} retry_safe={str(retry_safe).lower()}"
        )
        print(stop, file=sys.stderr, flush=True)
        self._append(stop)
        raise SystemExit(rc)

    def _append(self, text: str) -> None:
        self.evidence_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (self.evidence_dir / "steps.log").open("a", encoding="utf-8") as fh:
            fh.write(text + "\n")


def run(cmd: Sequence[str], *, cwd: Path | None = None, timeout_s: int = 30) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(cmd), cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False, timeout=timeout_s, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except subprocess.TimeoutExpired as exc:
        raise Blocked("command_timeout", "start_new_bounded_read_only_attempt", True) from exc
    except OSError as exc:
        raise Blocked("command_execution_failed", "verify_required_tool_and_execution_surface", True) from exc


def git_stdout(repo: Path, *args: str, timeout_s: int = 10) -> str:
    cp = run(["git", *args], cwd=repo, timeout_s=timeout_s)
    if cp.returncode != 0:
        raise Blocked("git_read_failed", "inspect_sanitized_evidence", True)
    return cp.stdout.strip()


def http_probe(url: str, marker: str, timeout_s: int) -> dict[str, object]:
    req = Request(url, headers={"User-Agent": "synergy-pages-recovery-v2/1"})
    try:
        with urlopen(req, timeout=timeout_s) as response:  # nosec B310: fixed HTTPS URL by default
            status = int(getattr(response, "status", 0))
            body = response.read(2_000_000)
    except HTTPError as exc:
        raise Blocked(f"http_status_{exc.code}", "inspect_pages_configuration", True) from exc
    except URLError as exc:
        raise Blocked("live_http_transport_failed", "rerun_read_only_http_probe_after_connectivity_recovery", True) from exc
    if status != 200:
        raise Blocked(f"http_status_{status}", "inspect_pages_configuration", True)
    text = body.decode("utf-8", errors="replace")
    if marker not in text:
        raise Blocked("live_http_marker_missing", "inspect_rendered_page", True)
    return {"status": status, "bytes": len(body), "marker_present": True}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-url", default=os.environ.get("REPO_URL", REPO_URL))
    p.add_argument("--live-url", default=os.environ.get("LIVE_URL", LIVE_URL))
    p.add_argument("--expected-main", default=os.environ.get("EXPECTED_MAIN_SHA", EXPECTED_MAIN_SHA))
    p.add_argument("--expected-index-blob", default=os.environ.get("EXPECTED_INDEX_BLOB", EXPECTED_INDEX_BLOB))
    p.add_argument("--expected-layout-blob", default=os.environ.get("EXPECTED_LAYOUT_BLOB", EXPECTED_LAYOUT_BLOB))
    p.add_argument("--expected-marker", default=os.environ.get("EXPECTED_MARKER", EXPECTED_MARKER))
    p.add_argument("--clone-timeout", type=int, default=60)
    p.add_argument("--http-timeout", type=int, default=20)
    p.add_argument("--state-root", type=Path, default=Path.home() / ".local/state/synergy-mesh/pages-recovery-v2")
    p.add_argument("--keep-workdir", action="store_true")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if shutil.which("git") is None:
        print("STEP_BLOCKED reason=missing_git", file=sys.stderr)
        return 78
    for name, value in {
        "expected_main": args.expected_main,
        "expected_index_blob": args.expected_index_blob,
        "expected_layout_blob": args.expected_layout_blob,
    }.items():
        if len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
            print(f"STEP_BLOCKED reason=invalid_{name}", file=sys.stderr)
            return 78

    run_id = f"{int(time.time())}-{os.getpid()}"
    evidence_dir = args.state_root / "runs" / run_id
    evidence_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    log = StepLogger(evidence_dir)
    print(f"RESUME last_confirmed=remote interrupted=terminal_closed state=local_workspace_disposable evidence_dir={evidence_dir}")

    tmp_ctx = tempfile.TemporaryDirectory(prefix="synergy-pages-recovery-v2-")
    tmp = Path(tmp_ctx.name)
    repo = tmp / "repo"
    receipt: dict[str, object] = {
        "schema": SCHEMA,
        "status": "BLOCKED",
        "identity": {},
        "http": {},
        "automatic_retries": 0,
        "mutation_replay": False,
        "git_push": False,
        "git_merge": False,
    }
    try:
        log.start("fresh_clone_read_only", args.clone_timeout)
        cp = run(["git", "clone", "--quiet", "--no-tags", args.repo_url, str(repo)], timeout_s=args.clone_timeout)
        if cp.returncode != 0:
            raise Blocked("git_clone_failed", "recover_connectivity_then_new_read_only_attempt", True)
        log.ok("repository_cloned")

        log.start("verify_exact_remote_main", 10)
        actual_main = git_stdout(repo, "rev-parse", "HEAD")
        if actual_main != args.expected_main:
            raise Blocked("canonical_main_drift", "refresh_remote_evidence", False)
        log.ok(f"main_{actual_main}")

        log.start("verify_published_blob_identities", 10)
        index_blob = git_stdout(repo, "rev-parse", "HEAD:index.md")
        layout_blob = git_stdout(repo, "rev-parse", "HEAD:_layouts/default.html")
        if index_blob != args.expected_index_blob or layout_blob != args.expected_layout_blob:
            raise Blocked("published_blob_drift", "inspect_remote_commit_and_refresh_tuple", False)
        log.ok(f"index_{index_blob}_layout_{layout_blob}")

        log.start("verify_source_marker", 5)
        index_text = (repo / "index.md").read_text(encoding="utf-8")
        if args.expected_marker not in index_text:
            raise Blocked("source_marker_missing", "inspect_remote_blob", False)
        log.ok("source_marker_present")

        log.start("verify_worktree_clean", 5)
        status = git_stdout(repo, "status", "--porcelain")
        if status:
            raise Blocked("read_only_clone_not_clean", "inspect_checkout", False)
        log.ok("fresh_clone_clean")

        log.start("live_http_probe", args.http_timeout)
        http = http_probe(args.live_url, args.expected_marker, args.http_timeout)
        log.ok(f"LIVE_HTTP_PASS_status_{http['status']}_marker_present")

        receipt.update({
            "status": "PASS",
            "identity": {
                "main_sha": actual_main,
                "index_blob": index_blob,
                "layout_blob": layout_blob,
                "repo_url": args.repo_url,
            },
            "http": {**http, "url": args.live_url},
        })
        (evidence_dir / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(
            f"LIVE_HTTP=PASS HEAD={actual_main} INDEX_BLOB={index_blob} "
            f"LAYOUT_BLOB={layout_blob} URL={args.live_url}"
        )
        print(f"RECEIPT={evidence_dir / 'receipt.json'}")
        return 0
    except Blocked as exc:
        receipt.update({
            "status": "BLOCKED",
            "blocker": {
                "reason": exc.reason,
                "next_safe_action": exc.next_safe_action,
                "retry_safe": exc.retry_safe,
                "step_id": log.step_id,
                "last_confirmed": log.last_confirmed,
            },
        })
        (evidence_dir / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        log.blocked(
            exc.reason, reason=exc.reason, next_safe_action=exc.next_safe_action, retry_safe=exc.retry_safe
        )
    finally:
        if args.keep_workdir:
            kept = args.state_root / "workdirs" / run_id
            kept.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.copytree(tmp, kept)
            print(f"WORKDIR_PRESERVED={kept}")
        tmp_ctx.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
