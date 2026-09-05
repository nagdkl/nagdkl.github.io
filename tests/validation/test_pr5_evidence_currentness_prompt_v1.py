from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
VPATH = ROOT / "scripts/validation/validate_pr5_evidence_currentness_prompt_v1.py"
SPEC = importlib.util.spec_from_file_location("validator", VPATH)
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)
PROMPT = ROOT / validator.PROMPT_PATH

class PromptContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = json.loads(PROMPT.read_text(encoding="utf-8"))

    def validate_copy(self, mutate=None):
        doc = json.loads(json.dumps(self.base))
        if mutate:
            mutate(doc)
        validator.validate(doc)

    def test_canonical_prompt_passes(self):
        self.validate_copy()

    def test_nonzero_retry_rejected(self):
        with self.assertRaises(validator.ValidationError):
            self.validate_copy(lambda d: d["prompt"]["metadata"].__setitem__("automatic_retries", 1))

    def test_ready_authority_rejected(self):
        with self.assertRaises(validator.ValidationError):
            self.validate_copy(lambda d: d["prompt"]["authority"].__setitem__("ready", True))

    def test_direct_main_rejected(self):
        with self.assertRaises(validator.ValidationError):
            self.validate_copy(lambda d: d["prompt"]["git_safety"].__setitem__("direct_main_write", True))

    def test_lane_weights_must_sum_to_one(self):
        with self.assertRaises(validator.ValidationError):
            self.validate_copy(lambda d: d["prompt"]["lane_selection"]["weights"].__setitem__("goal_alignment", 0.99))

    def test_missing_checkpoint_rejected(self):
        with self.assertRaises(validator.ValidationError):
            self.validate_copy(lambda d: d["prompt"]["nano_steps"][0].__setitem__("checkpoint", ""))

    def test_unknown_top_key_rejected(self):
        with self.assertRaises(validator.ValidationError):
            self.validate_copy(lambda d: d["prompt"].__setitem__("decorative_extra", True))

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

if __name__ == "__main__":
    unittest.main()
