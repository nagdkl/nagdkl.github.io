#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import base64
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
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

REPOSITORY = "nagdkl/nagdkl.github.io"
REPO_URL = "https://github.com/nagdkl/nagdkl.github.io.git"
CURRENT_MAIN_SHA = "0271aa210b587e53c08264de3342ba0fd14bb80f"
ORIGINAL_BASE_SHA = "0e872af12b2aee39bc06df49bedf4e5a3179dbdc"
EXPECTED_MAIN_TREE = "285dd06e2192ee1bef33d61f18fcb81917f64ebb"
OLD_HEAD = "adeaf4c92858f0843ecc21210c80817e70851a16"
BRANCH = "prompt/pr5-evidence-currentness-v1-20260905"
PR_NUMBER = 7
MIRROR_REL = Path("synergy/git-mirrors/nagdkl.github.io.git")
GL_VERSION = "8.30.1"
GL_ASSET_URL = "https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_linux_x64.tar.gz"
GL_ASSET_SHA256 = "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb"
GL_CACHE_REL = Path("synergy/downloads/gitleaks") / f"gitleaks_{GL_VERSION}_linux_x64_{GL_ASSET_SHA256}.tar.gz"
FALLBACK_GIT_NAME = "nagdkl"
FALLBACK_GIT_EMAIL = "194505092+nagdkl@users.noreply.github.com"

PUBLISHER = "scripts/human_node/publish_pr5_prompt_governance_v1.py"
VALIDATOR = "scripts/validation/validate_pr5_evidence_currentness_prompt_v1.py"
PROMPT_TEST = "tests/validation/test_pr5_evidence_currentness_prompt_v1.py"
PUBLISHER_TEST = "tests/validation/test_publish_pr5_prompt_governance_v1.py"
RUNNER_GIT = "scripts/human_node/repair_pr7_sonar_gate_v5.py"
RESEARCH_GIT = "docs/research/2026-09-06_pr7-sonar-repair-v5.yaml"
WRITE_SET = (PUBLISHER, VALIDATOR, PROMPT_TEST, PUBLISHER_TEST, RUNNER_GIT, RESEARCH_GIT)
PYTHON_WRITE_SET = (PUBLISHER, VALIDATOR, PROMPT_TEST, PUBLISHER_TEST, RUNNER_GIT)
PREIMAGE_BLOBS = {
    PUBLISHER: "e2c1ac70a41c25c0c876665db4d381c4456ef4c8",
    VALIDATOR: "fea0e8d7933c69adc1dac337157028dc04fa31b7",
    PROMPT_TEST: "a9cb5bac7db3d42ef9b113b7b6a41d9dd57aae43",
    PUBLISHER_TEST: "7d24ec6a86ba45a326dfeef75cb6bfc3438ea0f6",
}

RESEARCH_YAML = r'''schema: synergy.pr7_sonar_repair_research/v5
timestamp_basis: 2026-09-06
repository: nagdkl/nagdkl.github.io
pr: 7
mission: close_exact_six_Sonar_annotations_without_widening_authority
verified_start:
  pr_head: adeaf4c92858f0843ecc21210c80817e70851a16
  current_main: 0271aa210b587e53c08264de3342ba0fd14bb80f
  current_main_tree: 285dd06e2192ee1bef33d61f18fcb81917f64ebb
  incident_issue: 8
sonar_findings:
  - publisher_cognitive_complexity_line_236
  - publisher_duplicate_bundle_manifest_literal_line_112
  - validator_cognitive_complexity_line_63
  - publisher_cognitive_complexity_line_370
  - publisher_test_composite_assertion_line_14
  - validator_cli_path_confinement_line_32
selected_repair:
  - remove_user_controlled_validator_prompt_path
  - preserve_O_NOFOLLOW_regular_file_size_utf8_guards
  - split_validator_invariants_into_helpers
  - split_publisher_mirror_and_publication_phases
  - define_bundle_manifest_constant
  - split_composite_test_assertion
  - add_arbitrary_cwd_and_path_confinement_regressions
  - persist_this_repair_runner_as_normal_Git_source
considered_candidates:
  synergy_donors:
    - PR7_existing_publisher_controls
    - schema_tools_validator_patterns
    - control_plane_currentness_recovery_patterns
    - mcp_vm_control_supply_chain_patterns
  external_reference_only:
    - SonarSource_cognitive_complexity_guidance
  rejected_new_dependencies:
    - Bandit_not_authoritative_for_exact_Sonar_gate
    - Ruff_not_authoritative_for_exact_Sonar_gate
    - new_Git_abstraction_library_unnecessary
criteria:
  - exact_finding_correspondence
  - smallest_touch_surface
  - no_new_runtime_dependency
  - deterministic_hostile_tests
  - Gitleaks_before_commit
  - full_history_Gitleaks_before_push
  - zero_retry_and_read_only_recovery
security:
  gitleaks_version: 8.30.1
  gitleaks_asset_sha256: 551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb
  direct_main_write: forbidden
  force_push: false
  automatic_retries: 0
portability:
  arbitrary_cwd: true
  dirty_unrelated_repo_safe: true
  execution_surfaces: [WSL2, Ubuntu_24, Ubuntu_26, compatible_Debian]
reproducibility:
  GitHub_remote_is_SSOT: true
  local_model: reusable_bare_mirror_plus_ephemeral_worktree
  clone_every_nanostep: false
write_set_gate_repair:
  prior_runner: v3
  prior_blocker: write_set_drift_before_Gitleaks_commit_or_push
  remote_mutation_from_prior_attempt: false
  root_cause: git_diff_name_only_omits_untracked_reusable_Git_artifacts
  expected_existing_modified_paths: 4
  expected_new_untracked_paths: 2
  v4_fix:
    - in_memory_compile_no_pyc
    - unittest_python_B_no_bytecode
    - exact_pathset_union_tracked_diff_and_untracked_files
    - unexpected_or_missing_path_fails_closed
  hostile_AQA:
    exact_4_tracked_plus_2_untracked: PASS
    bytecode_artifacts_absent: PASS
    extra_untracked_path: BLOCKED_PASS
    missing_research_path: BLOCKED_PASS
gitleaks_cache_install_repair:
  prior_runner: v4
  prior_blocker: gitleaks_cache_install_failed_before_commit_or_push
  remote_mutation_from_prior_attempt: false
  root_cause_class: cross_filesystem_unsafe_rename_boundary
  evidence:
    - v4_download_target_is_tempfile_TemporaryDirectory
    - cache_target_is_XDG_CACHE_HOME_or_home_dot_cache
    - Python_os_replace_may_fail_across_filesystems
  selected_synergy_donors:
    - repository: nagdkl-lab/control_plane
      ref: 652f4177816a421877cc79cbad76543f48377498
      path: scripts/git/preserve_local_work_to_draft_pr.py.part02
      pattern: destination_local_mkstemp_flush_fsync_replace_directory_fsync
    - repository: nagdkl-lab/schema_tools
      ref: 2bf7002d47d2edcab8deda56e68266ac4ef12097
      path: tools/wsl2/schema_tools_mvp_acceptance_v1.py
      pattern: destination_local_temp_fsync_atomic_replace
  external_reference:
    source: Python_3_14_os_replace
    url: https://docs.python.org/3/library/os.html#os.replace
    fact: replace_may_fail_when_source_and_destination_are_on_different_filesystems
  v5_fix:
    - nonblocking_cache_lock_zero_retry
    - copy_verified_bytes_to_secure_temp_in_destination_directory
    - flush_and_fsync_temp
    - sha256_readback_before_install
    - same_filesystem_os_replace
    - chmod_0600_and_directory_fsync
    - preserve_existing_invalid_or_unknown_cache
    - explicit_cache_hit_or_miss_terminal_step
    - separate_gitleaks_identity_canary_step
  rejected:
    - shutil_move_reason_not_selected_because_cross_filesystem_copy_semantics_weaken_final_atomic_install_contract
    - direct_cache_download_reason_not_selected_because_crash_can_leave_partial_canonical_asset
recovery:
  timeout_or_ambiguous_push: read_only_reconcile_before_replay
  execution_surface_loss: resume_from_remote_branch_and_Draft_PR
limitations:
  - SonarCloud_is_final_acceptance_surface_for_reported_annotations
  - exact_live_execution_requires_Human_Node_network_surface
assumptions:
  - gh_auth_remains_available_on_Human_Node
known_unknowns:
  - whether_Sonar_emits_new_findings_after_repair
authority:
  draft: true
  ready: false
  merge: false
  runtime: false
  release: false
  deployment: false
  production: false
'''

