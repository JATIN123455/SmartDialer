from __future__ import annotations

import time

from .allocator import CallAllocator
from .pacing import (
    PacingMetrics,
    PredictivePacingEngine,
    ProgressivePacingEngine,
)
from .repository import Repository
from .safety import SafetyController


class SmartDialer:

    def __init__(
        self,
        repo: Repository,
        allocator: CallAllocator,
        mode: str = "predictive",
    ):

        self.repo = repo
        self.allocator = allocator
        self.mode = mode

        self.safety = SafetyController(
            repo
        )

        self.predictive = (
            PredictivePacingEngine()
        )

        self.progressive = (
            ProgressivePacingEngine()
        )

        self.metrics = PacingMetrics()

    def tick(
        self,
        worker_id: str = "worker-1",
    ) -> dict:

        counts = self.repo.counts()

        # ----------------------------
        # PACING
        # ----------------------------

        if self.mode == "progressive":

            requested = (
                self.progressive.recommend(
                    counts[
                        "agents_available"
                    ]
                )
            )

        else:

            requested = (
                self.predictive.recommend(
                    counts[
                        "agents_available"
                    ],
                    counts[
                        "calls_active"
                    ],
                    self.metrics,
                )
            )

        # ----------------------------
        # SAFETY
        # ----------------------------

        decision = (
            self.safety.authorize(
                requested,
                self.metrics,
                progressive=(
                    self.mode
                    == "progressive"
                ),
            )
        )

        # ----------------------------
        # ALLOCATION
        # ----------------------------

        started = 0

        for _ in range(
            decision.approved
        ):

            borrowers = (
                self.repo.available_borrowers()
            )

            if not borrowers:
                break

            borrower = borrowers[0]

            call_id = (
                self.allocator.allocate_one(
                    borrower,
                    worker_id,
                )
            )

            if call_id:
                started += 1

        return {
            "requested": requested,
            "approved": decision.approved,
            "started": started,
            "reason": decision.reason,
        }

    def recover(self):

        return self.repo.recover_expired(
            time.time()
        )
