from __future__ import annotations

import random
import time
from dataclasses import dataclass

from .models import ProviderEvent


class TelecomProvider:

    name = "abstract"
    health = 1.0

    def dial(self, phone: str) -> str:
        raise NotImplementedError

    def drain_events(
        self,
        provider_call_id: str,
    ) -> list[ProviderEvent]:
        return []


@dataclass
class ProviderConfig:

    answer_rate: float
    setup_seconds: float
    talk_seconds: float
    failure_rate: float

    duplicate_events: bool = False
    out_of_order: bool = False


class MockProvider(TelecomProvider):

    def __init__(
        self,
        name: str,
        config: ProviderConfig,
        seed: int = 1,
    ):

        self.name = name
        self.config = config

        self.rng = random.Random(seed)

        self.health = (
            1.0 - config.failure_rate
        )

        self._seq = 0
        self._pending = {}

    def dial(self, phone: str) -> str:

        self._seq += 1

        provider_call_id = (
            f"{self.name}-{self._seq}"
        )

        now = time.time()

        # Provider failure
        if (
            self.rng.random()
            < self.config.failure_rate
        ):

            events = [
                ProviderEvent(
                    provider_call_id,
                    f"{provider_call_id}-failed",
                    "FAILED",
                    now,
                )
            ]

        else:

            answered = (
                self.rng.random()
                < self.config.answer_rate
            )

            names = ["RINGING"]

            if answered:

                names += [
                    "ANSWERED",
                    "CONNECTED",
                    "COMPLETED",
                ]

            else:

                names += [
                    "COMPLETED"
                ]

            # Create out-of-order events
            if (
                self.config.out_of_order
                and len(names) >= 4
            ):

                names[1], names[2] = (
                    names[2],
                    names[1],
                )

            events = [
                ProviderEvent(
                    provider_call_id,
                    f"{provider_call_id}-{i}",
                    event,
                    now
                    + self.config.setup_seconds
                    + i * self.config.talk_seconds,
                )
                for i, event in enumerate(names)
            ]

            # Duplicate events
            if self.config.duplicate_events:

                duplicated = []

                for event in events:

                    duplicated.append(event)

                    if event.event in {
                        "ANSWERED",
                        "COMPLETED",
                    }:

                        duplicated.append(event)

                events = duplicated

        self._pending[
            provider_call_id
        ] = events

        return provider_call_id

    def drain_events(
        self,
        provider_call_id: str,
    ):

        return self._pending.pop(
            provider_call_id,
            [],
        )


class ProviderA(MockProvider):

    def __init__(self, seed: int = 1):

        super().__init__(
            "provider-a",

            ProviderConfig(
                answer_rate=0.50,
                setup_seconds=0.05,
                talk_seconds=0.01,
                failure_rate=0.02,
            ),

            seed,
        )


class ProviderB(MockProvider):

    def __init__(self, seed: int = 2):

        super().__init__(
            "provider-b",

            ProviderConfig(
                answer_rate=0.50,
                setup_seconds=0.20,
                talk_seconds=0.02,
                failure_rate=0.15,
                duplicate_events=True,
                out_of_order=True,
            ),

            seed,
        )