BUNDLE_MANIFEST_CONSTANT = 'BUNDLE_MANIFEST_NAME = "bundle-manifest.json"\n'

NEW_VALIDATOR = r'''#!/usr/bin/env python3
from __future__ import annotations
import json
import math
import os
from pathlib import Path
import stat

MAX_BYTES = 131072
PROMPT_PATH = "docs/prompts/pr5-evidence-currentness-continuation.v1.yaml"
REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPT_FILE = REPO_ROOT / PROMPT_PATH
EXPECTED_TOP = {"prompt"}
EXPECTED_PROMPT_KEYS = {
    "metadata", "mission", "canonical_full_read_gate", "verified_starting_tuple",
    "prompt_list_improvement", "lane_selection", "council", "reuse_policy",
    "external_candidate_policy", "git_safety", "timeout_policy_seconds",
    "execution_protocol", "nano_steps", "artifact_policy", "human_node_policy",
    "authority", "stop_conditions", "definition_of_done", "execution_start",
}

class ValidationError(ValueError):
    pass

def fail(msg: str) -> None:
    raise ValidationError(msg)

def read_regular(path: Path) -> str:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        fail("O_NOFOLLOW unavailable")
    fd = os.open(path, flags | nofollow)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            fail("regular file required")
        if st.st_size > MAX_BYTES:
            fail("prompt oversized")
        data = bytearray()
        while len(data) <= MAX_BYTES:
            part = os.read(fd, min(65536, MAX_BYTES + 1 - len(data)))
            if not part:
                break
            data.extend(part)
        if len(data) > MAX_BYTES:
            fail("prompt oversized")
    finally:
        os.close(fd)
    try:
        return bytes(data).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError("invalid utf-8") from exc

def walk(value, path="$" ):
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, f"{path}[{index}]")

def require_prompt(doc: dict) -> dict:
    if set(doc) != EXPECTED_TOP:
        fail("unexpected top-level keys")
    prompt = doc["prompt"]
    if not isinstance(prompt, dict) or set(prompt) != EXPECTED_PROMPT_KEYS:
        fail("prompt schema key drift")
    return prompt

def validate_metadata(prompt: dict) -> None:
    expected = {
        "schema": "synergy.pages.pr5-evidence-currentness-continuation/v1",
        "version": "1.0.0",
        "repository": "nagdkl/nagdkl.github.io",
        "pull_request": 5,
        "selected_lane": "PR5-EVIDENCE-CURRENTNESS-RECONCILIATION",
        "execute_in_generation_message": False,
        "automatic_retries": 0,
    }
    metadata = prompt["metadata"]
    for key, value in expected.items():
        if metadata.get(key) != value:
            fail(f"metadata.{key} drift")

def validate_full_read_gate(prompt: dict) -> None:
    gate = prompt["canonical_full_read_gate"]
    if gate.get("required_before_execution") is not True:
        fail("full read gate disabled")
    if gate.get("fail_closed_on_gap") is not True:
        fail("full read fail-closed disabled")

def validate_lane_weights(prompt: dict) -> None:
    weights = prompt["lane_selection"]["weights"]
    if not isinstance(weights, dict) or not weights:
        fail("lane weights missing")
    invalid = any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
        for value in weights.values()
    )
    if invalid:
        fail("invalid lane weight")
    if abs(sum(weights.values()) - 1.0) > 1e-12:
        fail("lane weights must sum to 1")

def validate_reuse_policy(prompt: dict) -> None:
    policy = prompt["reuse_policy"]
    if policy["material_gap_candidate_count"] != {"min": 3, "max": 7}:
        fail("material candidate range drift")
    if policy["trivial_atom_candidate_count"] != 1:
        fail("trivial candidate count drift")

def validate_git_safety(prompt: dict) -> None:
    safety = prompt["git_safety"]
    for key in ("direct_main_write", "force_push", "shared_mutable_branch"):
        if safety.get(key) is not False:
            fail(f"unsafe git setting: {key}")
    if safety.get("gitleaks_before_every_commit") is not True:
        fail("gitleaks law missing")

def validate_authority_and_artifacts(prompt: dict) -> None:
    expected_authority = {
        "draft": True, "ready": False, "merge": False, "runtime": False,
        "release": False, "deployment": False, "production": False,
        "certification": False,
    }
    if prompt["authority"] != expected_authority:
        fail("authority drift")
    artifact = prompt["artifact_policy"]
    if artifact.get("canonical_human_node_publisher_path") != "scripts/human_node/publish_pr5_prompt_governance_v1.py":
        fail("canonical publisher path drift")
    if artifact.get("publisher_test_path") != "tests/validation/test_publish_pr5_prompt_governance_v1.py":
        fail("publisher test path drift")

def validate_execution_protocol(prompt: dict) -> None:
    protocol = prompt["execution_protocol"]
    if protocol.get("one_active_mutation_nano_step") is not True:
        fail("multiple active mutation allowed")
    if protocol.get("decompose_until_each_mutation_is_single_purpose_and_independently_readbackable") is not True:
        fail("nano decomposition law missing")

def validate_nano_steps(prompt: dict) -> None:
    steps = prompt["nano_steps"]
    if not isinstance(steps, list) or len(steps) != 12:
        fail("expected N0..N11")
    if [step.get("id") for step in steps] != [f"N{i}" for i in range(12)]:
        fail("nano step order/id drift")
    for step in steps:
        validate_nano_step(step)

def validate_nano_step(step: dict) -> None:
    if step.get("mutation_class") not in {"READ_ONLY", "LOCAL_EPHEMERAL", "WRITE"}:
        fail("invalid mutation class")
    timeout = step.get("timeout_s")
    if not isinstance(timeout, int) or not 1 <= timeout <= 120:
        fail("invalid step timeout")
    if not step.get("checkpoint"):
        fail("missing checkpoint")

def validate_timeout_policy(prompt: dict) -> None:
    policy = prompt["timeout_policy_seconds"]
    if policy.get("automatic_retries") != 0:
        fail("timeout policy retry drift")
    for key, value in policy.items():
        if key == "automatic_retries":
            continue
        if not isinstance(value, int) or not 1 <= value <= 120:
            fail(f"invalid timeout {key}")

def validate_retry_invariants(prompt: dict) -> None:
    for path, value in walk(prompt):
        leaf = path.rsplit(".", 1)[-1]
        if leaf in {"automatic_retries", "automatic_retry"} and value != 0:
            fail(f"retry drift at {path}")

def validate(doc: dict) -> None:
    prompt = require_prompt(doc)
    validators = (
        validate_metadata,
        validate_full_read_gate,
        validate_lane_weights,
        validate_reuse_policy,
        validate_git_safety,
        validate_authority_and_artifacts,
        validate_execution_protocol,
        validate_nano_steps,
        validate_timeout_policy,
        validate_retry_invariants,
    )
    for validator in validators:
        validator(prompt)

def main() -> int:
    try:
        doc = json.loads(read_regular(PROMPT_FILE))
        if not isinstance(doc, dict):
            fail("root must be object")
        validate(doc)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"VALIDATION=FAIL reason={type(exc).__name__}:{exc}")
        return 1
    print("VALIDATION=PASS schema=synergy.pages.pr5-evidence-currentness-continuation/v1")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
'''

