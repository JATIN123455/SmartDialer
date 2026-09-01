from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Iterable

from .models import (
    Agent,
    AgentState,
    Borrower,
    Call,
    CallState,
)


class Repository:

    def __init__(self, path: str = ":memory:") -> None:

        self._lock = threading.RLock()

        self._uri = False

        if path == ":memory:":
            self.path = (
                f"file:smartdialer-{uuid.uuid4().hex}"
                "?mode=memory&cache=shared"
            )
            self._uri = True
        else:
            self.path = path
            Path(path).parent.mkdir(
                parents=True,
                exist_ok=True,
            )

        self._conn = sqlite3.connect(
            self.path,
            uri=self._uri,
            timeout=10,
            isolation_level=None,
            check_same_thread=False,
        )

        self._conn.row_factory = sqlite3.Row

        self._conn.execute(
            "PRAGMA busy_timeout=10000"
        )

        if not self._uri:
            self._conn.execute(
                "PRAGMA journal_mode=WAL"
            )
            self._conn.execute(
                "PRAGMA synchronous=NORMAL"
            )

        self.init_schema()

    def __del__(self):
        try:
            self._conn.close()
        except Exception:
            pass

    # --------------------------------------------------
    # DATABASE
    # --------------------------------------------------

    def init_schema(self):

        with self._lock:

            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS agents(
                    id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    lease_until REAL
                );

                CREATE TABLE IF NOT EXISTS borrowers(
                    id TEXT PRIMARY KEY,
                    phone TEXT NOT NULL,
                    reserved_by TEXT
                );

                CREATE TABLE IF NOT EXISTS calls(
                    id TEXT PRIMARY KEY,
                    borrower_id TEXT NOT NULL,
                    agent_id TEXT,
                    state TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    lease_until REAL,
                    provider_call_id TEXT,
                    attempt INTEGER NOT NULL DEFAULT 0
                );

                CREATE UNIQUE INDEX IF NOT EXISTS
                idx_provider_call_id
                ON calls(provider_call_id)
                WHERE provider_call_id IS NOT NULL;

                CREATE TABLE IF NOT EXISTS provider_events(
                    event_id TEXT PRIMARY KEY,
                    provider_call_id TEXT NOT NULL,
                    event TEXT NOT NULL,
                    received_at REAL NOT NULL
                );
                """
            )

    # --------------------------------------------------
    # SEED DATA
    # --------------------------------------------------

    def add_agents(
        self,
        ids: Iterable[str],
    ):

        with self._lock:

            self._conn.executemany(
                """
                INSERT OR IGNORE INTO agents(id,state)
                VALUES (?,?)
                """,
                [
                    (
                        agent_id,
                        AgentState.AVAILABLE.value,
                    )
                    for agent_id in ids
                ],
            )

    def add_borrowers(
        self,
        borrowers: Iterable[tuple[str, str]],
    ):

        with self._lock:

            self._conn.executemany(
                """
                INSERT OR IGNORE INTO borrowers(id,phone)
                VALUES (?,?)
                """,
                borrowers,
            )

    # --------------------------------------------------
    # COUNTERS
    # --------------------------------------------------

    def counts(self):

        with self._lock:

            agent_rows = self._conn.execute(
                """
                SELECT state, COUNT(*)
                FROM agents
                GROUP BY state
                """
            ).fetchall()

            call_rows = self._conn.execute(
                """
                SELECT state, COUNT(*)
                FROM calls
                GROUP BY state
                """
            ).fetchall()

            agents = {
                row[0]: row[1]
                for row in agent_rows
            }

            calls = {
                row[0]: row[1]
                for row in call_rows
            }

            active_states = [
                CallState.RESERVED,
                CallState.INITIATED,
                CallState.RINGING,
                CallState.ANSWERED,
                CallState.CONNECTED,
            ]

            return {
                "agents_available":
                    agents.get(
                        AgentState.AVAILABLE.value,
                        0,
                    ),

                "agents_reserved":
                    agents.get(
                        AgentState.RESERVED.value,
                        0,
                    ),

                "agents_dialing":
                    agents.get(
                        AgentState.DIALING.value,
                        0,
                    ),

                "agents_connected":
                    agents.get(
                        AgentState.CONNECTED.value,
                        0,
                    ),

                "calls_active":
                    sum(
                        calls.get(
                            state.value,
                            0,
                        )
                        for state in active_states
                    ),

                "calls_connected":
                    calls.get(
                        CallState.CONNECTED.value,
                        0,
                    ),

                "calls_answered_total":
                    self._conn.execute(
                        """
                        SELECT COUNT(*)
                        FROM provider_events
                        WHERE event='ANSWERED'
                        """
                    ).fetchone()[0],

                "calls_completed":
                    calls.get(
                        CallState.COMPLETED.value,
                        0,
                    ),

                "calls_failed":
                    calls.get(
                        CallState.FAILED.value,
                        0,
                    ),

                "calls_cancelled":
                    calls.get(
                        CallState.CANCELLED.value,
                        0,
                    ),
            }

    # --------------------------------------------------
    # ATOMIC AGENT RESERVATION
    # --------------------------------------------------

    def reserve_agent(
        self,
        worker_id: str,
        lease_seconds: float = 15.0,
    ) -> Agent | None:

        now = time.time()

        with self._lock:

            self._conn.execute(
                "BEGIN IMMEDIATE"
            )

            try:

                row = self._conn.execute(
                    """
                    SELECT id
                    FROM agents
                    WHERE state=?
                    ORDER BY id
                    LIMIT 1
                    """,
                    (
                        AgentState.AVAILABLE.value,
                    ),
                ).fetchone()

                if not row:

                    self._conn.execute(
                        "COMMIT"
                    )

                    return None

                agent_id = row["id"]

                updated = self._conn.execute(
                    """
                    UPDATE agents

                    SET state=?,
                        lease_until=?

                    WHERE id=?
                    AND state=?
                    """,
                    (
                        AgentState.RESERVED.value,
                        now + lease_seconds,
                        agent_id,
                        AgentState.AVAILABLE.value,
                    ),
                ).rowcount

                self._conn.execute(
                    "COMMIT"
                )

                if updated != 1:
                    return None

                return Agent(
                    agent_id,
                    AgentState.RESERVED,
                    now + lease_seconds,
                )

            except Exception:

                self._conn.execute(
                    "ROLLBACK"
                )

                raise

    # --------------------------------------------------
    # ATOMIC BORROWER RESERVATION
    # --------------------------------------------------

    def reserve_borrower(
        self,
        borrower_id: str,
        call_id: str,
    ) -> bool:

        with self._lock:

            updated = self._conn.execute(
                """
                UPDATE borrowers

                SET reserved_by=?

                WHERE id=?
                AND reserved_by IS NULL
                """,
                (
                    call_id,
                    borrower_id,
                ),
            ).rowcount

            return updated == 1

    # --------------------------------------------------
    # RELEASE
    # --------------------------------------------------

    def release_agent(
        self,
        agent_id: str,
    ):

        with self._lock:

            self._conn.execute(
                """
                UPDATE agents

                SET state=?,
                    lease_until=NULL

                WHERE id=?
                """,
                (
                    AgentState.AVAILABLE.value,
                    agent_id,
                ),
            )

    def release_borrower(
        self,
        borrower_id: str,
        call_id: str | None = None,
    ):

        with self._lock:

            if call_id:

                self._conn.execute(
                    """
                    UPDATE borrowers

                    SET reserved_by=NULL

                    WHERE id=?
                    AND reserved_by=?
                    """,
                    (
                        borrower_id,
                        call_id,
                    ),
                )

            else:

                self._conn.execute(
                    """
                    UPDATE borrowers

                    SET reserved_by=NULL

                    WHERE id=?
                    """,
                    (
                        borrower_id,
                    ),
                )

    # --------------------------------------------------
    # CALL CREATION
    # --------------------------------------------------

    def create_call(
        self,
        call_id: str,
        borrower_id: str,
        agent_id: str,
        now: float | None = None,
        lease_seconds: float = 15.0,
    ) -> Call:

        now = (
            time.time()
            if now is None
            else now
        )

        with self._lock:

            self._conn.execute(
                """
                INSERT INTO calls(
                    id,
                    borrower_id,
                    agent_id,
                    state,
                    created_at,
                    updated_at,
                    lease_until,
                    attempt
                )

                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, 1
                )
                """,
                (
                    call_id,
                    borrower_id,
                    agent_id,
                    CallState.RESERVED.value,
                    now,
                    now,
                    now + lease_seconds,
                ),
            )

            self._conn.execute(
                """
                UPDATE agents

                SET state=?,
                    lease_until=?

                WHERE id=?
                """,
                (
                    AgentState.DIALING.value,
                    now + lease_seconds,
                    agent_id,
                ),
            )

        return self.get_call(call_id)

    # --------------------------------------------------
    # PROVIDER CALL ID
    # --------------------------------------------------

    def set_provider_call_id(
        self,
        call_id: str,
        provider_call_id: str,
    ):

        with self._lock:

            self._conn.execute(
                """
                UPDATE calls

                SET provider_call_id=?,
                    state=?,
                    updated_at=?,
                    lease_until=NULL

                WHERE id=?
                """,
                (
                    provider_call_id,
                    CallState.INITIATED.value,
                    time.time(),
                    call_id,
                ),
            )

    # --------------------------------------------------
    # GET CALL
    # --------------------------------------------------

    def get_call(
        self,
        call_id: str,
    ) -> Call:

        with self._lock:

            row = self._conn.execute(
                """
                SELECT *
                FROM calls
                WHERE id=?
                """,
                (
                    call_id,
                ),
            ).fetchone()

        if not row:
            raise KeyError(call_id)

        return self._row_to_call(row)

    def get_call_by_provider_id(
        self,
        provider_call_id: str,
    ) -> Call | None:

        with self._lock:

            row = self._conn.execute(
                """
                SELECT *
                FROM calls

                WHERE provider_call_id=?
                """,
                (
                    provider_call_id,
                ),
            ).fetchone()

        if not row:
            return None

        return self._row_to_call(row)

    # --------------------------------------------------
    # STATE CHANGES
    # --------------------------------------------------

    def set_call_state(
        self,
        call_id: str,
        state: CallState,
    ):

        with self._lock:

            self._conn.execute(
                """
                UPDATE calls

                SET state=?,
                    updated_at=?,
                    lease_until=NULL

                WHERE id=?
                """,
                (
                    state.value,
                    time.time(),
                    call_id,
                ),
            )

    def set_agent_state(
        self,
        agent_id: str,
        state: AgentState,
    ):

        with self._lock:

            self._conn.execute(
                """
                UPDATE agents

                SET state=?,
                    lease_until=NULL

                WHERE id=?
                """,
                (
                    state.value,
                    agent_id,
                ),
            )

    # --------------------------------------------------
    # IDEMPOTENT PROVIDER EVENTS
    # --------------------------------------------------

    def record_event_once(
        self,
        event_id: str,
        provider_call_id: str,
        event: str,
    ) -> bool:

        with self._lock:

            inserted = self._conn.execute(
                """
                INSERT OR IGNORE INTO provider_events(
                    event_id,
                    provider_call_id,
                    event,
                    received_at
                )

                VALUES (?, ?, ?, ?)
                """,
                (
                    event_id,
                    provider_call_id,
                    event,
                    time.time(),
                ),
            ).rowcount

            return inserted == 1

    # --------------------------------------------------
    # CRASH RECOVERY
    # --------------------------------------------------

    def recover_expired(
        self,
        now: float | None = None,
    ) -> list[str]:

        now = (
            time.time()
            if now is None
            else now
        )

        with self._lock:

            rows = self._conn.execute(
                """
                SELECT
                    id,
                    borrower_id,
                    agent_id

                FROM calls

                WHERE lease_until IS NOT NULL
                AND lease_until < ?

                AND state IN (?, ?, ?)
                """,
                (
                    now,
                    CallState.RESERVED.value,
                    CallState.INITIATED.value,
                    CallState.RINGING.value,
                ),
            ).fetchall()

            recovered = []

            for row in rows:

                call_id = row["id"]

                self._conn.execute(
                    """
                    UPDATE calls

                    SET state=?,
                        updated_at=?,
                        lease_until=NULL

                    WHERE id=?
                    """,
                    (
                        CallState.CANCELLED.value,
                        now,
                        call_id,
                    ),
                )

                if row["agent_id"]:

                    self._conn.execute(
                        """
                        UPDATE agents

                        SET state=?,
                            lease_until=NULL

                        WHERE id=?
                        """,
                        (
                            AgentState.AVAILABLE.value,
                            row["agent_id"],
                        ),
                    )

                self._conn.execute(
                    """
                    UPDATE borrowers

                    SET reserved_by=NULL

                    WHERE id=?
                    AND reserved_by=?
                    """,
                    (
                        row["borrower_id"],
                        call_id,
                    ),
                )

                recovered.append(call_id)

            return recovered

    # --------------------------------------------------
    # AVAILABLE BORROWERS
    # --------------------------------------------------

    def available_borrowers(self):

        with self._lock:

            rows = self._conn.execute(
                """
                SELECT id

                FROM borrowers

                WHERE reserved_by IS NULL

                ORDER BY id
                """
            ).fetchall()

            return [
                row[0]
                for row in rows
            ]

    # --------------------------------------------------
    # LIST
    # --------------------------------------------------

    def list_agents(self):

        with self._lock:

            rows = self._conn.execute(
                """
                SELECT *
                FROM agents
                ORDER BY id
                """
            ).fetchall()

        return [
            Agent(
                row["id"],
                AgentState(row["state"]),
                row["lease_until"],
            )
            for row in rows
        ]

    def list_calls(self):

        with self._lock:

            rows = self._conn.execute(
                """
                SELECT *
                FROM calls
                ORDER BY created_at
                """
            ).fetchall()

        return [
            self._row_to_call(row)
            for row in rows
        ]

    @staticmethod
    def _row_to_call(
        row: sqlite3.Row,
    ) -> Call:

        return Call(
            row["id"],
            row["borrower_id"],
            row["agent_id"],
            CallState(row["state"]),
            row["created_at"],
            row["updated_at"],
            row["lease_until"],
            row["provider_call_id"],
            row["attempt"],
        )
