#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import secrets
import signal
import shutil
import stat
import string
import subprocess
import sys
import tarfile
import tempfile
import time
from typing import NoReturn, Sequence
from urllib.error import URLError
from urllib.request import Request, urlopen
import zipfile

REPOSITORY = "nagdkl/nagdkl.github.io"
REPO_URL = "https://github.com/nagdkl/nagdkl.github.io.git"
EXPECTED_BASE = "0e872af12b2aee39bc06df49bedf4e5a3179dbdc"
BRANCH = "prompt/pr5-evidence-currentness-v1-20260905"
MIRROR_REL = Path("synergy/git-mirrors/nagdkl.github.io.git")
GL_VERSION = "8.30.1"
GL_ASSET_URL = "https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_linux_x64.tar.gz"
GL_ASSET_SHA256 = "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb"
FALLBACK_GIT_NAME = "nagdkl"
FALLBACK_GIT_EMAIL = "194505092+nagdkl@users.noreply.github.com"
SOURCE_PATHS = (
    "docs/prompts/pr5-evidence-currentness-continuation.v1.yaml",
    "docs/research/2026-09-05_pr5-prompt-engineering-evolution.v1.yaml",
    "scripts/validation/validate_pr5_evidence_currentness_prompt_v1.py",
    "tests/validation/test_pr5_evidence_currentness_prompt_v1.py",
    "scripts/human_node/publish_pr5_prompt_governance_v1.py",
    "tests/validation/test_publish_pr5_prompt_governance_v1.py",
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
        self._write(f"[{self.now()}] STEP_BLOCKED id={self.step} result={b.reason} last_confirmed={self.last}", err=True)
        self._write(f"STOP reason={b.reason} last_completed={self.last} next_safe_action={b.next_safe_action} retry_safe={str(b.retry_safe).lower()}", err=True)
        raise SystemExit(b.exit_code)

def cp(cmd: Sequence[str], *, cwd: Path | None = None, timeout_s: int = 30, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = {**os.environ, "GIT_TERMINAL_PROMPT": "0", **(env or {})}
    try:
        return subprocess.run(list(cmd), cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=timeout_s, env=merged)
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

def safe_extract_bundle(bundle: Path, target: Path, expected_sha: str) -> Path:
    if sha256(bundle) != expected_sha:
        raise Blocked("bundle_sha256_mismatch", "recover_exact_prompt_governance_bundle", False)
    target.mkdir(parents=True, exist_ok=False, mode=0o700)
    with zipfile.ZipFile(bundle) as zf:
        names = set()
        for info in zf.infolist():
            p = PurePosixPath(info.filename)
            mode = (info.external_attr >> 16) & 0o170000
            if p.is_absolute() or ".." in p.parts or mode == stat.S_IFLNK:
                raise Blocked("unsafe_bundle_member", "recover_exact_prompt_governance_bundle", False)
            if info.is_dir():
                continue
            names.add(info.filename)
            dst = target.joinpath(*p.parts)
            dst.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, dst.open("wb") as out:
                shutil.copyfileobj(src, out)
            dst.chmod(0o600)
    expected_names = set(SOURCE_PATHS) | {"bundle-manifest.json"}
    if names != expected_names:
        raise Blocked("bundle_pathset_mismatch", "recover_exact_prompt_governance_bundle", False)
    manifest = json.loads((target / "bundle-manifest.json").read_text(encoding="utf-8"))
    if manifest.get("write_set") != list(SOURCE_PATHS):
        raise Blocked("bundle_manifest_write_set_mismatch", "recover_exact_prompt_governance_bundle", False)
    files = manifest.get("files")
    if not isinstance(files, dict) or set(files) != set(SOURCE_PATHS):
        raise Blocked("bundle_manifest_files_mismatch", "recover_exact_prompt_governance_bundle", False)
    for rel in SOURCE_PATHS:
        p = target / rel
        if not p.is_file() or sha256(p) != files[rel]:
            raise Blocked("bundle_file_hash_mismatch", "recover_exact_prompt_governance_bundle", False)
    return target

def download(url: str, dst: Path, timeout_s: int) -> None:
    req = Request(url, headers={"User-Agent": "synergy-pr5-prompt-governance-v1/1"})
    def _alarm(_signum: int, _frame: object) -> None:
        raise TimeoutError("hard_download_timeout")
    old = signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, timeout_s)
    try:
        with urlopen(req, timeout=min(10, timeout_s)) as response, dst.open("wb") as out:  # nosec B310 pinned HTTPS
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
    except (URLError, TimeoutError) as exc:
        raise Blocked("gitleaks_download_failed_or_timed_out", "recover_network_then_start_new_attempt", True) from exc
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)

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