NEW_INITIALIZE_MIRROR = r'''def _install_staged_mirror(staged: Path, mirror: Path, repo_url: str) -> None:
    try:
        os.replace(staged, mirror)
        return
    except OSError:
        pass
    if mirror.exists() and validate_mirror(mirror, repo_url):
        shutil.rmtree(staged, ignore_errors=True)
        return
    raise Blocked("mirror_atomic_install_failed", "inspect_cache_parent_without_deleting_unknown_state", False)


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
    _install_staged_mirror(staged, mirror, repo_url)
    steps.ok(f"canonical_mirror_initialized path={mirror}")
    return mirror
'''

NEW_MAIN_BLOCK = r'''def _prepare_gitleaks_binary(args: argparse.Namespace, private: Path, steps: Steps) -> Path:
    if args.gitleaks_bin is not None:
        return args.gitleaks_bin.resolve(strict=True)
    asset = args.gitleaks_asset.resolve(strict=True) if args.gitleaks_asset else private / "gitleaks.tar.gz"
    if args.gitleaks_asset is None:
        steps.start("download_pinned_gitleaks_asset", 60)
        download(GL_ASSET_URL, asset, 60)
        steps.ok("gitleaks_asset_download_PASS retries=0")
    steps.start("verify_gitleaks_asset_sha256", 10)
    if sha256(asset) != GL_ASSET_SHA256:
        raise Blocked("gitleaks_asset_sha256_mismatch", "stop_and_reconcile_official_asset", False)
    steps.ok(f"gitleaks_asset_sha256_{GL_ASSET_SHA256}")
    return safe_extract_gitleaks(asset, private / "gitleaks-bin")


def _prepare_candidate(args: argparse.Namespace, private: Path, steps: Steps) -> tuple[Path, Path]:
    candidate = safe_extract_bundle(args.bundle.resolve(strict=True), private / "candidate", args.bundle_sha256)
    steps.ok(f"bundle_identity_PASS paths={len(SOURCE_PATHS)}")
    gitleaks = _prepare_gitleaks_binary(args, private, steps)
    validate_gitleaks(gitleaks, private, steps)
    steps.start("exact_outgoing_bundle_gitleaks", 60)
    report = private / "candidate-report.json"
    scan = gitleaks_run(gitleaks, candidate, report, git_mode=False, timeout_s=60)
    if scan.returncode != 0 or load_report(report):
        raise Blocked("exact_outgoing_gitleaks_failed", "do_not_commit_or_publish_candidate", False)
    steps.ok("exact_outgoing_gitleaks_PASS findings=0")
    return candidate, gitleaks


def _prepare_mirror(args: argparse.Namespace, private: Path, steps: Steps) -> tuple[Path, object]:
    cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    mirror = cache_root / MIRROR_REL
    lock = acquire_mirror_lock(mirror.parent / "nagdkl.github.io.mirror.lock")
    try:
        mirror_used = initialize_mirror(args.repo_url, mirror, private, steps)
    except BaseException:
        lock.close()
        raise
    return mirror_used, lock


def _verify_reserved_lane(args: argparse.Namespace, mirror: Path, steps: Steps) -> None:
    steps.start("mirror_currentness_fence", 20)
    local_main = mirror_ref(mirror, "refs/heads/main")
    local_prompt = mirror_ref(mirror, f"refs/heads/{args.branch}")
    if local_main != args.expected_base:
        raise Blocked("base_drift", "refresh_remote_currentness_before_source_write", False)
    if local_prompt != args.expected_base:
        raise Blocked("reserved_branch_drift", "recover_reserved_prompt_branch_read_only", False)
    remote_prompt = remote_branch_sha_from_url(args.repo_url, args.branch)
    if remote_prompt != args.expected_base:
        raise Blocked("reserved_branch_remote_drift", "recover_reserved_prompt_branch_read_only", False)
    for rel in SOURCE_PATHS:
        exists = git_bare(mirror, ["cat-file", "-e", f"{args.expected_base}:{rel}"], timeout_s=5)
        if exists.returncode == 0:
            raise Blocked("candidate_path_already_exists", "inspect_existing_prompt_lane_before_replay", False)
    steps.ok(f"mirror_currentness_PASS main={local_main} reserved_branch={local_prompt}")


def _create_worktree(args: argparse.Namespace, mirror: Path, private: Path, steps: Steps) -> Path:
    repo = private / "worktree"
    steps.start("create_ephemeral_detached_worktree", 30)
    add_detached_worktree(mirror, repo, args.expected_base)
    head = cp(["git", "rev-parse", "HEAD"], cwd=repo, timeout_s=10).stdout.strip()
    if head != args.expected_base:
        raise Blocked("worktree_base_drift", "remove_ephemeral_worktree_and_reconcile_mirror", False)
    steps.ok(f"ephemeral_worktree_PASS head={head}")
    return repo


def _materialize_candidate(candidate: Path, repo: Path, steps: Steps) -> None:
    steps.start("materialize_exact_write_set", 10)
    manifest = json.loads((candidate / BUNDLE_MANIFEST_NAME).read_text(encoding="utf-8"))["files"]
    for rel in SOURCE_PATHS:
        dst = repo / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(candidate / rel, dst)
        if sha256(dst) != manifest[rel]:
            raise Blocked("post_copy_hash_mismatch", "discard_ephemeral_checkout_and_recover_candidate", False)
    steps.ok(f"write_set_materialized_paths={len(SOURCE_PATHS)}")


def _validate_candidate(repo: Path, private: Path, gitleaks: Path, steps: Steps) -> None:
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
    steps.ok("compile_validator_prompt_publisher_diffcheck_PASS")
    steps.start("precommit_worktree_gitleaks", 60)
    report = private / "worktree-report.json"
    scan = gitleaks_run(gitleaks, repo, report, git_mode=False, timeout_s=60)
    if scan.returncode != 0 or load_report(report):
        raise Blocked("precommit_gitleaks_failed", "do_not_commit_candidate", False)
    steps.ok("precommit_gitleaks_PASS findings=0")


def _git_identity(repo: Path) -> tuple[str, str]:
    name = cp(["git", "config", "user.name"], cwd=repo, timeout_s=5)
    email = cp(["git", "config", "user.email"], cwd=repo, timeout_s=5)
    commit_name = name.stdout.strip() if name.returncode == 0 and name.stdout.strip() else FALLBACK_GIT_NAME
    commit_email = email.stdout.strip() if email.returncode == 0 and email.stdout.strip() else FALLBACK_GIT_EMAIL
    return commit_name, commit_email


def _create_verified_commit(repo: Path, private: Path, gitleaks: Path, steps: Steps) -> str:
    steps.start("create_local_commit_after_security_PASS", 30)
    add = cp(["git", "add", "--", *SOURCE_PATHS], cwd=repo, timeout_s=10)
    if add.returncode != 0:
        raise Blocked("git_add_failed", "inspect_ephemeral_checkout", True)
    staged = cp(["git", "diff", "--cached", "--name-only"], cwd=repo, timeout_s=10)
    if set(staged.stdout.splitlines()) != set(SOURCE_PATHS):
        raise Blocked("staged_pathset_mismatch", "discard_ephemeral_checkout_and_reconcile", False)
    commit_name, commit_email = _git_identity(repo)
    commit = cp(["git", "-c", f"user.name={commit_name}", "-c", f"user.email={commit_email}", "commit", "-m", "docs(prompt): add PR5 evidence-currentness continuation v1"], cwd=repo, timeout_s=20)
    if commit.returncode != 0:
        raise Blocked("local_commit_failed", "inspect_ephemeral_checkout", False)
    commit_sha = cp(["git", "rev-parse", "HEAD"], cwd=repo, timeout_s=10).stdout.strip()
    steps.ok(f"local_commit_{commit_sha}")
    steps.start("full_reachable_history_gitleaks", 90)
    report = private / "history-report.json"
    scan = gitleaks_run(gitleaks, repo, report, git_mode=True, timeout_s=90)
    if scan.returncode != 0 or load_report(report):
        raise Blocked("full_history_gitleaks_failed", "do_not_push_candidate", False)
    steps.ok("full_reachable_history_gitleaks_PASS findings=0")
    return commit_sha


def _publish_checkpoint(args: argparse.Namespace, repo: Path, commit_sha: str, steps: Steps) -> str | None:
    steps.start("prepush_remote_currentness_fence", 20)
    if remote_branch_sha(repo, "main") != args.expected_base:
        raise Blocked("remote_main_drift_before_push", "refresh_base_and_revalidate_candidate", False)
    old_branch = remote_branch_sha(repo, args.branch)
    if old_branch != args.expected_base:
        raise Blocked("reserved_branch_drift_before_push", "recover_reserved_branch_read_only", False)
    steps.ok(f"prepush_fence_PASS main={args.expected_base} reserved_branch={old_branch}")
    if not args.publish:
        steps.start("publication_authority", 1)
        steps.ok("LOCAL_VALIDATION_ONLY no_push no_PR")
        return None
    push_with_recovery(repo, args.repo_url, args.branch, commit_sha, old_branch, steps)
    steps.start("postpush_base_currentness_fence", 20)
    if remote_branch_sha(repo, "main") != args.expected_base:
        raise Blocked("base_drift_after_branch_checkpoint", "keep_branch_checkpoint_and_reconcile_before_PR_creation", False)
    steps.ok(f"postpush_base_fence_PASS main={args.expected_base}")
    return create_draft_pr(repo, args.branch, commit_sha, steps, args.gh_bin)


def _write_success_receipt(evidence: Path, receipt: dict[str, object], commit_sha: str, pr_url: str | None) -> None:
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


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    evidence = args.state_root / "runs" / f"{int(time.time())}-{os.getpid()}"
    steps = Steps(evidence)
    receipt: dict[str, object] = {
        "schema": "synergy.pages.pr5_prompt_governance_publication_receipt/v1",
        "status": "BLOCKED",
        "automatic_retries": 0,
        "base": args.expected_base,
        "branch": args.branch,
        "bundle_sha256": args.bundle_sha256,
    }
    try:
        steps.start("preflight_and_bundle_identity", 10)
        if sys.version_info < (3, 10):
            raise Blocked("python_too_old", "use_Python_3_10_plus", False)
        if shutil.which("git") is None:
            raise Blocked("git_missing", "install_git_then_new_attempt", True)
        with tempfile.TemporaryDirectory(prefix="synergy-pr5-prompt-v1-") as td:
            private = Path(td)
            private.chmod(0o700)
            candidate, gitleaks = _prepare_candidate(args, private, steps)
            mirror_used, lock = _prepare_mirror(args, private, steps)
            try:
                _verify_reserved_lane(args, mirror_used, steps)
                repo = _create_worktree(args, mirror_used, private, steps)
                _materialize_candidate(candidate, repo, steps)
                _validate_candidate(repo, private, gitleaks, steps)
                commit_sha = _create_verified_commit(repo, private, gitleaks, steps)
                pr_url = _publish_checkpoint(args, repo, commit_sha, steps)
                _write_success_receipt(evidence, receipt, commit_sha, pr_url)
                steps.start("cleanup_ephemeral_worktree", 20)
                remove_worktree(mirror_used, repo)
                steps.ok("ephemeral_worktree_cleanup_PASS mirror_preserved=true")
            finally:
                lock.close()
        print(f"GATE=PASS COMMIT={commit_sha} BRANCH={args.branch} DRAFT_PR={pr_url or 'DEFERRED_TO_CONNECTOR'}")
        print(f"BREADCRUMBS={evidence}")
        return 0
    except Blocked as blocked:
        receipt["blocker"] = {
            "reason": blocked.reason,
            "next_safe_action": blocked.next_safe_action,
            "retry_safe": blocked.retry_safe,
        }
        (evidence / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        steps.blocked(blocked)
'''

