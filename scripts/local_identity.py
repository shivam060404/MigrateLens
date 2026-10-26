"""Issue short lived local development tokens after explicit key initialization."""

import argparse

from src.config.paths import ROOT
from src.config.settings import Settings
from src.infrastructure.identity.local_emulator import LocalIdentityEmulator


def main():
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("init")
    token = subcommands.add_parser("token")
    token.add_argument("--subject", required=True)
    args = parser.parse_args()
    settings = Settings()
    emulator = LocalIdentityEmulator(ROOT / ".local/identity", environment=settings.environment)
    if args.command == "init":
        print(emulator.initialize())
    else:
        print(emulator.issue(args.subject))


if __name__ == "__main__":
    main()
