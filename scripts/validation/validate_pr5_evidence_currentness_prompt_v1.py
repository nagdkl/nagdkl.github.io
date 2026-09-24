#!/usr/bin/env python3
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
