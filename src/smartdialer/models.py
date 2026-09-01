
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class AgentState(str, Enum):
    OFFLINE = "OFFLINE"
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    DIALING = "DIALING"
    CONNECTED = "CONNECTED"
    WRAP_UP = "WRAP_UP"
    PAUSED = "PAUSED"


class CallState(str, Enum):
    QUEUED = "QUEUED"
    RESERVED = "RESERVED"
    INITIATED = "INITIATED"
    RINGING = "RINGING"
    ANSWERED = "ANSWERED"
    CONNECTED = "CONNECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class Agent:
    id: str
    state: AgentState
    lease_until: float | None = None


@dataclass(frozen=True)
class Borrower:
    id: str
    phone: str
    reserved_by: str | None = None


@dataclass(frozen=True)
class Call:
    id: str
    borrower_id: str
    agent_id: str | None
    state: CallState
    created_at: float
    updated_at: float
    lease_until: float | None = None
    provider_call_id: str | None = None
    attempt: int = 0


@dataclass(frozen=True)
class ProviderEvent:
    provider_call_id: str
    event_id: str
    event: str
    at: float


TERMINAL_CALL_STATES = {
    CallState.COMPLETED,
    CallState.FAILED,
    CallState.CANCELLED,
}


# Used to prevent old/out-of-order events
# from moving a call backwards.
CALL_PROGRESS = {
    CallState.QUEUED: 0,
    CallState.RESERVED: 1,
    CallState.INITIATED: 2,
    CallState.RINGING: 3,
    CallState.ANSWERED: 4,
    CallState.CONNECTED: 5,
    CallState.COMPLETED: 6,
    CallState.FAILED: 6,
    CallState.CANCELLED: 6,
}


def as_dict(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "__dataclass_fields__"):
        return {
            k: getattr(obj, k)
            for k in obj.__dataclass_fields__
        }

    return dict(obj)