def gitleaks_run(binary: Path, source: Path, report: Path, *, git_mode: bool, timeout_s: int) -> subprocess.CompletedProcess[str]:
    cmd = [str(binary), "detect", "--source", str(source), "--redact", "--report-format", "json", "--report-path", str(report), "--exit-code", "1"]
    if not git_mode:
        cmd.append("--no-git")
    return cp(cmd, timeout_s=timeout_s)

def load_report(path: Path) -> list[dict[str, object]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    v = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(v, list):
        raise Blocked("gitleaks_report_malformed", "stop_and_reconcile_scanner_output", False)
    return [x for x in v if isinstance(x, dict)]

def validate_gitleaks(binary: Path, private: Path, steps: Steps) -> None:
    steps.start("gitleaks_version_identity", 10)
    version = cp([str(binary), "version"], timeout_s=10)
    if version.returncode != 0 or GL_VERSION not in (version.stdout + version.stderr):
        raise Blocked("gitleaks_version_drift", "stop_and_reconcile_scanner_identity", False)
    steps.ok(f"gitleaks_version_{GL_VERSION}")
    alphabet = string.ascii_letters + string.digits
    token = "gh" + "p_" + "".join(secrets.choice(alphabet) for _ in range(36))
    posdir = private / "canary-positive"; posdir.mkdir(mode=0o700)
    (posdir / "fixture.txt").write_text(f'github_token = "{token}"\n', encoding="utf-8")
    steps.start("gitleaks_positive_canary", 30)
    preport = private / "positive-report.json"
    pos = gitleaks_run(binary, posdir, preport, git_mode=False, timeout_s=30)
    findings = load_report(preport)
    if pos.returncode != 1 or not findings:
        raise Blocked("gitleaks_positive_canary_failed", "do_not_credit_scanner_or_publish_source", False)
    steps.ok(f"positive_canary_PASS findings={len(findings)} token_sha256={hashlib.sha256(token.encode()).hexdigest()}")
    negdir = private / "canary-negative"; negdir.mkdir(mode=0o700)
    (negdir / "fixture.txt").write_text("Synergy negative scanner control: no credential material.\n", encoding="utf-8")
    steps.start("gitleaks_negative_canary", 30)
    nreport = private / "negative-report.json"
    neg = gitleaks_run(binary, negdir, nreport, git_mode=False, timeout_s=30)
    if neg.returncode != 0 or load_report(nreport):
        raise Blocked("gitleaks_negative_canary_failed", "do_not_credit_scanner_or_publish_source", False)
    steps.ok("negative_canary_PASS findings=0")



def acquire_mirror_lock(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = lock_path.open("a+")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        fh.close()
        raise Blocked("mirror_busy", "another_synergy_process_owns_mirror;inspect_then_retry_new_attempt", True) from exc
    return fh


def git_bare(mirror: Path, args: Sequence[str], *, timeout_s: int = 30) -> subprocess.CompletedProcess[str]:
    return cp(["git", f"--git-dir={mirror}", *args], timeout_s=timeout_s)


def validate_mirror(mirror: Path, repo_url: str) -> bool:
    if not mirror.is_dir():
        return False
    bare = git_bare(mirror, ["rev-parse", "--is-bare-repository"], timeout_s=5)
    if bare.returncode != 0 or bare.stdout.strip() != "true":
        return False
    origin = git_bare(mirror, ["remote", "get-url", "origin"], timeout_s=5)
    if origin.returncode != 0 or origin.stdout.strip() != repo_url:
        return False
    fsck = git_bare(mirror, ["fsck", "--connectivity-only", "--no-progress"], timeout_s=20)
    return fsck.returncode == 0


def initialize_mirror(repo_url: str, mirror: Path, private: Path, steps: Steps) -> Path:
    mirror.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if mirror.exists():
        if not validate_mirror(mirror, repo_url):
            fallback = private / "mirror.git"
            steps.start("canonical_mirror_invalid_fallback_clone", 60)
            clone = cp(["git", "clone", "--mirror", "--quiet", repo_url, str(fallback)], timeout_s=60)
            if clone.returncode != 0 or not validate_mirror(fallback, repo_url):
                raise Blocked("mirror_invalid_and_fallback_clone_failed", "preserve_invalid_mirror_and_recover_connectivity", False)
            steps.ok(f"fallback_mirror_PASS preserved_invalid={mirror}")
            return fallback
        steps.start("refresh_canonical_mirror", 45)
        fetch = git_bare(mirror, ["fetch", "--quiet", "--prune", "origin", "+refs/heads/main:refs/heads/main", f"+refs/heads/{BRANCH}:refs/heads/{BRANCH}"], timeout_s=45)
        if fetch.returncode != 0:
            raise Blocked("mirror_fetch_failed", "recover_connectivity_then_new_attempt", True)
        steps.ok("canonical_mirror_refresh_PASS")
        return mirror

    staged = private / "new-mirror.git"
    steps.start("initialize_canonical_mirror", 60)
    clone = cp(["git", "clone", "--mirror", "--quiet", repo_url, str(staged)], timeout_s=60)
    if clone.returncode != 0 or not validate_mirror(staged, repo_url):
        raise Blocked("mirror_initialization_failed", "recover_connectivity_then_new_attempt", True)
    try:
        os.replace(staged, mirror)
    except OSError:
        if mirror.exists() and validate_mirror(mirror, repo_url):
            shutil.rmtree(staged, ignore_errors=True)
        else:
            raise Blocked("mirror_atomic_install_failed", "inspect_cache_parent_without_deleting_unknown_state", False)
    steps.ok(f"canonical_mirror_initialized path={mirror}")
    return mirror


def mirror_ref(mirror: Path, ref: str) -> str | None:
    result = git_bare(mirror, ["rev-parse", "--verify", ref], timeout_s=10)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def add_detached_worktree(mirror: Path, worktree: Path, commit: str) -> None:
    result = git_bare(mirror, ["worktree", "add", "--detach", str(worktree), commit], timeout_s=30)
    if result.returncode != 0:
        raise Blocked("worktree_add_failed", "inspect_mirror_worktree_metadata", False)


def remove_worktree(mirror: Path, worktree: Path) -> None:
    if not worktree.exists():
        return
    result = git_bare(mirror, ["worktree", "remove", "--force", str(worktree)], timeout_s=20)
    if result.returncode != 0:
        raise Blocked("worktree_cleanup_failed", f"inspect_{worktree}_without_deleting_unknown_state", True)

def remote_branch_sha(repo: Path, branch: str, timeout_s: int = 20) -> str | None:
    result = cp(["git", "ls-remote", "--heads", "origin", f"refs/heads/{branch}"], cwd=repo, timeout_s=timeout_s)
    if result.returncode != 0:
        raise Blocked("remote_branch_read_failed", "recover_connectivity_then_read_only_check", True)
    line = result.stdout.strip()
    return None if not line else line.split()[0]

def remote_branch_sha_from_url(repo_url: str, branch: str, timeout_s: int = 20) -> str | None:
    result = cp(["git", "ls-remote", "--heads", repo_url, f"refs/heads/{branch}"], timeout_s=timeout_s)
    if result.returncode != 0:
        raise Blocked("remote_branch_read_failed", "recover_connectivity_then_read_only_check", True)
    line = result.stdout.strip()
    return line.split()[0] if line else None

def push_with_recovery(repo: Path, repo_url: str, branch: str, commit: str, expected_old: str, steps: Steps) -> None:
    steps.start("push_remote_checkpoint", 60)
    try:
        result = cp(["git", "push", repo_url, f"HEAD:refs/heads/{branch}"], cwd=repo, timeout_s=60)
    except Blocked as exc:
        if exc.reason != "command_timeout":
            raise
        observed = remote_branch_sha_from_url(repo_url, branch)
        if observed == commit:
            steps.ok(f"push_outcome_recovered_exact_branch_{branch}_sha_{commit}")
            return
        raise Blocked("push_outcome_unknown", "read_only_remote_branch_recovery_before_any_replay", False, 124)
    observed = remote_branch_sha_from_url(repo_url, branch)
    if result.returncode != 0 and observed != commit:
        raise Blocked("git_push_failed", "inspect_sanitized_git_error_and_remote_branch_state", False)
    if observed != commit:
        raise Blocked("remote_branch_exact_readback_failed", "do_not_replay_push_until_remote_state_reconciled", False)
    steps.ok(f"remote_branch_PASS previous={expected_old} branch={branch} sha={commit}")

def create_draft_pr(repo: Path, branch: str, commit: str, steps: Steps, gh_bin: str | None) -> str | None:
    gh = gh_bin or shutil.which("gh")
    if gh is None:
        steps.start("Draft_PR_deferred", 1)
        steps.ok("gh_unavailable branch_checkpoint_preserved")
        return None
    auth = cp([gh, "auth", "status"], timeout_s=10)
    if auth.returncode != 0:
        steps.start("Draft_PR_deferred", 1)
        steps.ok("gh_auth_unavailable branch_checkpoint_preserved")
        return None
    body = steps.evidence / "pr-body.md"
    body.write_text(
        "## Goal\nPersist the PR #5 evidence-currentness continuation prompt, research, validator, and hostile tests.\n\n"
        "## Gates\n- FULL_READ SSOT: PASS\n- sandbox validator/tests: PASS 7/7\n- exact outgoing Gitleaks v8.30.1: PASS before commit\n- full reachable-history Gitleaks: PASS before push\n- remote branch exact readback: PASS\n\n"
        "## Authority\nDraft only. This PR does not change PR #5 Ready/merge/runtime/release/deployment authority.\n",
        encoding="utf-8",
    )
    steps.start("create_Draft_PR", 60)
    create = cp([gh, "pr", "create", "--repo", REPOSITORY, "--base", "main", "--head", branch, "--draft", "--title", "docs(prompt): PR5 evidence-currentness continuation v1", "--body-file", str(body)], cwd=repo, timeout_s=60)
    listed = cp([gh, "pr", "list", "--repo", REPOSITORY, "--head", branch, "--state", "all", "--json", "number,isDraft,headRefOid,headRefName,baseRefName,state,url"], timeout_s=20)
    if listed.returncode != 0:
        raise Blocked("draft_pr_readback_failed", "read_only_GitHub_PR_recovery", True)
    rows = json.loads(listed.stdout or "[]")
    exact = [r for r in rows if r.get("headRefOid") == commit and r.get("headRefName") == branch and r.get("baseRefName") == "main" and r.get("isDraft") is True and r.get("state") == "OPEN"]
    if len(exact) != 1:
        if create.returncode != 0:
            raise Blocked("draft_pr_outcome_unknown", "read_only_GitHub_PR_recovery_before_any_replay", False)
        raise Blocked("draft_pr_exact_readback_ambiguous", "inspect_PR_state_without_replaying_creation", False)
    url = str(exact[0]["url"])
    steps.ok(f"Draft_PR_PASS url={url} head={commit}")
    return url

def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--bundle-sha256", required=True)
    p.add_argument("--repo-url", default=REPO_URL)
    p.add_argument("--expected-base", default=EXPECTED_BASE)
    p.add_argument("--branch", default=BRANCH)
    p.add_argument("--gitleaks-bin", type=Path)
    p.add_argument("--gitleaks-asset", type=Path)
    p.add_argument("--gh-bin")
    p.add_argument("--state-root", type=Path, default=Path.home() / ".local/state/synergy-mesh/pr5-prompt-governance-v1")
    p.add_argument("--publish", action="store_true")
    return p.parse_args(argv)

def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    evidence = args.state_root / "runs" / f"{int(time.time())}-{os.getpid()}"
    steps = Steps(evidence)
    receipt: dict[str, object] = {"schema":"synergy.pages.pr5_prompt_governance_publication_receipt/v1","status":"BLOCKED","automatic_retries":0,"base":args.expected_base,"branch":args.branch,"bundle_sha256":args.bundle_sha256}
    try:
        steps.start("preflight_and_bundle_identity", 10)
        if sys.version_info < (3, 10):
            raise Blocked("python_too_old", "use_Python_3_10_plus", False)
        if shutil.which("git") is None:
            raise Blocked("git_missing", "install_git_then_new_attempt", True)
        with tempfile.TemporaryDirectory(prefix="synergy-pr5-prompt-v1-") as td:
            private = Path(td); private.chmod(0o700)
            candidate = safe_extract_bundle(args.bundle.resolve(strict=True), private / "candidate", args.bundle_sha256)
            steps.ok(f"bundle_identity_PASS paths={len(SOURCE_PATHS)}")
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
            steps.start("exact_outgoing_bundle_gitleaks", 60)
            creport = private / "candidate-report.json"
            cscan = gitleaks_run(gitleaks, candidate, creport, git_mode=False, timeout_s=60)
            if cscan.returncode != 0 or load_report(creport):
                raise Blocked("exact_outgoing_gitleaks_failed", "do_not_commit_or_publish_candidate", False)
            steps.ok("exact_outgoing_gitleaks_PASS findings=0")
            cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
            mirror = cache_root / MIRROR_REL
            lock = acquire_mirror_lock(mirror.parent / "nagdkl.github.io.mirror.lock")
            repo = private / "worktree"
            mirror_used: Path | None = None
            mirror_used = initialize_mirror(args.repo_url, mirror, private, steps)
            steps.start("mirror_currentness_fence", 20)
            local_main = mirror_ref(mirror_used, "refs/heads/main")
            local_prompt = mirror_ref(mirror_used, f"refs/heads/{args.branch}")
            if local_main != args.expected_base:
                raise Blocked("base_drift", "refresh_remote_currentness_before_source_write", False)
            if local_prompt != args.expected_base:
                raise Blocked("reserved_branch_drift", "recover_reserved_prompt_branch_read_only", False)
            remote_prompt = remote_branch_sha_from_url(args.repo_url, args.branch)
            if remote_prompt != args.expected_base:
                raise Blocked("reserved_branch_remote_drift", "recover_reserved_prompt_branch_read_only", False)
            for rel in SOURCE_PATHS:
                exists = git_bare(mirror_used, ["cat-file", "-e", f"{args.expected_base}:{rel}"], timeout_s=5)
                if exists.returncode == 0:
                    raise Blocked("candidate_path_already_exists", "inspect_existing_prompt_lane_before_replay", False)
            steps.ok(f"mirror_currentness_PASS main={local_main} reserved_branch={local_prompt}")

            steps.start("create_ephemeral_detached_worktree", 30)
            add_detached_worktree(mirror_used, repo, args.expected_base)
            head = cp(["git", "rev-parse", "HEAD"], cwd=repo, timeout_s=10).stdout.strip()
            if head != args.expected_base:
                raise Blocked("worktree_base_drift", "remove_ephemeral_worktree_and_reconcile_mirror", False)
            steps.ok(f"ephemeral_worktree_PASS head={head}")
            steps.start("materialize_exact_write_set", 10)
            manifest = json.loads((candidate / "bundle-manifest.json").read_text(encoding="utf-8"))["files"]
            for rel in SOURCE_PATHS:
                dst = repo / rel; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(candidate / rel, dst)
                if sha256(dst) != manifest[rel]:
                    raise Blocked("post_copy_hash_mismatch", "discard_ephemeral_checkout_and_recover_candidate", False)
            steps.ok(f"write_set_materialized_paths={len(SOURCE_PATHS)}")
            steps.start("local_prompt_validation", 45)
            python_paths = [str(repo / rel) for rel in SOURCE_PATHS if rel.endswith(".py")]
            compile_result = cp([sys.executable, "-m", "py_compile", *python_paths], timeout_s=30)
            if compile_result.returncode != 0:
                raise Blocked("python_compile_failed", "repair_candidate_before_publication", False)
            validate = cp([sys.executable, SOURCE_PATHS[2]], cwd=repo, timeout_s=15)
            if validate.returncode != 0:
                raise Blocked("prompt_validator_failed", "repair_candidate_before_publication", False)
            tests = cp([sys.executable, "-m", "unittest", "-v", SOURCE_PATHS[3], SOURCE_PATHS[5]], cwd=repo, timeout_s=45)
            if tests.returncode != 0:
                raise Blocked("prompt_or_publisher_hostile_tests_failed", "repair_candidate_before_publication", False)
            diffcheck = cp(["git", "diff", "--check"], cwd=repo, timeout_s=10)
            if diffcheck.returncode != 0:
                raise Blocked("git_diff_check_failed", "repair_candidate_before_publication", False)
            steps.ok("compile_validator_prompt7_publisher5_diffcheck_PASS")
            steps.start("precommit_worktree_gitleaks", 60)
            wreport = private / "worktree-report.json"
            wscan = gitleaks_run(gitleaks, repo, wreport, git_mode=False, timeout_s=60)
            if wscan.returncode != 0 or load_report(wreport):
                raise Blocked("precommit_gitleaks_failed", "do_not_commit_candidate", False)
            steps.ok("precommit_gitleaks_PASS findings=0")
            steps.start("create_local_commit_after_security_PASS", 30)
            add = cp(["git", "add", "--", *SOURCE_PATHS], cwd=repo, timeout_s=10)
            if add.returncode != 0:
                raise Blocked("git_add_failed", "inspect_ephemeral_checkout", True)
            staged = cp(["git", "diff", "--cached", "--name-only"], cwd=repo, timeout_s=10)
            if set(staged.stdout.splitlines()) != set(SOURCE_PATHS):
                raise Blocked("staged_pathset_mismatch", "discard_ephemeral_checkout_and_reconcile", False)
            name = cp(["git", "config", "user.name"], cwd=repo, timeout_s=5)
            email = cp(["git", "config", "user.email"], cwd=repo, timeout_s=5)
            commit_name = name.stdout.strip() if name.returncode == 0 and name.stdout.strip() else FALLBACK_GIT_NAME
            commit_email = email.stdout.strip() if email.returncode == 0 and email.stdout.strip() else FALLBACK_GIT_EMAIL
            commit = cp(["git", "-c", f"user.name={commit_name}", "-c", f"user.email={commit_email}", "commit", "-m", "docs(prompt): add PR5 evidence-currentness continuation v1"], cwd=repo, timeout_s=20)
            if commit.returncode != 0:
                raise Blocked("local_commit_failed", "inspect_ephemeral_checkout", False)
            commit_sha = cp(["git", "rev-parse", "HEAD"], cwd=repo, timeout_s=10).stdout.strip()
            steps.ok(f"local_commit_{commit_sha}")
            steps.start("full_reachable_history_gitleaks", 90)
            hreport = private / "history-report.json"
            hscan = gitleaks_run(gitleaks, repo, hreport, git_mode=True, timeout_s=90)
            if hscan.returncode != 0 or load_report(hreport):
                raise Blocked("full_history_gitleaks_failed", "do_not_push_candidate", False)
            steps.ok("full_reachable_history_gitleaks_PASS findings=0")
            steps.start("prepush_remote_currentness_fence", 20)
            if remote_branch_sha(repo, "main") != args.expected_base:
                raise Blocked("remote_main_drift_before_push", "refresh_base_and_revalidate_candidate", False)
            old_branch = remote_branch_sha(repo, args.branch)
            if old_branch != args.expected_base:
                raise Blocked("reserved_branch_drift_before_push", "recover_reserved_branch_read_only", False)
            steps.ok(f"prepush_fence_PASS main={args.expected_base} reserved_branch={old_branch}")
            pr_url = None
            if args.publish:
                push_with_recovery(repo, args.repo_url, args.branch, commit_sha, old_branch, steps)
                steps.start("postpush_base_currentness_fence", 20)
                if remote_branch_sha(repo, "main") != args.expected_base:
                    raise Blocked("base_drift_after_branch_checkpoint", "keep_branch_checkpoint_and_reconcile_before_PR_creation", False)
                steps.ok(f"postpush_base_fence_PASS main={args.expected_base}")
                pr_url = create_draft_pr(repo, args.branch, commit_sha, steps, args.gh_bin)
            else:
                steps.start("publication_authority", 1); steps.ok("LOCAL_VALIDATION_ONLY no_push no_PR")
            receipt.update({"status":"PASS","commit":commit_sha,"gitleaks_version":GL_VERSION,"gitleaks_exact_outgoing":"PASS","gitleaks_full_history":"PASS","source_paths":list(SOURCE_PATHS),"pr_url":pr_url})
            (evidence / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2)+"\n", encoding="utf-8")
            steps.start("cleanup_ephemeral_worktree", 20)
            remove_worktree(mirror_used, repo)
            steps.ok("ephemeral_worktree_cleanup_PASS mirror_preserved=true")
            lock.close()
            print(f"GATE=PASS COMMIT={commit_sha} BRANCH={args.branch} DRAFT_PR={pr_url or 'DEFERRED_TO_CONNECTOR'}")
            print(f"BREADCRUMBS={evidence}")
            return 0
    except Blocked as b:
        receipt["blocker"]={"reason":b.reason,"next_safe_action":b.next_safe_action,"retry_safe":b.retry_safe}
        (evidence / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2)+"\n", encoding="utf-8")
        steps.blocked(b)

if __name__ == "__main__":
    raise SystemExit(main())
