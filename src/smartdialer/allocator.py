from __future__ import annotations

import uuid

from .models import (
    AgentState,
    CallState,
    CALL_PROGRESS,
)
from .providers import TelecomProvider
from .repository import Repository


class CallAllocator:

    """
    Converts a Safety Controller approval
    into an actual provider call.
    """

    def __init__(
        self,
        repo: Repository,
        provider: TelecomProvider,
    ):

        self.repo = repo
        self.provider = provider

    def allocate_one(
        self,
        borrower_id: str,
        worker_id: str,
    ) -> str | None:

        call_id = str(
            uuid.uuid4()
        )

        # 1. Reserve agent
        agent = self.repo.reserve_agent(
            worker_id
        )

        if not agent:
            return None

        # 2. Reserve borrower
        if not self.repo.reserve_borrower(
            borrower_id,
            call_id,
        ):

            self.repo.release_agent(
                agent.id
            )

            return None

        try:

            # 3. Persist call
            self.repo.create_call(
                call_id,
                borrower_id,
                agent.id,
            )

            # 4. Only now contact provider
            provider_call_id = (
                self.provider.dial(
                    borrower_id
                )
            )

            # 5. Persist provider ID
            self.repo.set_provider_call_id(
                call_id,
                provider_call_id,
            )

            # 6. Process provider events
            events = (
                self.provider.drain_events(
                    provider_call_id
                )
            )

            for event in events:
                self._handle_provider_event(
                    event
                )

            return call_id

        except Exception:

            self.repo.release_borrower(
                borrower_id,
                call_id,
            )

            self.repo.release_agent(
                agent.id
            )

            try:
                self.repo.set_call_state(
                    call_id,
                    CallState.FAILED,
                )
            except KeyError:
                pass

            return None

    def _handle_provider_event(
        self,
        event,
    ):

        call = (
            self.repo.get_call_by_provider_id(
                event.provider_call_id
            )
        )

        if not call:
            return

        # Idempotency
        if not self.repo.record_event_once(
            event.event_id,
            event.provider_call_id,
            event.event,
        ):
            return

        self.apply_event(
            call.id,
            event.event,
        )

    def apply_event(
        self,
        call_id: str,
        event: str,
    ):

        call = self.repo.get_call(
            call_id
        )

        # Terminal states cannot change
        if call.state in {
            CallState.COMPLETED,
            CallState.FAILED,
            CallState.CANCELLED,
        }:
            return

        transitions = {

            "RINGING":
                CallState.RINGING,

            "ANSWERED":
                CallState.ANSWERED,

            "CONNECTED":
                CallState.CONNECTED,

            "COMPLETED":
                CallState.COMPLETED,

            "FAILED":
                CallState.FAILED,
        }

        target = transitions.get(
            event
        )

        if target is None:
            return

        # Out-of-order event protection
        if (
            CALL_PROGRESS[target]
            < CALL_PROGRESS[call.state]
        ):
            return

        self.repo.set_call_state(
            call_id,
            target,
        )

        if (
            target
            == CallState.CONNECTED
        ):

            if call.agent_id:

                self.repo.set_agent_state(
                    call.agent_id,
                    AgentState.CONNECTED,
                )

        elif target in {
            CallState.COMPLETED,
            CallState.FAILED,
        }:

            if call.agent_id:

                self.repo.set_agent_state(
                    call.agent_id,
                    AgentState.WRAP_UP,
                )

            self.repo.release_borrower(
                call.borrower_id,
                call.id,
            )

            if call.agent_id:

                self.repo.release_agent(
                    call.agent_id
                )