PROMPT_TEST_ADDITION = r'''
    def test_validator_uses_canonical_prompt_from_any_cwd(self):
        original = Path.cwd()
        with tempfile.TemporaryDirectory() as td:
            os.chdir(td)
            try:
                self.assertEqual(validator.main(), 0)
            finally:
                os.chdir(original)

    def test_validator_has_no_user_controlled_prompt_cli_path(self):
        source = VPATH.read_text(encoding="utf-8")
        self.assertNotIn('add_argument("--prompt"', source)
        self.assertNotIn("args.prompt", source)
'''


@dataclass(slots=True)
class Blocked(RuntimeError):
    reason: str
    next_action: str
    code: int = 78


class Steps:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.i = 0
        self.last = 0

    @staticmethod
    def now() -> str:
        return dt_now()

    def emit(self, text: str, *, err: bool = False) -> None:
        print(text, file=sys.stderr if err else sys.stdout, flush=True)
        with (self.root / "steps.log").open("a", encoding="utf-8") as fh:
            fh.write(text + "\n")

    def start(self, action: str, timeout: int) -> None:
        self.i += 1
        self.emit(f"[{self.now()}] STEP_START id={self.i} action={action} timeout={timeout}s retries=0")

    def ok(self, result: str) -> None:
        self.last = self.i
        self.emit(f"[{self.now()}] STEP_OK id={self.i} result={result} last_confirmed={self.last}")

    def stop(self, exc: Blocked) -> NoReturn:
        self.emit(f"[{self.now()}] STEP_BLOCKED id={self.i} result={exc.reason} last_confirmed={self.last}", err=True)
        self.emit(f"STOP reason={exc.reason} next_safe_action={exc.next_action} retry_safe=false breadcrumbs={self.root}", err=True)
        raise SystemExit(exc.code)


