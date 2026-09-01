from __future__ import annotations

from dataclasses import dataclass

from .pacing import PacingMetrics
from .repository import Repository


@dataclass(frozen=True)
class SafetyDecision:

    requested: int
    approved: int
    reason: str

    fallback_progressive: bool = False


class SafetyController:

    """
    The only component that authorizes outbound dialing.

    Predictive pacing cannot bypass this controller.
    """

    def __init__(
        self,
        repo: Repository,
        max_answer_exposure: float = 0.90,
    ):

        self.repo = repo

        self.max_answer_exposure = (
            max_answer_exposure
        )

    def authorize(
        self,
        requested: int,
        metrics: PacingMetrics,
        progressive: bool = False,
    ) -> SafetyDecision:

        counts = self.repo.counts()

        free = counts[
            "agents_available"
        ]

        # No capacity
        if (
            requested <= 0
            or free <= 0
        ):

            return SafetyDecision(
                requested,
                0,
                "no agent capacity",
            )

        # Provider degraded
        if (
            metrics.provider_health
            < 0.30
        ):

            approved = min(
                free,
                1 if progressive else 0,
            )

            return SafetyDecision(
                requested,
                approved,
                "provider health below safety threshold",
                progressive,
            )

        p = max(
            0.01,
            min(
                1.0,
                metrics.recent_answer_rate
                if metrics.recent_answer_rate
                is not None
                else metrics.answer_rate,
            ),
        )

        # Independent safety capacity
        safe = int(
            free
            * self.max_answer_exposure
        )

        approved = min(
            requested,
            safe,
        )

        # If answer rate is extremely high,
        # become more conservative.
        if p > 0.80:

            approved = min(
                approved,
                max(
                    0,
                    int(free * 0.60),
                ),
            )

        return SafetyDecision(
            requested,
            approved,
            "approved within live agent capacity and safety limits",
            False,
        )
