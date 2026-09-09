import argparse
import unittest

from seam.api_client import PROVIDERS, add_provider_arguments, resolve_provider


class ProviderConfigTests(unittest.TestCase):
    def parser(self):
        parser = argparse.ArgumentParser()
        add_provider_arguments(parser)
        return parser

    def test_openrouter_defaults(self):
        config = resolve_provider(self.parser().parse_args([]))
        self.assertEqual(config, PROVIDERS["openrouter"])

    def test_deepseek_defaults(self):
        args = self.parser().parse_args(["--provider", "deepseek"])
        config = resolve_provider(args)
        self.assertEqual(config.base_url, "https://api.deepseek.com")
        self.assertEqual(config.api_key_env, "DEEPSEEK_API_KEY")

    def test_caller_can_select_deepseek_as_default(self):
        parser = argparse.ArgumentParser()
        add_provider_arguments(parser, default_provider="deepseek")
        config = resolve_provider(parser.parse_args([]))
        self.assertEqual(config, PROVIDERS["deepseek"])

    def test_custom_openai_compatible_endpoint(self):
        args = self.parser().parse_args([
            "--base-url", "https://example.test/v1",
            "--api-key-env", "EXAMPLE_KEY",
        ])
        config = resolve_provider(args)
        self.assertEqual(config.base_url, "https://example.test/v1")
        self.assertEqual(config.api_key_env, "EXAMPLE_KEY")


if __name__ == "__main__":
    unittest.main()
