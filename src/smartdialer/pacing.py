from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PacingMetrics:

    answer_rate: float = 0.5

    avg_talk_seconds: float = 90.0

    avg_setup_seconds: float = 2.0

    provider_health: float = 1.0

    recent_answer_rate: float | None = None


class PredictivePacingEngine:

    """
    Rule-based predictive pacing.

    Prediction only recommends a number.
    It does NOT call the provider.
    """

    def __init__(
        self,
        safety_margin: float = 0.80,
        horizon_seconds: float = 15.0,
    ):

        self.safety_margin = safety_margin

        self.horizon_seconds = (
            horizon_seconds
        )

    def forecast_near_term_capacity(
        self,
        available_agents: int,
        active_calls: int,
        metrics: PacingMetrics,
    ) -> int:

        if available_agents <= 0:
            return 0

        turnover = max(
            0.0,
            min(
                1.0,
                self.horizon_seconds
                / max(
                    metrics.avg_talk_seconds,
                    1.0,
                ),
            ),
        )

        return int(
            active_calls * turnover
        )

    def recommend(
        self,
        available_agents: int,
        active_calls: int,
        metrics: PacingMetrics,
    ) -> int:

        if available_agents <= 0:
            return 0

        p = (
            metrics.recent_answer_rate
            if metrics.recent_answer_rate
            is not None
            else metrics.answer_rate
        )

        p = max(
            0.0,
            min(1.0, p),
        )

        health = max(
            0.1,
            min(
                1.0,
                metrics.provider_health,
            ),
        )

        # Conservative capacity
        safe_answer_capacity = max(
            0,
            int(
                available_agents
                * self.safety_margin
            ),
        )

        # Expected answers from current calls
        projected_answers = int(
            active_calls * p
        )

        # Remaining safe capacity
        headroom = max(
            0,
            safe_answer_capacity
            - projected_answers,
        )

        # Number of calls required
        desired = (
            int(
                headroom
                / max(p, 0.05)
            )
            if p > 0
            else safe_answer_capacity
        )

        # Avoid large sudden bursts
        burst_cap = max(
            1,
            min(
                20,
                available_agents,
            ),
        )

        return max(
            0,
            min(
                desired,
                burst_cap,
                int(
                    safe_answer_capacity
                    * health
                )
                + 1,
            ),
        )


class ProgressivePacingEngine:

    def recommend(
        self,
        available_agents: int,
        *_args,
        **_kwargs,
    ) -> int:

        return max(
            0,
            available_agents,
        )
