# SmartDialer Assignment Submission

## Final Answer

I would make prediction a request, not an authority.

The architecture is:

Campaign
    ↓
Pacing Engine
    ↓
Safety Controller
    ↓
Call Allocator
    ↓
Telecom Provider

The predictive engine estimates how many calls are likely
to answer using:

- agent availability
- active calls
- answer rate
- average talk time
- provider health

However, it cannot directly place a call.

The Safety Controller independently checks live durable state.

It can:

- approve
- reduce
- reject
- fallback to progressive

Only after approval does the Call Allocator reserve:

1. an agent
2. a borrower

Only then does it initiate the provider call.

Agent reservation is atomic, so two workers cannot reserve
the same agent.

Provider events are idempotent using event IDs.

Out-of-order events cannot move a call backwards.

Worker crashes are handled using leases and recovery.

Provider outages reduce or stop new dialing instead of
creating retry storms.

The predictive model is intentionally rule-based because
the main objective is correctness and safety rather than
complex ML.

The key invariant is:

active agent-bound outbound calls
<= usable agents

Therefore predictive dialing can improve utilization while
the Safety Controller retains deterministic protection.
