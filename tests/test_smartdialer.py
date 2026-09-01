import sys
import threading
import time
import unittest

sys.path.insert(0, "src")

from smartdialer.allocator import (
    CallAllocator,
)
from smartdialer.engine import (
    SmartDialer,
)
from smartdialer.models import (
    AgentState,
    CallState,
)
from smartdialer.pacing import (
    PacingMetrics,
)
from smartdialer.providers import (
    ProviderA,
)
from smartdialer.repository import (
    Repository,
)
from smartdialer.safety import (
    SafetyController,
)


class SmartDialerTests(unittest.TestCase):

    def setup_repo(
        self,
        agents=2,
        borrowers=10,
    ):

        repo = Repository()

        repo.add_agents(
            [
                f"a{i}"
                for i in range(agents)
            ]
        )

        repo.add_borrowers(
            [
                (
                    f"b{i}",
                    f"+91{i}",
                )
                for i in range(borrowers)
            ]
        )

        return repo

    # ------------------------------------------
    # CONCURRENCY
    # ------------------------------------------

    def test_two_workers_cannot_reserve_same_agent(
        self,
    ):

        repo = self.setup_repo(
            agents=1
        )

        results = []

        barrier = threading.Barrier(
            2
        )

        def worker(i):

            barrier.wait()

            results.append(
                repo.reserve_agent(
                    f"worker-{i}"
                )
            )

        threads = [
            threading.Thread(
                target=worker,
                args=(i,),
            )
            for i in range(2)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        self.assertEqual(
            sum(
                result is not None
                for result in results
            ),
            1,
        )

    # ------------------------------------------
    # PROGRESSIVE
    # ------------------------------------------

    def test_progressive_never_starts_more_than_available_agents(
        self,
    ):

        repo = self.setup_repo(
            agents=3,
            borrowers=10,
        )

        dialer = SmartDialer(
            repo,
            CallAllocator(
                repo,
                ProviderA(),
            ),
            "progressive",
        )

        result = dialer.tick()

        self.assertLessEqual(
            result["started"],
            3,
        )

    # ------------------------------------------
    # DUPLICATE / OUT OF ORDER
    # ------------------------------------------

    def test_duplicate_and_out_of_order_events_are_safe(
        self,
    ):

        repo = self.setup_repo(
            agents=1
        )

        agent = repo.reserve_agent(
            "worker"
        )

        repo.reserve_borrower(
            "b0",
            "c1",
        )

        repo.create_call(
            "c1",
            "b0",
            agent.id,
        )

        allocator = CallAllocator(
            repo,
            ProviderA(),
        )

        allocator.apply_event(
            "c1",
            "ANSWERED",
        )

        allocator.apply_event(
            "c1",
            "ANSWERED",
        )

        allocator.apply_event(
            "c1",
            "RINGING",
        )

        self.assertEqual(
            repo.get_call("c1").state,
            CallState.ANSWERED,
        )

        allocator.apply_event(
            "c1",
            "COMPLETED",
        )

        allocator.apply_event(
            "c1",
            "RINGING",
        )

        self.assertEqual(
            repo.get_call("c1").state,
            CallState.COMPLETED,
        )

    # ------------------------------------------
    # WORKER CRASH / RECOVERY
    # ------------------------------------------

    def test_recovery_releases_expired_reservation(
        self,
    ):

        repo = self.setup_repo(
            agents=1
        )

        agent = repo.reserve_agent(
            "worker",
            lease_seconds=-1,
        )

        repo.reserve_borrower(
            "b0",
            "c1",
        )

        repo.create_call(
            "c1",
            "b0",
            agent.id,
            now=time.time() - 20,
            lease_seconds=-1,
        )

        recovered = (
            repo.recover_expired()
        )

        self.assertEqual(
            recovered,
            ["c1"],
        )

        self.assertEqual(
            repo.get_call("c1").state,
            CallState.CANCELLED,
        )

        self.assertEqual(
            repo.list_agents()[0].state,
            AgentState.AVAILABLE,
        )

    # ------------------------------------------
    # PROVIDER OUTAGE
    # ------------------------------------------

    def test_safety_rejects_predictive_when_provider_is_bad(
        self,
    ):

        repo = self.setup_repo(
            agents=5
        )

        safety = SafetyController(
            repo
        )

        decision = safety.authorize(
            10,
            PacingMetrics(
                provider_health=0.1
            ),
            progressive=False,
        )

        self.assertEqual(
            decision.approved,
            0,
        )


if __name__ == "__main__":
    unittest.main()
