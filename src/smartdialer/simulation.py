from __future__ import annotations

from .allocator import CallAllocator
from .engine import SmartDialer
from .pacing import PacingMetrics
from .providers import (
    MockProvider,
    ProviderConfig,
)
from .repository import Repository


def run_scenario(
    name: str,
    answer_rate: float,
    talk_seconds: float,
    provider_failures: float = 0.02,
    agents: int = 50,
    borrowers: int = 500,
    ticks: int = 20,
):

    repo = Repository()

    repo.add_agents(
        [
            f"a-{i}"
            for i in range(agents)
        ]
    )

    repo.add_borrowers(
        [
            (
                f"b-{i}",
                f"+9100000{i:04d}",
            )
            for i in range(borrowers)
        ]
    )

    provider = MockProvider(
        "scenario",

        ProviderConfig(
            answer_rate=answer_rate,
            setup_seconds=0.05,
            talk_seconds=talk_seconds,
            failure_rate=provider_failures,
        ),

        seed=42,
    )

    dialer = SmartDialer(
        repo,
        CallAllocator(
            repo,
            provider,
        ),
        "predictive",
    )

    dialer.metrics = PacingMetrics(
        answer_rate=answer_rate,
        avg_talk_seconds=talk_seconds,
        provider_health=(
            1 - provider_failures
        ),
    )

    rows = []

    for _ in range(ticks):

        rows.append(
            dialer.tick()
        )

    counts = repo.counts()

    return {
        "scenario": name,

        "answer_rate":
            answer_rate,

        "talk_sec":
            talk_seconds,

        "initiated":
            sum(
                row["started"]
                for row in rows
            ),

        "connected":
            counts[
                "calls_answered_total"
            ],

        "failed":
            counts[
                "calls_failed"
            ],

        "cancelled":
            counts[
                "calls_cancelled"
            ],

        "max_request":
            max(
                row["requested"]
                for row in rows
            ),

        "max_approved":
            max(
                row["approved"]
                for row in rows
            ),
    }


def main():

    scenarios = [

        ("A", 0.20, 120),

        ("B", 0.50, 90),

        ("C", 0.70, 180),

        (
            "D-provider-degraded",
            0.50,
            90,
            0.60,
        ),
    ]

    print(
        "Scenario | Answer | Talk | "
        "Initiated | Failed | Cancelled | "
        "Max request | Max approved"
    )

    print(
        "---------|--------|------|"
        "-----------|--------|-----------|"
        "--------------|-------------"
    )

    for scenario in scenarios:

        result = run_scenario(
            *scenario
        )

        print(
            f"{result['scenario']:8} | "
            f"{result['answer_rate']:.0%}   | "
            f"{result['talk_sec']:4.0f} | "
            f"{result['initiated']:9} | "
            f"{result['failed']:6} | "
            f"{result['cancelled']:9} | "
            f"{result['max_request']:12} | "
            f"{result['max_approved']:11}"
        )


if __name__ == "__main__":
    main()
