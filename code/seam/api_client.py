"""Shared configuration for OpenAI-compatible model providers."""

from __future__ import annotations

import os
from dataclasses import dataclass

from openai import OpenAI


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    api_key_env: str


PROVIDERS = {
    "openrouter": ProviderConfig(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
    ),
    "deepseek": ProviderConfig(
        name="deepseek",
        base_url="https://api.deepseek.com",
        api_key_env="DEEPSEEK_API_KEY",
    ),
}


def add_provider_arguments(parser, default_provider: str = "openrouter") -> None:
    parser.add_argument(
        "--provider", choices=sorted(PROVIDERS), default=default_provider,
        help=f"Named OpenAI-compatible provider (default: {default_provider}).",
    )
    parser.add_argument(
        "--base-url",
        help="Override the provider's OpenAI-compatible API base URL.",
    )
    parser.add_argument(
        "--api-key-env",
        help="Override the environment variable containing the API key.",
    )


def resolve_provider(args) -> ProviderConfig:
    preset = PROVIDERS[args.provider]
    return ProviderConfig(
        name=preset.name,
        base_url=args.base_url or preset.base_url,
        api_key_env=args.api_key_env or preset.api_key_env,
    )


def make_client(args) -> tuple[OpenAI, ProviderConfig]:
    config = resolve_provider(args)
    api_key = os.environ.get(config.api_key_env)
    if not api_key:
        raise SystemExit(f"{config.api_key_env} not set")
    return OpenAI(base_url=config.base_url, api_key=api_key), config
