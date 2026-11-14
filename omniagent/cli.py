"""Command-line interface for OmniAgent Studio."""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import Settings
from .providers import ProviderManager
from .router import RequestRouter
from .session_store import SessionStore
from .plugins import PluginRegistry


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OmniAgent Studio — a local-first AI orchestration platform")
    parser.add_argument("--data-dir", type=Path, default=Path.home() / ".omniagent", help="Directory for local session and plugin data")
    parser.add_argument("--provider", choices=["offline", "ollama", "openai"], default="offline", help="Model backend selection")
    parser.add_argument("--model", default="local-default", help="Model or deployment name")
    parser.add_argument("--api-base", default=None, help="Custom API base URL for OpenAI-compatible backends")
    parser.add_argument("--api-key", default=None, help="Optional API key for hosted providers")
    parser.add_argument("--chat", help="Open a single-turn chat prompt")
    parser.add_argument("--status", action="store_true", help="Display the current OmniAgent status")
    parser.add_argument("--skills", action="store_true", help="List the registered skills")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    settings = Settings(
        data_dir=args.data_dir,
        provider=args.provider,
        model=args.model,
        api_base=args.api_base,
        api_key=args.api_key,
    )
    settings.ensure_directories()

    store = SessionStore(settings.sqlite_path)
    registry = PluginRegistry()
    router = RequestRouter()
    provider = ProviderManager(settings).create()

    if args.status:
        print(f"Project: {settings.project_name}")
        print(f"Provider: {settings.provider}")
        print(f"Model: {settings.model}")
        print(f"Data directory: {settings.data_dir}")
        print(f"SQLite DB: {settings.sqlite_path}")
        print(f"Local-only mode: {'yes' if settings.local_only else 'no'}")
        return 0

    if args.skills:
        for skill in registry.list_skills():
            print(f"- {skill.name} [{skill.category}]: {skill.description}")
        return 0

    if args.chat:
        decision = router.route(args.chat)
        response = provider.generate(args.chat, system_prompt="You are OmniAgent Studio. Keep answers short, clear, and privacy-aware.")
        print(f"Route: {decision.route} | confidence={decision.confidence:.2f}")
        print(response)
        return 0

    print("OmniAgent Studio ready. Use --chat 'your prompt', --status, or --skills.")
    print("Tip: The project is local-first by default and uses opt-in cloud providers.")
    return 0
