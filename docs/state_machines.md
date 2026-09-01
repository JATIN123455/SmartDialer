# State Machines

## Agent State Machine

OFFLINE
   |
   v
AVAILABLE
   |
   v
RESERVED
   |
   v
DIALING
   |
   v
CONNECTED
   |
   v
WRAP_UP
   |
   v
AVAILABLE

AVAILABLE <----> PAUSED

## Call State Machine

QUEUED
   |
   v
RESERVED
   |
   v
INITIATED
   |
   v
RINGING
   |
   v
ANSWERED
   |
   v
CONNECTED
   |
   v
COMPLETED

Failure path:

QUEUED
RESERVED
INITIATED
RINGING
    |
    v
FAILED

Cancellation:

QUEUED
RESERVED
INITIATED
RINGING
    |
    v
CANCELLED

Rules:

1. Terminal states cannot move backwards.
2. Duplicate events are ignored.
3. Out-of-order events cannot regress state.
4. Leases allow worker crash recovery.