def dt_now() -> str:
    import datetime as dt
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def cp(cmd: Sequence[str], *, cwd: Path | None = None, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(list(cmd), cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False, env={**os.environ, "GIT_TERMINAL_PROMPT":"0", "GH_PROMPT_DISABLED":"1"})
    except subprocess.TimeoutExpired as exc:
        raise Blocked("command_timeout", "read_only_outcome_recovery_before_replay", 124) from exc
    except OSError as exc:
        raise Blocked("command_execution_failed", "verify_required_tool", 78) from exc


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_hash(path: Path, repo: Path) -> str:
    result = cp(["git", "hash-object", str(path)], cwd=repo, timeout=10)
    if result.returncode != 0:
        raise Blocked("git_hash_object_failed", "inspect_worktree")
    return result.stdout.strip()


def replace_between(source: str, start: str, end: str, replacement: str) -> str:
    left = source.find(start)
    right = source.find(end, left + len(start))
    if left < 0 or right < 0:
        raise Blocked("source_marker_missing", "refresh_exact_head_and_regenerate_repair")
    return source[:left] + replacement.rstrip() + "\n\n" + source[right:]


def patch_publisher(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    if BUNDLE_MANIFEST_CONSTANT.strip() in source:
        raise Blocked("publisher_already_partially_repaired", "read_only_reconcile_existing_head")
    source = source.replace('"bundle-manifest.json"', "BUNDLE_MANIFEST_NAME")
    anchor = 'FALLBACK_GIT_EMAIL = "194505092+nagdkl@users.noreply.github.com"\n'
    if anchor not in source:
        raise Blocked("publisher_constant_anchor_missing", "refresh_exact_head")
    source = source.replace(anchor, anchor + BUNDLE_MANIFEST_CONSTANT, 1)
    source = replace_between(source, "def initialize_mirror(", "def mirror_ref(", NEW_INITIALIZE_MIRROR)
    main_start = source.find("def main(argv: Sequence[str] | None = None) -> int:")
    guard = source.find('if __name__ == "__main__":', main_start)
    if main_start < 0 or guard < 0:
        raise Blocked("publisher_main_markers_missing", "refresh_exact_head")
    source = source[:main_start] + NEW_MAIN_BLOCK.rstrip() + "\n\n" + source[guard:]
    path.write_text(source, encoding="utf-8")


def patch_validator(path: Path) -> None:
    path.write_text(NEW_VALIDATOR, encoding="utf-8")


def patch_prompt_test(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    if "import os\n" not in source:
        source = source.replace("import json\n", "import json\nimport os\n", 1)
    marker = '\nif __name__ == "__main__":\n'
    if marker not in source:
        raise Blocked("prompt_test_guard_missing", "refresh_exact_head")
    source = source.replace(marker, PROMPT_TEST_ADDITION + marker, 1)
    path.write_text(source, encoding="utf-8")


def patch_publisher_test(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    old = "assert spec and spec.loader\n"
    if old not in source:
        raise Blocked("publisher_test_composite_assertion_missing", "read_only_reconcile_existing_head")
    source = source.replace(old, "assert spec is not None\nassert spec.loader is not None\n", 1)
    path.write_text(source, encoding="utf-8")


def function_decisions(source: str, name: str) -> int:
    tree = ast.parse(source)
    node = next((n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name), None)
    if node is None:
        raise Blocked(f"function_missing_{name}", "inspect_patched_source")
    decision_types = (ast.If, ast.For, ast.While, ast.Try, ast.BoolOp, ast.IfExp, ast.Match)
    return sum(isinstance(n, decision_types) for n in ast.walk(node))


def static_sonar_regressions(repo: Path) -> dict[str, int]:
    publisher = (repo / PUBLISHER).read_text(encoding="utf-8")
    validator = (repo / VALIDATOR).read_text(encoding="utf-8")
    ptest = (repo / PUBLISHER_TEST).read_text(encoding="utf-8")
    if publisher.count('"bundle-manifest.json"') != 1:
        raise Blocked("duplicate_bundle_manifest_literal_not_closed", "repair_candidate")
    if 'add_argument("--prompt"' in validator or "args.prompt" in validator or "import argparse" in validator:
        raise Blocked("user_controlled_validator_path_not_closed", "repair_candidate")
    if "assert spec and spec.loader" in ptest:
        raise Blocked("composite_assertion_not_closed", "repair_candidate")
    decisions = {
        "publisher.initialize_mirror": function_decisions(publisher, "initialize_mirror"),
        "publisher.main": function_decisions(publisher, "main"),
        "validator.validate": function_decisions(validator, "validate"),
    }
    if decisions["publisher.main"] > 6 or decisions["validator.validate"] > 3 or decisions["publisher.initialize_mirror"] > 8:
        raise Blocked("refactor_complexity_sanity_gate_failed", "repair_candidate")
    return decisions


def download(url: str, dst: Path, timeout: int) -> None:
    request = Request(url, headers={"User-Agent":"synergy-pr7-sonar-repair-v5/1"})
    try:
        with urlopen(request, timeout=min(timeout, 15)) as response, dst.open("wb") as out:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    return
                out.write(chunk)
    except (URLError, TimeoutError) as exc:
        raise Blocked("gitleaks_download_failed", "recover_network_then_new_attempt") from exc


def extract_gitleaks(archive: Path, target: Path) -> Path:
    target.mkdir(parents=True, exist_ok=False, mode=0o700)
    with tarfile.open(archive, "r:gz") as tf:
        candidates = []
        for member in tf.getmembers():
            p = Path(member.name)
            if p.is_absolute() or ".." in p.parts or member.issym() or member.islnk() or member.isdev():
                raise Blocked("unsafe_gitleaks_archive", "discard_cached_asset_and_stop")
            if p.name == "gitleaks" and member.isfile():
                candidates.append(member)
        if len(candidates) != 1:
            raise Blocked("gitleaks_member_ambiguous", "discard_cached_asset_and_stop")
        src = tf.extractfile(candidates[0])
        if src is None:
            raise Blocked("gitleaks_extract_failed", "discard_cached_asset_and_stop")
        binary = target / "gitleaks"
        binary.write_bytes(src.read())
        binary.chmod(0o700)
        return binary


def report(path: Path) -> list[object]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, list) else ["malformed"]


def gitleaks_run(binary: Path, source: Path, out: Path, *, git_mode: bool, timeout: int) -> subprocess.CompletedProcess[str]:
    cmd = [str(binary), "detect", "--source", str(source), "--redact", "--report-format", "json", "--report-path", str(out), "--exit-code", "1"]
    if not git_mode:
        cmd.append("--no-git")
    return cp(cmd, timeout=timeout)


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise Blocked(
            "gitleaks_cache_directory_open_failed",
            "inspect_cache_without_deleting_unknown_state",
        ) from exc
    try:
        try:
            os.fsync(fd)
        except OSError as exc:
            raise Blocked(
                "gitleaks_cache_directory_fsync_failed",
                "inspect_cache_without_deleting_unknown_state",
            ) from exc
    finally:
        os.close(fd)


def _acquire_gitleaks_cache_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise Blocked(
            "gitleaks_cache_parent_unsafe",
            "inspect_cache_without_deleting_unknown_state",
        )
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise Blocked(
            "gitleaks_cache_lock_requires_O_NOFOLLOW",
            "use_supported_Linux_execution_surface",
        )
    flags = os.O_RDWR | os.O_CREAT | nofollow
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        raise Blocked(
            "gitleaks_cache_lock_open_failed",
            "inspect_cache_without_deleting_unknown_state",
        ) from exc
    fh = os.fdopen(fd, "a+")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        fh.close()
        raise Blocked(
            "gitleaks_cache_busy",
            "another_process_owns_gitleaks_cache;inspect_then_start_new_attempt",
        ) from exc
    return fh


def _install_verified_cache_file(
    source: Path,
    destination: Path,
    expected_sha256: str,
) -> None:
    try:
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError as exc:
        raise Blocked(
            "gitleaks_cache_parent_create_failed",
            "inspect_cache_without_deleting_unknown_state",
        ) from exc

    if destination.parent.is_symlink() or not destination.parent.is_dir():
        raise Blocked(
            "gitleaks_cache_parent_unsafe",
            "inspect_cache_without_deleting_unknown_state",
        )

    if destination.exists():
        if destination.is_symlink() or not destination.is_file():
            raise Blocked(
                "gitleaks_cache_destination_unsafe",
                "inspect_cache_without_deleting_unknown_state",
            )
        if sha256(destination) == expected_sha256:
            return
        raise Blocked(
            "cached_gitleaks_asset_sha256_mismatch",
            "preserve_invalid_cache_and_inspect",
        )

    try:
        fd, temporary = tempfile.mkstemp(
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
        )
    except OSError as exc:
        raise Blocked(
            "gitleaks_cache_temp_create_failed",
            "inspect_cache_without_deleting_unknown_state",
        ) from exc

    temp_path = Path(temporary)
    try:
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as out, source.open("rb") as src:
                shutil.copyfileobj(src, out, length=1024 * 1024)
                out.flush()
                os.fsync(out.fileno())
        except OSError as exc:
            raise Blocked(
                "gitleaks_cache_temp_write_failed",
                "inspect_cache_without_deleting_unknown_state",
            ) from exc

        if sha256(temp_path) != expected_sha256:
            raise Blocked(
                "gitleaks_destination_temp_sha256_mismatch",
                "discard_destination_temp",
            )

        try:
            os.replace(temp_path, destination)
        except OSError as exc:
            if (
                destination.exists()
                and destination.is_file()
                and not destination.is_symlink()
                and sha256(destination) == expected_sha256
            ):
                return
            raise Blocked(
                "gitleaks_cache_install_failed",
                "inspect_cache_without_deleting_unknown_state",
            ) from exc

        try:
            os.chmod(destination, 0o600)
        except OSError as exc:
            raise Blocked(
                "gitleaks_cache_chmod_failed",
                "inspect_cache_without_deleting_unknown_state",
            ) from exc

        _fsync_directory(destination.parent)

        if sha256(destination) != expected_sha256:
            raise Blocked(
                "gitleaks_cache_postinstall_sha256_mismatch",
                "preserve_cache_and_stop",
            )
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def prepare_gitleaks(
    private: Path,
    cache_root: Path,
    steps: Steps,
) -> Path:
    asset = cache_root / GL_CACHE_REL
    try:
        asset.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError as exc:
        raise Blocked(
            "gitleaks_cache_parent_create_failed",
            "inspect_cache_without_deleting_unknown_state",
        ) from exc

    steps.start("prepare_pinned_gitleaks_asset_cache", 90)
    lock = _acquire_gitleaks_cache_lock(
        asset.parent / f".{asset.name}.lock"
    )
    try:
        if asset.exists():
            if asset.is_symlink() or not asset.is_file():
                raise Blocked(
                    "gitleaks_cache_destination_unsafe",
                    "inspect_cache_without_deleting_unknown_state",
                )
            if sha256(asset) != GL_ASSET_SHA256:
                raise Blocked(
                    "cached_gitleaks_asset_sha256_mismatch",
                    "preserve_invalid_cache_and_inspect",
                )
            steps.ok("gitleaks_asset_cache_HIT_PASS")
        else:
            staged = private / "gitleaks.tar.gz"
            download(GL_ASSET_URL, staged, 90)
            if sha256(staged) != GL_ASSET_SHA256:
                raise Blocked(
                    "gitleaks_asset_sha256_mismatch",
                    "discard_download",
                )
            source_dev = staged.stat().st_dev
            cache_dev = asset.parent.stat().st_dev
            _install_verified_cache_file(
                staged,
                asset,
                GL_ASSET_SHA256,
            )
            steps.ok(
                "gitleaks_asset_cache_MISS_install_PASS "
                f"source_dev={source_dev} "
                f"cache_dev={cache_dev} "
                f"cross_fs={str(source_dev != cache_dev).lower()}"
            )
    finally:
        lock.close()

    steps.start("gitleaks_identity_and_canaries", 75)
    binary = extract_gitleaks(
        asset,
        private / "gitleaks-bin",
    )
    version = cp(
        [str(binary), "version"],
        timeout=10,
    )
    if (
        version.returncode != 0
        or GL_VERSION not in (
            version.stdout + version.stderr
        )
    ):
        raise Blocked(
            "gitleaks_version_drift",
            "stop_and_reconcile_scanner",
        )

    alphabet = (
        string.ascii_letters
        + string.digits
    )
    token = (
        "gh"
        + "p_"
        + "".join(
            secrets.choice(alphabet)
            for _ in range(36)
        )
    )

    pos = private / "canary-positive"
    pos.mkdir()
    (pos / "fixture.txt").write_text(
        f'github_token = "{token}"\n'
    )
    pos_report = private / "pos.json"
    pos_run = gitleaks_run(
        binary,
        pos,
        pos_report,
        git_mode=False,
        timeout=30,
    )
    if (
        pos_run.returncode != 1
        or not report(pos_report)
    ):
        raise Blocked(
            "gitleaks_positive_canary_failed",
            "do_not_credit_scanner",
        )

    neg = private / "canary-negative"
    neg.mkdir()
    (neg / "fixture.txt").write_text(
        "no credential material\n"
    )
    neg_report = private / "neg.json"
    neg_run = gitleaks_run(
        binary,
        neg,
        neg_report,
        git_mode=False,
        timeout=30,
    )
    if (
        neg_run.returncode != 0
        or report(neg_report)
    ):
        raise Blocked(
            "gitleaks_negative_canary_failed",
            "do_not_credit_scanner",
        )

    steps.ok(
        "gitleaks_identity_canaries_PASS"
    )
    return binary


def git_bare(mirror: Path, args: Sequence[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return cp(["git", f"--git-dir={mirror}", *args], timeout=timeout)


def validate_mirror(mirror: Path) -> bool:
    if not mirror.is_dir():
        return False
    bare = git_bare(mirror, ["rev-parse", "--is-bare-repository"], 5)
    origin = git_bare(mirror, ["remote", "get-url", "origin"], 5)
    return bare.returncode == 0 and bare.stdout.strip() == "true" and origin.returncode == 0 and origin.stdout.strip() == REPO_URL


def acquire_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fh = path.open("a+")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        fh.close()
        raise Blocked("mirror_busy", "inspect_other_synergy_mirror_owner") from exc
    return fh


def fetch_required_refs(mirror: Path, timeout: int) -> None:
    result = git_bare(mirror, ["fetch", "--quiet", "--no-tags", "--prune", "origin", "+refs/heads/main:refs/heads/main", f"+refs/heads/{BRANCH}:refs/heads/{BRANCH}"], timeout)
    if result.returncode != 0:
        raise Blocked("mirror_fetch_failed", "recover_connectivity_then_new_attempt")


def prepare_mirror(private: Path, cache_root: Path, steps: Steps) -> tuple[Path, object]:
    mirror = cache_root / MIRROR_REL
    lock = acquire_lock(mirror.parent / "nagdkl.github.io.mirror.lock")
    try:
        if validate_mirror(mirror):
            steps.start("refresh_branch_scoped_mirror", 90)
            fetch_required_refs(mirror, 90)
            steps.ok("mirror_refresh_PASS")
            return mirror, lock
        if mirror.exists():
            raise Blocked("canonical_mirror_invalid", "preserve_and_inspect_invalid_cache")
        staged = private / "new-mirror.git"
        cp(["git", "init", "--bare", "--quiet", str(staged)], timeout=15)
        remote = git_bare(staged, ["remote", "add", "origin", REPO_URL], 10)
        if remote.returncode != 0:
            raise Blocked("mirror_remote_add_failed", "inspect_staged_mirror")
        steps.start("initialize_branch_scoped_mirror", 240)
        fetch_required_refs(staged, 240)
        fsck = git_bare(staged, ["fsck", "--connectivity-only", "--no-progress"], 30)
        if fsck.returncode != 0:
            raise Blocked("mirror_connectivity_failed", "discard_staged_mirror")
        os.replace(staged, mirror)
        steps.ok("branch_scoped_mirror_init_PASS")
        return mirror, lock
    except BaseException:
        lock.close()
        raise


def mirror_ref(mirror: Path, ref: str) -> str:
    result = git_bare(mirror, ["rev-parse", "--verify", ref], 10)
    if result.returncode != 0:
        raise Blocked("mirror_ref_missing", "refresh_read_only_currentness")
    return result.stdout.strip()


def gh_json(endpoint: str, timeout: int = 20):
    gh = shutil.which("gh")
    if gh is None:
        raise Blocked("gh_missing", "restore_previously_used_GitHub_CLI")
    result = cp([gh, "api", "--hostname", "github.com", endpoint], timeout=timeout)
    if result.returncode != 0:
        raise Blocked("gh_api_read_failed", "recover_GitHub_auth_or_connectivity")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise Blocked("gh_api_json_invalid", "inspect_read_only_response") from exc


def mirror_tree(mirror: Path, ref: str) -> str:
    result = git_bare(mirror, ["rev-parse", "--verify", f"{ref}^{{tree}}"], 10)
    if result.returncode != 0:
        raise Blocked("mirror_tree_missing", "refresh_read_only_currentness")
    return result.stdout.strip()


def pr_base_binding_ok(pr: object) -> bool:
    if not isinstance(pr, dict):
        return False
    base = pr.get("base")
    if not isinstance(base, dict) or base.get("ref") != "main":
        return False
    return base.get("sha") in {ORIGINAL_BASE_SHA, CURRENT_MAIN_SHA}


def verify_remote_tuple(mirror: Path, steps: Steps) -> None:
    main = mirror_ref(mirror, "refs/heads/main")
    head = mirror_ref(mirror, f"refs/heads/{BRANCH}")
    main_tree = mirror_tree(mirror, "refs/heads/main")
    if main != CURRENT_MAIN_SHA or head != OLD_HEAD:
        raise Blocked("remote_tuple_drift", "read_only_reconcile_main_branch_PR")
    if main_tree != EXPECTED_MAIN_TREE:
        raise Blocked("main_tree_drift", "read_only_reconcile_main_tree")
    pr = gh_json(f"repos/{REPOSITORY}/pulls/{PR_NUMBER}")
    if not (
        isinstance(pr, dict)
        and pr.get("state") == "open"
        and pr.get("draft") is True
        and isinstance(pr.get("head"), dict)
        and pr["head"].get("sha") == OLD_HEAD
        and pr_base_binding_ok(pr)
    ):
        raise Blocked("PR7_currentness_drift", "read_only_reconcile_PR7")
    steps.ok(
        f"currentness_PASS main={main} tree={main_tree} "
        f"branch={head} PR7=OPEN_DRAFT base_ref=main"
    )


def create_worktree(mirror: Path, private: Path) -> Path:
    repo = private / "worktree"
    result = git_bare(mirror, ["worktree", "add", "--detach", str(repo), OLD_HEAD], 30)
    if result.returncode != 0:
        raise Blocked("worktree_add_failed", "inspect_mirror_worktree_metadata")
    return repo


def verify_preimages(repo: Path) -> None:
    for rel, expected in PREIMAGE_BLOBS.items():
        if git_hash(repo / rel, repo) != expected:
            raise Blocked(f"preimage_drift_{rel}", "read_only_reconcile_exact_PR7_head")
    for rel in (RUNNER_GIT, RESEARCH_GIT):
        if (repo / rel).exists():
            raise Blocked(f"new_path_already_exists_{rel}", "read_only_reconcile_exact_PR7_head")


def persist_reusable_artifacts(repo: Path) -> None:
    runner_dst = repo / RUNNER_GIT
    runner_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(__file__).resolve(strict=True), runner_dst)
    runner_dst.chmod(0o700)
    research_dst = repo / RESEARCH_GIT
    research_dst.parent.mkdir(parents=True, exist_ok=True)
    research_dst.write_text(RESEARCH_YAML, encoding="utf-8")
    research_dst.chmod(0o600)


def apply_patch(repo: Path) -> dict[str, int]:
    patch_publisher(repo / PUBLISHER)
    patch_validator(repo / VALIDATOR)
    patch_prompt_test(repo / PROMPT_TEST)
    patch_publisher_test(repo / PUBLISHER_TEST)
    persist_reusable_artifacts(repo)
    return static_sonar_regressions(repo)


def compile_sources_in_memory(repo: Path) -> None:
    for rel in PYTHON_WRITE_SET:
        path = repo / rel
        try:
            source = path.read_text(encoding="utf-8")
            compile(source, str(path), "exec")
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            raise Blocked(f"python_compile_failed_{rel}", "repair_candidate") from exc


def exact_worktree_paths(repo: Path) -> set[str]:
    tracked = cp(["git", "diff", "--name-only"], cwd=repo, timeout=10)
    if tracked.returncode != 0:
        raise Blocked("git_diff_name_read_failed", "inspect_ephemeral_worktree")
    untracked = cp(["git", "ls-files", "--others", "--exclude-standard"], cwd=repo, timeout=10)
    if untracked.returncode != 0:
        raise Blocked("git_untracked_name_read_failed", "inspect_ephemeral_worktree")
    return {line for line in (*tracked.stdout.splitlines(), *untracked.stdout.splitlines()) if line}


def run_tests(repo: Path, steps: Steps) -> None:
    steps.start("compile_and_hostile_tests", 90)
    compile_sources_in_memory(repo)
    tests = cp([sys.executable, "-B", "-m", "unittest", "-v", PROMPT_TEST, PUBLISHER_TEST], cwd=repo, timeout=60)
    if tests.returncode != 0:
        raise Blocked("focused_tests_failed", "repair_candidate")
    diff = cp(["git", "diff", "--check"], cwd=repo, timeout=10)
    if diff.returncode != 0:
        raise Blocked("git_diff_check_failed", "repair_candidate")
    observed = exact_worktree_paths(repo)
    if observed != set(WRITE_SET):
        unexpected = sorted(observed - set(WRITE_SET))
        missing = sorted(set(WRITE_SET) - observed)
        raise Blocked(
            "write_set_drift"
            f"_unexpected={','.join(unexpected) or 'none'}"
            f"_missing={','.join(missing) or 'none'}",
            "discard_worktree_and_reconcile",
        )
    steps.ok("compile_tests_diff_exact_write_set_PASS")


def scan_worktree(repo: Path, private: Path, gitleaks: Path, steps: Steps) -> None:
    steps.start("precommit_gitleaks", 60)
    out = private / "worktree-gitleaks.json"
    scan = gitleaks_run(gitleaks, repo, out, git_mode=False, timeout=60)
    if scan.returncode != 0 or report(out):
        raise Blocked("precommit_gitleaks_failed", "do_not_commit")
    steps.ok("precommit_gitleaks_PASS findings=0")


def commit_candidate(repo: Path, private: Path, gitleaks: Path, steps: Steps) -> str:
    add = cp(["git", "add", "--", *WRITE_SET], cwd=repo, timeout=10)
    if add.returncode != 0:
        raise Blocked("git_add_failed", "inspect_worktree")
    staged = cp(["git", "diff", "--cached", "--name-only"], cwd=repo, timeout=10)
    if set(staged.stdout.splitlines()) != set(WRITE_SET):
        raise Blocked("staged_pathset_mismatch", "do_not_commit")
    name = cp(["git", "config", "user.name"], cwd=repo, timeout=5)
    email = cp(["git", "config", "user.email"], cwd=repo, timeout=5)
    commit_name = name.stdout.strip() if name.returncode == 0 and name.stdout.strip() else FALLBACK_GIT_NAME
    commit_email = email.stdout.strip() if email.returncode == 0 and email.stdout.strip() else FALLBACK_GIT_EMAIL
    steps.start("create_followup_commit", 30)
    commit = cp(["git", "-c", f"user.name={commit_name}", "-c", f"user.email={commit_email}", "commit", "-m", "fix(sonar): harden PR7 prompt governance"], cwd=repo, timeout=20)
    if commit.returncode != 0:
        raise Blocked("local_commit_failed", "inspect_worktree")
    head = cp(["git", "rev-parse", "HEAD"], cwd=repo, timeout=10).stdout.strip()
    steps.ok(f"local_commit_PASS sha={head}")
    steps.start("full_history_gitleaks", 90)
    out = private / "history-gitleaks.json"
    scan = gitleaks_run(gitleaks, repo, out, git_mode=True, timeout=90)
    if scan.returncode != 0 or report(out):
        raise Blocked("full_history_gitleaks_failed", "do_not_push")
    steps.ok("full_history_gitleaks_PASS findings=0")
    return head


def remote_ref(branch: str) -> str:
    result = cp(["git", "ls-remote", "--heads", REPO_URL, f"refs/heads/{branch}"], timeout=20)
    if result.returncode != 0 or not result.stdout.strip():
        raise Blocked("remote_ref_read_failed", "read_only_recover_remote")
    return result.stdout.split()[0]


def push_exact(repo: Path, commit: str, steps: Steps) -> None:
    if remote_ref("main") != CURRENT_MAIN_SHA or remote_ref(BRANCH) != OLD_HEAD:
        raise Blocked("prepush_currentness_drift", "read_only_reconcile_before_replay")
    steps.start("zero_retry_push", 60)
    try:
        result = cp(["git", "push", REPO_URL, f"HEAD:refs/heads/{BRANCH}"], cwd=repo, timeout=60)
    except Blocked as exc:
        if exc.code != 124:
            raise
        observed = remote_ref(BRANCH)
        if observed == commit:
            steps.ok(f"push_outcome_recovered_PASS sha={commit}")
            return
        raise Blocked("push_outcome_unknown", "read_only_reconcile_before_any_replay", 124)
    observed = remote_ref(BRANCH)
    if result.returncode != 0 or observed != commit:
        raise Blocked("push_or_readback_failed", "read_only_reconcile_before_any_replay")
    steps.ok(f"remote_branch_exact_readback_PASS sha={commit}")


def sonar_readback(commit: str, steps: Steps) -> str:
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        value = gh_json(f"repos/{REPOSITORY}/commits/{commit}/check-runs", 20)
        runs = value.get("check_runs", []) if isinstance(value, dict) else []
        sonar = [r for r in runs if isinstance(r, dict) and r.get("name") == "SonarCloud Code Analysis" and r.get("head_sha") == commit]
        if sonar:
            run = sonar[0]
            if run.get("status") == "completed":
                conclusion = str(run.get("conclusion"))
                if conclusion == "success":
                    return "PASS"
                count = int((run.get("output") or {}).get("annotations_count") or 0)
                annotations = gh_json(f"repos/{REPOSITORY}/check-runs/{run['id']}/annotations?per_page=100", 20)
                safe = []
                if isinstance(annotations, list):
                    for row in annotations:
                        if isinstance(row, dict):
                            safe.append({k:row.get(k) for k in ("path","start_line","end_line","annotation_level","title")})
                (steps.root / "sonar-annotations.sanitized.json").write_text(json.dumps(safe, indent=2, sort_keys=True)+"\n")
                print("SONAR_ANNOTATIONS_BEGIN")
                print(json.dumps(safe, indent=2, sort_keys=True))
                print("SONAR_ANNOTATIONS_END")
                raise Blocked(f"sonar_failed_annotations_{count}", "review_exact_new_annotations_without_replaying_push")
        time.sleep(10)
    return "PENDING"


def cleanup_worktree(mirror: Path, repo: Path) -> None:
    if not repo.exists():
        return
    git_bare(mirror, ["worktree", "remove", "--force", str(repo)], 20)


def main() -> int:
    state = Path.home() / ".local/state/synergy-mesh/pr7-sonar-repair-v5"
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    run = Path(tempfile.mkdtemp(prefix="run.", dir=state)); os.chmod(run, 0o700)
    steps = Steps(run)
    print(f"RESUME last_confirmed=224 state=PR7_exact_head_Sonar6_repair_v5 run_dir={run}", flush=True)
    if sys.version_info < (3, 10):
        steps.stop(Blocked("python_too_old", "use_Python_3_10_plus"))
    if shutil.which("git") is None:
        steps.stop(Blocked("git_missing", "install_git"))
    cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    mirror = None
    lock = None
    repo = None
    try:
        with tempfile.TemporaryDirectory(prefix="synergy-pr7-sonar-") as td:
            private = Path(td); private.chmod(0o700)
            mirror, lock = prepare_mirror(private, cache_root, steps)
            steps.start("exact_remote_tuple", 30)
            verify_remote_tuple(mirror, steps)
            repo = create_worktree(mirror, private)
            verify_preimages(repo)
            steps.start("apply_exact_six_path_repair", 30)
            decisions = apply_patch(repo)
            steps.ok("patch_PASS decisions=" + json.dumps(decisions, sort_keys=True))
            run_tests(repo, steps)
            gitleaks = prepare_gitleaks(private, cache_root, steps)
            scan_worktree(repo, private, gitleaks, steps)
            commit = commit_candidate(repo, private, gitleaks, steps)
            push_exact(repo, commit, steps)
            pr = gh_json(f"repos/{REPOSITORY}/pulls/{PR_NUMBER}")
            if not (isinstance(pr, dict) and pr.get("draft") is True and pr.get("state") == "open" and isinstance(pr.get("head"), dict) and pr["head"].get("sha") == commit and pr_base_binding_ok(pr)):
                raise Blocked("PR7_postpush_readback_failed", "read_only_reconcile_PR7")
            steps.start("Sonar_readback", 180)
            sonar = sonar_readback(commit, steps)
            steps.ok(f"Sonar_{sonar}")
            receipt = {
                "schema":"synergy.pr7_sonar_repair_receipt/v5",
                "status":"PASS" if sonar == "PASS" else "CHECKPOINTED_SONAR_PENDING",
                "old_head":OLD_HEAD,
                "current_main":CURRENT_MAIN_SHA,
                "expected_main_tree":EXPECTED_MAIN_TREE,
                "incident_issue":8,
                "commit":commit,
                "write_set":list(WRITE_SET),
                "gitleaks_version":GL_VERSION,
                "precommit_gitleaks":"PASS",
                "full_history_gitleaks":"PASS",
                "draft":True,
                "sonar":sonar,
            }
            (run / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n")
            cleanup_worktree(mirror, repo)
            print(f"GATE=PASS COMMIT={commit} PR=7 DRAFT=true SONAR={sonar}")
            print(f"BREADCRUMBS={run}")
            return 0
    except Blocked as exc:
        steps.stop(exc)
    finally:
        if lock is not None:
            lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
