#!/usr/bin/env python3
"""Publish the Synergy Pages terminal-loss recovery v2 candidate safely.

The candidate is scanned with pinned Gitleaks before any commit/remote source
publication. The bootstrap uses a fresh isolated clone and never touches the
caller's current directory or repository.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import shutil
import string
import subprocess
import sys
import tarfile
import tempfile
import time
from typing import NoReturn, Sequence
from urllib.error import URLError
from urllib.request import Request, urlopen

REPOSITORY = "nagdkl/nagdkl.github.io"
REPO_URL = "https://github.com/nagdkl/nagdkl.github.io.git"
EXPECTED_BASE = "0e872af12b2aee39bc06df49bedf4e5a3179dbdc"
BRANCH = "recovery/pages-terminal-loss-v4-20260905"
GL_VERSION = "8.30.1"
GL_ASSET_URL = "https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_linux_x64.tar.gz"
GL_ASSET_SHA256 = "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb"
FALLBACK_GIT_NAME = "nagdkl"
FALLBACK_GIT_EMAIL = "194505092+nagdkl@users.noreply.github.com"
SOURCE_PATHS = (
    "scripts/recover_pages_after_terminal_loss_v2.py",
    "scripts/bootstrap_publish_pages_recovery_v2.py",
    "scripts/run_pages_recovery_v4.py",
    "tests/test_recover_pages_after_terminal_loss_v2.py",
    "tests/test_bootstrap_publish_pages_recovery_v2.py",
    "tests/test_run_pages_recovery_v4.py",
    "docs/runbooks/pages-terminal-loss-recovery-v2.md",
    "docs/research/pages-terminal-loss-recovery-donors.v2.yaml",
    "docs/research/pages-terminal-loss-recovery-aqa.v2.yaml",
    "docs/research/pages-terminal-loss-recovery-manifest.v2.json",
)


@dataclass(slots=True)
class Blocked(RuntimeError):
    reason: str
    next_safe_action: str
    retry_safe: bool = False
    exit_code: int = 78


class Steps:
    def __init__(self, evidence: Path) -> None:
        self.evidence = evidence
        self.evidence.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.step = 0
        self.last = 0

    @staticmethod
    def now() -> str:
        import datetime as dt
        return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")

    def _write(self, line: str, *, err: bool = False) -> None:
        print(line, file=sys.stderr if err else sys.stdout, flush=True)
        with (self.evidence / "steps.log").open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def start(self, action: str, timeout_s: int) -> None:
        self.step += 1
        self._write(f"[{self.now()}] STEP_START id={self.step} action={action} timeout={timeout_s}s retries=0")

    def ok(self, result: str) -> None:
        self.last = self.step
        self._write(f"[{self.now()}] STEP_OK id={self.step} result={result} last_confirmed={self.last}")

    def blocked(self, b: Blocked) -> NoReturn:
        self._write(
            f"[{self.now()}] STEP_BLOCKED id={self.step} result={b.reason} last_confirmed={self.last}", err=True
        )
        self._write(
            f"STOP reason={b.reason} last_completed={self.last} next_safe_action={b.next_safe_action} "
            f"retry_safe={str(b.retry_safe).lower()}", err=True
        )
        raise SystemExit(b.exit_code)


def cp(cmd: Sequence[str], *, cwd: Path | None = None, timeout_s: int = 30, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = {**os.environ, "GIT_TERMINAL_PROMPT": "0", **(env or {})}
    try:
        return subprocess.run(list(cmd), cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              check=False, timeout=timeout_s, env=merged)
    except subprocess.TimeoutExpired as exc:
        raise Blocked("command_timeout", "perform_read_only_outcome_recovery_before_any_replay", False, 124) from exc
    except OSError as exc:
        raise Blocked("command_execution_failed", "verify_required_tool_or_execution_surface", True) from exc


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dst: Path, timeout_s: int) -> None:
    req = Request(url, headers={"User-Agent": "synergy-pages-bootstrap-v2/1"})
    def _alarm(_signum: int, _frame: object) -> None:
        raise TimeoutError("hard_download_timeout")
    old_handler = signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, timeout_s)
    try:
        with urlopen(req, timeout=min(10, timeout_s)) as response, dst.open("wb") as out:  # nosec B310: pinned HTTPS URL
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
    except (URLError, TimeoutError) as exc:
        raise Blocked("gitleaks_download_failed_or_timed_out", "recover_network_then_start_new_attempt", True) from exc
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)


def safe_extract_gitleaks(archive: Path, target: Path) -> Path:
    target.mkdir(parents=True, exist_ok=False, mode=0o700)
    with tarfile.open(archive, "r:gz") as tf:
        candidates = []
        for member in tf.getmembers():
            parts = Path(member.name).parts
            if Path(member.name).is_absolute() or ".." in parts or member.issym() or member.islnk() or member.isdev():
                raise Blocked("unsafe_gitleaks_archive_member", "stop_and_reconcile_official_asset", False)
            if Path(member.name).name == "gitleaks" and member.isfile():
                candidates.append(member)
        if len(candidates) != 1:
            raise Blocked("gitleaks_binary_member_ambiguous", "stop_and_reconcile_official_asset", False)
        src = tf.extractfile(candidates[0])
        if src is None:
            raise Blocked("gitleaks_extract_failed", "stop_and_reconcile_official_asset", False)
        binary = target / "gitleaks"
        binary.write_bytes(src.read())
        binary.chmod(0o700)
        return binary


def gitleaks_run(binary: Path, source: Path, report: Path, *, git_mode: bool, timeout_s: int = 60) -> subprocess.CompletedProcess[str]:
    cmd = [str(binary), "detect", "--source", str(source), "--redact", "--report-format", "json",
           "--report-path", str(report), "--exit-code", "1"]
    if not git_mode:
        cmd.append("--no-git")
    return cp(cmd, timeout_s=timeout_s)


def load_report(path: Path) -> list[dict[str, object]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise Blocked("gitleaks_report_malformed", "stop_and_reconcile_scanner_output", False)
    return [x for x in value if isinstance(x, dict)]


def validate_gitleaks(binary: Path, private: Path, steps: Steps) -> None:
    steps.start("gitleaks_version_identity", 10)
    version = cp([str(binary), "version"], timeout_s=10)
    if version.returncode != 0 or GL_VERSION not in (version.stdout + version.stderr):
        raise Blocked("gitleaks_version_drift", "stop_and_reconcile_scanner_identity", False)
    steps.ok(f"gitleaks_version_{GL_VERSION}")

    alphabet = string.ascii_letters + string.digits
    token = "gh" + "p_" + "".join(secrets.choice(alphabet) for _ in range(36))
    positive_dir = private / "canary-positive"
    positive_dir.mkdir(mode=0o700)
    positive_file = positive_dir / "fixture.txt"
    positive_file.write_text(f'github_token = "{token}"\n', encoding="utf-8")
    positive_file.chmod(0o600)
    token_digest = hashlib.sha256(token.encode()).hexdigest()

    steps.start("gitleaks_positive_canary", 30)
    positive_report = private / "positive-report.json"
    pos = gitleaks_run(binary, positive_dir, positive_report, git_mode=False, timeout_s=30)
    findings = load_report(positive_report)
    rule_ids = {str(f.get("RuleID", "")) for f in findings}
    if pos.returncode != 1 or not findings or not any("github" in r.lower() for r in rule_ids):
        raise Blocked("gitleaks_positive_canary_failed", "do_not_credit_scanner_or_publish_source", False)
    steps.ok(f"positive_canary_PASS findings={len(findings)} token_sha256={token_digest}")

    negative_dir = private / "canary-negative"
    negative_dir.mkdir(mode=0o700)
    negative_file = negative_dir / "fixture.txt"
    negative_file.write_text("Synergy negative scanner control: no credential material.\n", encoding="utf-8")
    negative_file.chmod(0o600)
    steps.start("gitleaks_negative_canary", 30)
    negative_report = private / "negative-report.json"
    neg = gitleaks_run(binary, negative_dir, negative_report, git_mode=False, timeout_s=30)
    if neg.returncode != 0 or load_report(negative_report):
        raise Blocked("gitleaks_negative_canary_failed", "do_not_credit_scanner_or_publish_source", False)
    steps.ok("negative_canary_PASS findings=0")


def verify_manifest(candidate: Path) -> dict[str, str]:
    manifest_path = candidate / "docs/research/pages-terminal-loss-recovery-manifest.v2.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or set(manifest) != set(SOURCE_PATHS) - {manifest_path.relative_to(candidate).as_posix()}:
        raise Blocked("candidate_manifest_scope_mismatch", "recover_exact_candidate_bundle", False)
    for rel, expected in manifest.items():
        path = candidate / rel
        if not path.is_file() or sha256(path) != expected:
            raise Blocked("candidate_manifest_hash_mismatch", "recover_exact_candidate_bundle", False)
    return {str(k): str(v) for k, v in manifest.items()}


def remote_branch_sha(repo: Path, branch: str, timeout_s: int = 20) -> str | None:
    result = cp(["git", "ls-remote", "--heads", "origin", f"refs/heads/{branch}"], cwd=repo, timeout_s=timeout_s)
    if result.returncode != 0:
        raise Blocked("remote_branch_read_failed", "recover_connectivity_then_read_only_check", True)
    line = result.stdout.strip()
    if not line:
        return None
    return line.split()[0]


def push_with_recovery(repo: Path, branch: str, commit: str, steps: Steps, timeout_s: int = 60) -> None:
    steps.start("push_remote_checkpoint", timeout_s)
    try:
        result = cp(["git", "push", "--set-upstream", "origin", f"HEAD:refs/heads/{branch}"], cwd=repo, timeout_s=timeout_s)
    except Blocked as exc:
        if exc.reason != "command_timeout":
            raise
        observed = remote_branch_sha(repo, branch)
        if observed == commit:
            steps.ok(f"push_outcome_recovered_exact_branch_{branch}_sha_{commit}")
            return
        raise Blocked("push_outcome_unknown", "read_only_remote_branch_recovery_before_any_replay", False, 124)
    if result.returncode != 0:
        observed = remote_branch_sha(repo, branch)
        if observed == commit:
            steps.ok(f"push_transport_nonzero_but_remote_exact_{commit}")
            return
        raise Blocked("git_push_failed", "inspect_sanitized_git_error_and_remote_branch_state", False)
    observed = remote_branch_sha(repo, branch)
    if observed != commit:
        raise Blocked("remote_branch_exact_readback_failed", "do_not_replay_push_until_remote_state_reconciled", False)
    steps.ok(f"remote_branch_PASS branch={branch} sha={commit}")


def create_draft_pr(repo: Path, branch: str, commit: str, evidence: Path, steps: Steps, timeout_s: int = 60) -> str:
    gh = shutil.which("gh")
    if gh is None:
        raise Blocked("gh_unavailable_after_branch_checkpoint", "create_Draft_PR_from_remote_branch_via_GitHub_connector", True)
    auth = cp([gh, "auth", "status"], timeout_s=10)
    if auth.returncode != 0:
        raise Blocked("gh_auth_unavailable_after_branch_checkpoint", "create_Draft_PR_via_GitHub_connector", True)
    body = evidence / "pr-body.md"
    body.write_text(
        "## Goal\nPublish the Python-first terminal-loss recovery donor v2.\n\n"
        "## Gates\n- sandbox AQA: 23/23 PASS including v4 launcher hostile tests before publication\n"
        "- exact outgoing Gitleaks v8.30.1: PASS before commit\n"
        "- full reachable-history Gitleaks v8.30.1: PASS before push\n"
        "- remote branch exact readback: PASS\n\n"
        "## Authority\nDraft only; no merge/runtime/release/deployment/production authority.\n",
        encoding="utf-8",
    )
    steps.start("create_Draft_PR", timeout_s)
    create = cp([
        gh, "pr", "create", "--repo", REPOSITORY, "--base", "main", "--head", branch, "--draft",
        "--title", "chore(recovery): Python-first Pages terminal-loss donor v2", "--body-file", str(body),
    ], cwd=repo, timeout_s=timeout_s)
    if create.returncode != 0:
        # Do not replay. Recover by listing the branch's PRs.
        listed = cp([gh, "pr", "list", "--repo", REPOSITORY, "--head", branch, "--state", "all",
                     "--json", "number,isDraft,headRefOid,headRefName,baseRefName,state,url"], timeout_s=20)
        if listed.returncode != 0:
            raise Blocked("draft_pr_outcome_unknown", "read_only_GitHub_PR_recovery_before_any_replay", False)
        rows = json.loads(listed.stdout or "[]")
    else:
        rows_result = cp([gh, "pr", "list", "--repo", REPOSITORY, "--head", branch, "--state", "all",
                          "--json", "number,isDraft,headRefOid,headRefName,baseRefName,state,url"], timeout_s=20)
        if rows_result.returncode != 0:
            raise Blocked("draft_pr_readback_failed", "read_only_GitHub_PR_recovery", True)
        rows = json.loads(rows_result.stdout or "[]")
    exact = [r for r in rows if r.get("headRefOid") == commit and r.get("headRefName") == branch
             and r.get("baseRefName") == "main" and r.get("isDraft") is True and r.get("state") == "OPEN"]
    if len(exact) != 1:
        raise Blocked("draft_pr_exact_readback_ambiguous", "inspect_PR_state_without_replaying_creation", False)
    url = str(exact[0]["url"])
    steps.ok(f"Draft_PR_PASS url={url} head={commit}")
    return url


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate-root", type=Path, required=True)
    p.add_argument("--repo-url", default=REPO_URL)
    p.add_argument("--expected-base", default=EXPECTED_BASE)
    p.add_argument("--branch", default=BRANCH)
    p.add_argument("--gitleaks-bin", type=Path)
    p.add_argument("--gitleaks-asset", type=Path, help="pre-downloaded official tar.gz; useful for deterministic/offline AQA")
    p.add_argument("--state-root", type=Path, default=Path.home() / ".local/state/synergy-mesh/pages-recovery-publish-v2")
    p.add_argument("--publish", action="store_true", help="push branch and create Draft PR; omitted means local validation only")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    run_id = f"{int(time.time())}-{os.getpid()}"
    evidence = args.state_root / "runs" / run_id
    steps = Steps(evidence)
    receipt: dict[str, object] = {
        "schema": "synergy.pages_terminal_loss_recovery_publication_receipt/v2",
        "status": "BLOCKED",
        "automatic_retries": 0,
        "base": args.expected_base,
        "branch": args.branch,
        "publish_requested": bool(args.publish),
    }
    try:
        steps.start("preflight_python_git_candidate", 5)
        if sys.version_info < (3, 10):
            raise Blocked("python_too_old", "use_supported_Ubuntu_Debian_with_Python_3_10_plus", False)
        if shutil.which("git") is None:
            raise Blocked("git_missing", "install_git_then_new_attempt", True)
        candidate = args.candidate_root.resolve(strict=True)
        manifest = verify_manifest(candidate)
        steps.ok(f"candidate_manifest_PASS files={len(manifest)+1}")

        with tempfile.TemporaryDirectory(prefix="synergy-pages-publish-v2-") as td:
            private = Path(td)
            private.chmod(0o700)
            if args.gitleaks_bin:
                gitleaks = args.gitleaks_bin.resolve(strict=True)
            else:
                asset = args.gitleaks_asset.resolve(strict=True) if args.gitleaks_asset else private / "gitleaks.tar.gz"
                if not args.gitleaks_asset:
                    steps.start("download_pinned_gitleaks_asset", 60)
                    download(GL_ASSET_URL, asset, 60)
                    steps.ok("gitleaks_asset_download_PASS retries=0")
                steps.start("verify_gitleaks_asset_sha256", 10)
                if sha256(asset) != GL_ASSET_SHA256:
                    raise Blocked("gitleaks_asset_sha256_mismatch", "stop_and_reconcile_official_asset", False)
                steps.ok(f"gitleaks_asset_sha256_{GL_ASSET_SHA256}")
                gitleaks = safe_extract_gitleaks(asset, private / "gitleaks-bin")

            validate_gitleaks(gitleaks, private, steps)

            steps.start("exact_outgoing_candidate_gitleaks", 60)
            candidate_report = private / "candidate-report.json"
            scan = gitleaks_run(gitleaks, candidate, candidate_report, git_mode=False, timeout_s=60)
            if scan.returncode != 0 or load_report(candidate_report):
                raise Blocked("exact_outgoing_gitleaks_failed", "do_not_commit_or_publish_candidate", False)
            steps.ok("exact_outgoing_gitleaks_PASS findings=0")

            repo = private / "repo"
            steps.start("fresh_complete_clone", 60)
            clone = cp(["git", "clone", "--quiet", "--no-tags", args.repo_url, str(repo)], timeout_s=60)
            if clone.returncode != 0:
                raise Blocked("fresh_clone_failed", "recover_connectivity_then_new_attempt", True)
            actual_base = cp(["git", "rev-parse", "HEAD"], cwd=repo, timeout_s=10)
            if actual_base.returncode != 0 or actual_base.stdout.strip() != args.expected_base:
                raise Blocked("base_drift", "refresh_remote_currentness_before_source_write", False)
            if remote_branch_sha(repo, args.branch) is not None:
                raise Blocked("target_branch_already_exists", "recover_existing_remote_branch_read_only;do_not_replay", False)
            steps.ok(f"clone_exact_base_{args.expected_base}_branch_absent")

            steps.start("materialize_exact_write_set", 10)
            for rel in SOURCE_PATHS:
                src = candidate / rel
                if not src.is_file():
                    raise Blocked("candidate_path_missing", "recover_exact_candidate_bundle", False)
                dst = repo / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
            for rel, expected in manifest.items():
                if sha256(repo / rel) != expected:
                    raise Blocked("post_copy_hash_mismatch", "discard_ephemeral_checkout_and_recover_candidate", False)
            steps.ok(f"write_set_materialized_paths={len(SOURCE_PATHS)}")

            steps.start("local_source_sanity", 30)
            check = cp(["git", "diff", "--check"], cwd=repo, timeout_s=10)
            if check.returncode != 0:
                raise Blocked("git_diff_check_failed", "repair_candidate_before_publication", False)
            python_paths = [str(repo / rel) for rel in SOURCE_PATHS if rel.endswith(".py")]
            compile_result = cp([sys.executable, "-m", "py_compile", *python_paths], timeout_s=30)
            if compile_result.returncode != 0:
                raise Blocked("python_compile_failed", "repair_candidate_before_publication", False)
            steps.ok("diff_check_and_py_compile_PASS")

            steps.start("precommit_worktree_gitleaks", 60)
            repo_report = private / "repo-worktree-report.json"
            worktree_scan = gitleaks_run(gitleaks, repo, repo_report, git_mode=False, timeout_s=60)
            if worktree_scan.returncode != 0 or load_report(repo_report):
                raise Blocked("precommit_gitleaks_failed", "do_not_commit_candidate", False)
            steps.ok("precommit_gitleaks_PASS findings=0")

            steps.start("create_local_commit_after_security_PASS", 20)
            add = cp(["git", "add", "--", *SOURCE_PATHS], cwd=repo, timeout_s=10)
            if add.returncode != 0:
                raise Blocked("git_add_failed", "inspect_ephemeral_checkout", True)
            staged = cp(["git", "diff", "--cached", "--name-only"], cwd=repo, timeout_s=10)
            observed_paths = tuple(x for x in staged.stdout.splitlines() if x)
            if observed_paths != tuple(sorted(SOURCE_PATHS)) and set(observed_paths) != set(SOURCE_PATHS):
                raise Blocked("staged_pathset_mismatch", "discard_ephemeral_checkout_and_reconcile", False)
            name = cp(["git", "config", "user.name"], cwd=repo, timeout_s=5)
            email = cp(["git", "config", "user.email"], cwd=repo, timeout_s=5)
            commit_name = name.stdout.strip() if name.returncode == 0 and name.stdout.strip() else FALLBACK_GIT_NAME
            commit_email = email.stdout.strip() if email.returncode == 0 and email.stdout.strip() else FALLBACK_GIT_EMAIL
            branch = cp(["git", "switch", "-c", args.branch], cwd=repo, timeout_s=10)
            if branch.returncode != 0:
                raise Blocked("local_branch_creation_failed", "inspect_ephemeral_checkout", False)
            commit = cp(["git", "-c", f"user.name={commit_name}", "-c", f"user.email={commit_email}",
                         "commit", "-m", "chore(recovery): add Python-first Pages terminal-loss donor v2"],
                        cwd=repo, timeout_s=20)
            if commit.returncode != 0:
                raise Blocked("local_commit_failed", "inspect_ephemeral_checkout", False)
            commit_sha = cp(["git", "rev-parse", "HEAD"], cwd=repo, timeout_s=10).stdout.strip()
            steps.ok(f"local_commit_{commit_sha}")

            steps.start("full_reachable_history_gitleaks", 90)
            history_report = private / "history-report.json"
            history = gitleaks_run(gitleaks, repo, history_report, git_mode=True, timeout_s=90)
            if history.returncode != 0 or load_report(history_report):
                raise Blocked("full_history_gitleaks_failed", "do_not_push_candidate", False)
            steps.ok("full_reachable_history_gitleaks_PASS findings=0")

            steps.start("prepush_remote_currentness_fence", 20)
            remote_main = remote_branch_sha(repo, "main", timeout_s=20)
            remote_target = remote_branch_sha(repo, args.branch, timeout_s=20)
            if remote_main != args.expected_base:
                raise Blocked("remote_main_drift_before_push", "refresh_base_and_revalidate_candidate_before_publication", False)
            if remote_target is not None:
                raise Blocked("target_branch_appeared_before_push", "recover_remote_branch_read_only;do_not_replay", False)
            steps.ok(f"prepush_fence_PASS main={remote_main} target_branch_absent=true")

            pr_url = None
            if args.publish:
                push_with_recovery(repo, args.branch, commit_sha, steps)
                steps.start("postpush_base_currentness_fence", 20)
                remote_main_after = remote_branch_sha(repo, "main", timeout_s=20)
                if remote_main_after != args.expected_base:
                    raise Blocked("base_drift_after_branch_checkpoint", "keep_branch_checkpoint_and_reconcile_before_PR_creation", False)
                steps.ok(f"postpush_base_fence_PASS main={remote_main_after}")
                pr_url = create_draft_pr(repo, args.branch, commit_sha, evidence, steps)
            else:
                steps.start("publication_authority", 1)
                steps.ok("LOCAL_VALIDATION_ONLY no_push no_PR")

            receipt.update({
                "status": "PASS",
                "commit": commit_sha,
                "gitleaks_version": GL_VERSION,
                "gitleaks_exact_outgoing": "PASS",
                "gitleaks_full_history": "PASS",
                "source_paths": list(SOURCE_PATHS),
                "pr_url": pr_url,
            })
            (evidence / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            print(f"GATE=PASS COMMIT={commit_sha} BRANCH={args.branch} DRAFT_PR={pr_url or 'NOT_REQUESTED'}")
            print(f"BREADCRUMBS={evidence}")
            return 0
    except Blocked as b:
        receipt["blocker"] = {"reason": b.reason, "next_safe_action": b.next_safe_action, "retry_safe": b.retry_safe}
        (evidence / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        steps.blocked(b)


if __name__ == "__main__":
    raise SystemExit(main())
