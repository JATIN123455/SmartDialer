from __future__ import annotations

import argparse

from .allocator import CallAllocator
from .engine import SmartDialer
from .providers import (
    ProviderA,
    ProviderB,
)
from .repository import Repository


def main():

    parser = argparse.ArgumentParser(
        description="SmartDialer functional prototype"
    )

    parser.add_argument(
        "--mode",
        choices=[
            "progressive",
            "predictive",
        ],
        default="predictive",
    )

    parser.add_argument(
        "--agents",
        type=int,
        default=10,
    )

    parser.add_argument(
        "--borrowers",
        type=int,
        default=100,
    )

    parser.add_argument(
        "--provider",
        choices=["a", "b"],
        default="a",
    )

    args = parser.parse_args()

    repo = Repository(
        "smartdialer.db"
    )

    repo.add_agents(
        [
            f"agent-{i}"
            for i in range(args.agents)
        ]
    )

    repo.add_borrowers(
        [
            (
                f"borrower-{i}",
                f"+9100000{i:05d}",
            )
            for i in range(args.borrowers)
        ]
    )

    provider = (
        ProviderA()
        if args.provider == "a"
        else ProviderB()
    )

    allocator = CallAllocator(
        repo,
        provider,
    )

    dialer = SmartDialer(
        repo,
        allocator,
        args.mode,
    )

    for i in range(5):

        print(
            f"tick {i + 1}: "
            f"{dialer.tick()}"
        )

    print(
        "counts:",
        repo.counts(),
    )


if __name__ == "__main__":
    main()
