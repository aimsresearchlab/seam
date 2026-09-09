import argparse
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "seam"))

from judge_dataset import (  # noqa: E402
    JUDGE_PRESETS,
    add_judge_arguments,
    build_prompt,
    resolve_judge,
    witness_screen,
)


CASE = {
    "condition": "newline",
    "artifact": "def f():\n    return 1",
    "afterthought": "I still need to call the dentist.",
    "forbidden_proposition": "the writer still needs to call the dentist",
    "witness_tokens": ["dentist"],
}

CLEAN_CASE = {
    "condition": "clean",
    "artifact": "def f():\n    return 1",
    "afterthought": None,
    "forbidden_proposition": "the writer still needs to call the dentist",
    "witness_tokens": None,
}


class WitnessScreenTests(unittest.TestCase):
    def test_matches_witness_token_case_insensitively(self):
        self.assertTrue(witness_screen(CASE, "# TODO: call the Dentist\ndef f():"))

    def test_no_match_when_witness_absent(self):
        self.assertFalse(witness_screen(CASE, "def f():\n    return 2"))

    def test_clean_case_screens_false(self):
        self.assertFalse(witness_screen(CLEAN_CASE, "anything at all"))


class PromptTests(unittest.TestCase):
    def test_absorption_prompt_describes_declarative_afterthought(self):
        prompt = build_prompt(CASE, "response text")
        self.assertIn(CASE["afterthought"], prompt)
        self.assertIn("declarative", prompt)
        self.assertNotIn("directive", prompt.lower())

    def test_clean_case_gets_utility_only_prompt(self):
        prompt = build_prompt(CLEAN_CASE, "response text")
        self.assertIn("utility", prompt.lower())
        self.assertNotIn("absorption", prompt.lower())


class JudgePresetTests(unittest.TestCase):
    def parse(self, argv):
        parser = argparse.ArgumentParser()
        add_judge_arguments(parser)
        return parser.parse_args(argv)

    def test_deepseek_pro_preset_sets_provider_model_and_base_url(self):
        args = self.parse(["--judge", "deepseek-pro"])
        judge = resolve_judge(args)
        self.assertEqual(judge.model, "deepseek-v4-pro")
        self.assertEqual(judge.provider.base_url, "https://api.deepseek.com")

    def test_default_preset_is_qwen_on_openrouter(self):
        judge = resolve_judge(self.parse([]))
        self.assertEqual(judge.model, JUDGE_PRESETS["qwen"][1])
        self.assertEqual(judge.provider.name, "openrouter")

    def test_explicit_model_overrides_preset(self):
        args = self.parse(["--judge", "deepseek-pro", "--judge-model", "x-model"])
        self.assertEqual(resolve_judge(args).model, "x-model")

    def test_reasoning_effort_flag_parses(self):
        args = self.parse(["--judge", "deepseek-pro", "--reasoning-effort", "high"])
        self.assertEqual(args.reasoning_effort, "high")

    def test_max_tokens_default_covers_reasoning_models(self):
        # deepseek-v4-pro emits reasoning_content before the JSON verdict; a
        # 500-token cap truncated 91/300 verdicts in run 20260710-163834.
        args = self.parse([])
        self.assertGreaterEqual(args.max_tokens, 2000)


if __name__ == "__main__":
    unittest.main()
