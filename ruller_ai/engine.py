"""Interactive command-line interface."""
import argparse
from pathlib import Path

if not __package__:
    raise SystemExit(
        "Run the CLI as a package from the repository root: "
        "python -m ruller_ai"
    )

from .config import Settings
from .engine import RullerAI


def main() -> int:
    parser = argparse.ArgumentParser(description="ULTRON — local memory + optional real AI model backend")
    parser.add_argument("--data-dir", type=Path, help="Directory for local memory and knowledge files")
    parser.add_argument("--provider", choices=["offline", "ollama", "openai"], help="Model backend to use")
    parser.add_argument("--model", help="Model name for the selected provider")
    parser.add_argument("--api-base", help="Custom API base URL for OpenAI-compatible endpoints")
    parser.add_argument("--api-key", help="API key for OpenAI-compatible providers")
    args = parser.parse_args()

    settings = Settings(
        data_dir=args.data_dir.expanduser() if args.data_dir else Settings().data_dir,
        provider=args.provider,
        model=args.model,
        api_base=args.api_base,
        api_key=args.api_key,
    )
    assistant = RullerAI(settings)
    print("ULTRON ready. Type /help for commands, /exit to quit.")
    while True:
        try:
            message = input("You> ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return 0
        if message.strip().casefold() in {"/exit", "exit", "quit"}:
            print("Goodbye.")
            return 0
        print(f"ULTRON> {assistant.chat(message)}")


if __name__ == "__main__":
    raise SystemExit(main())
