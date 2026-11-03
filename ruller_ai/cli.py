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
    parser = argparse.ArgumentParser(description="Ruller AI — offline-first Python assistant prototype")
    parser.add_argument("--data-dir", type=Path, help="Directory for local memory and knowledge files")
    args = parser.parse_args()
    settings = Settings(data_dir=args.data_dir.expanduser()) if args.data_dir else Settings()
    assistant = RullerAI(settings)
    print("Ruller AI ready. Type /help for commands, /exit to quit.")
    while True:
        try:
            message = input("You> ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return 0
        if message.strip().casefold() in {"/exit", "exit", "quit"}:
            print("Goodbye.")
            return 0
        print(f"Ruller> {assistant.chat(message)}")


if __name__ == "__main__":
    raise SystemExit(main())
