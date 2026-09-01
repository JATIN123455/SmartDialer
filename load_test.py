import sys
import time

from concurrent.futures import (
    ThreadPoolExecutor,
)

sys.path.insert(0, "src")

from smartdialer.allocator import (
    CallAllocator,
)
from smartdialer.repository import (
    Repository,
)


class HoldProvider:

    name = "hold-provider"
    health = 1.0

    def __init__(self):

        self.i = 0

    def dial(self, phone):

        self.i += 1

        return (
            f"hold-{self.i}"
        )

    def drain_events(
        self,
        provider_call_id,
    ):

        return []


repo = Repository()

TOTAL_ATTEMPTS = 1000

AGENTS = 100

repo.add_agents(
    [
        f"a-{i}"
        for i in range(AGENTS)
    ]
)

repo.add_borrowers(
    [
        (
            f"b-{i}",
            f"+910{i:07d}",
        )
        for i in range(
            TOTAL_ATTEMPTS
        )
    ]
)

allocator = CallAllocator(
    repo,
    HoldProvider(),
)


def worker(i):

    return allocator.allocate_one(
        f"b-{i}",
        f"worker-{i % 20}",
    )


start = time.perf_counter()

with ThreadPoolExecutor(
    max_workers=20
) as executor:

    results = list(
        executor.map(
            worker,
            range(TOTAL_ATTEMPTS),
        )
    )

elapsed = (
    time.perf_counter()
    - start
)

counts = repo.counts()

started = sum(
    result is not None
    for result in results
)

print(
    {
        "elapsed_sec":
            round(elapsed, 3),

        "attempted":
            TOTAL_ATTEMPTS,

        "started":
            started,

        "available_agents":
            counts[
                "agents_available"
            ],

        "active_calls":
            counts[
                "calls_active"
            ],
    }
)

print(
    "Invariant: active calls <= agents =",
    counts["calls_active"]
    <= AGENTS,
)
