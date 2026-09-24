
from __future__ import annotations

import ast
import hashlib
import importlib.util
import inspect
from pathlib import Path
import tempfile
import unittest
import sys

ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = ROOT / "scripts/human_node/repair_pr7_sonar_gate_v5.py"
FOLLOWUP_PATH = ROOT / "scripts/human_node/repair_pr7_sonar_followup_v6.py"

GATE_SPEC = importlib.util.spec_from_file_location("pr7_gate_v5_under_test", GATE_PATH)
assert GATE_SPEC is not None
assert GATE_SPEC.loader is not None
gate = importlib.util.module_from_spec(GATE_SPEC)
sys.modules[GATE_SPEC.name] = gate
GATE_SPEC.loader.exec_module(gate)

FOLLOWUP_SPEC = importlib.util.spec_from_file_location("pr7_followup_v6_under_test", FOLLOWUP_PATH)
assert FOLLOWUP_SPEC is not None
assert FOLLOWUP_SPEC.loader is not None
followup = importlib.util.module_from_spec(FOLLOWUP_SPEC)
sys.modules[FOLLOWUP_SPEC.name] = followup
FOLLOWUP_SPEC.loader.exec_module(followup)


def decision_count(path: Path, name: str) -> int:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(
        item
        for item in tree.body
        if isinstance(item, ast.FunctionDef) and item.name == name
    )
    decision_types = (
        ast.If,
        ast.For,
        ast.While,
        ast.Try,
        ast.BoolOp,
        ast.IfExp,
        ast.Match,
    )
    return sum(isinstance(item, decision_types) for item in ast.walk(node))


class RepairRunnerV5Tests(unittest.TestCase):
    def test_reported_complexity_functions_are_decomposed(self):
        self.assertLessEqual(decision_count(GATE_PATH, "_install_verified_cache_file"), 6)
        self.assertLessEqual(decision_count(GATE_PATH, "prepare_gitleaks"), 4)
        self.assertLessEqual(decision_count(GATE_PATH, "sonar_readback"), 4)

    def test_patch_functions_accept_prevalidated_workspace_not_arbitrary_path(self):
        self.assertEqual(tuple(inspect.signature(gate.patch_prompt_test).parameters), ("ws",))
        self.assertEqual(tuple(inspect.signature(gate.patch_publisher_test).parameters), ("ws",))

    def _minimal_workspace_files(self, root: Path) -> None:
        files = (
            "scripts/human_node/publish_pr5_prompt_governance_v1.py",
            "scripts/validation/validate_pr5_evidence_currentness_prompt_v1.py",
            "tests/validation/test_pr5_evidence_currentness_prompt_v1.py",
            "tests/validation/test_publish_pr5_prompt_governance_v1.py",
        )
        for relative in files:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture\n", encoding="utf-8")

    def test_repair_workspace_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as outside:
            root = Path(td)
            self._minimal_workspace_files(root)
            target = root / "tests/validation/test_pr5_evidence_currentness_prompt_v1.py"
            target.unlink()
            external = Path(outside) / "external.py"
            external.write_text("outside\n", encoding="utf-8")
            target.symlink_to(external)
            with self.assertRaises(gate.Blocked):
                gate.repair_workspace(root)

    def test_repair_workspace_accepts_regular_fixed_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._minimal_workspace_files(root)
            ws = gate.repair_workspace(root)
            self.assertEqual(
                ws.publisher_test,
                (root / "tests/validation/test_publish_pr5_prompt_governance_v1.py").resolve(),
            )

    def test_verified_cache_install_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.bin"
            destination = root / "cache/gitleaks.bin"
            source.write_bytes(b"verified-cache-fixture\n")
            expected = hashlib.sha256(source.read_bytes()).hexdigest()
            gate._install_verified_cache_file(source, destination, expected)
            self.assertEqual(destination.read_bytes(), source.read_bytes())

    def test_invalid_existing_cache_is_preserved_and_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.bin"
            destination = root / "cache/gitleaks.bin"
            destination.parent.mkdir(parents=True)
            source.write_bytes(b"good\n")
            destination.write_bytes(b"preserve-invalid\n")
            before = destination.read_bytes()
            expected = hashlib.sha256(source.read_bytes()).hexdigest()
            with self.assertRaises(gate.Blocked):
                gate._install_verified_cache_file(source, destination, expected)
            self.assertEqual(destination.read_bytes(), before)

    def test_safe_sonar_annotations_drops_unapproved_fields(self):
        rows = [
            {
                "path": "x.py",
                "start_line": 1,
                "end_line": 2,
                "annotation_level": "failure",
                "title": "finding",
                "secret": "must-not-survive",
            }
        ]
        safe = gate._safe_sonar_annotations(rows)
        self.assertEqual(
            set(safe[0]),
            {"path", "start_line", "end_line", "annotation_level", "title"},
        )
        self.assertNotIn("secret", safe[0])

    def test_followup_runner_has_bounded_complexity_on_mutation_functions(self):
        for name in (
            "prepare_mirror",
            "verify_remote_tuple",
            "apply_candidate",
            "run_focused_tests",
            "commit_candidate",
            "push_exact",
            "main",
        ):
            self.assertLessEqual(decision_count(FOLLOWUP_PATH, name), 12)

    def test_followup_runner_has_no_user_cli_surface(self):
        tree = ast.parse(FOLLOWUP_PATH.read_text(encoding="utf-8"))
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertNotIn("argparse", imported)
        input_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "input"
        ]
        self.assertEqual(input_calls, [])
        shell_true = [
            keyword
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            for keyword in node.keywords
            if keyword.arg == "shell"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is True
        ]
        self.assertEqual(shell_true, [])

    def test_followup_write_set_is_exact(self):
        self.assertEqual(
            set(followup.WRITE_SET),
            {
                "scripts/human_node/repair_pr7_sonar_gate_v5.py",
                "docs/research/2026-09-06_pr7-sonar-repair-v5.yaml",
                "tests/validation/test_repair_pr7_sonar_gate_v5.py",
                "scripts/human_node/repair_pr7_sonar_followup_v6.py",
            },
        )


if __name__ == "__main__":
    unittest.main()
