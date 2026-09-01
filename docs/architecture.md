# SmartDialer Architecture

## Goal

Get the utilization benefits of predictive dialing while
preserving the deterministic safety characteristics of
progressive dialing.

## Request flow

Campaign
    ↓
Pacing Engine
    ↓
Safety Controller
    ↓
Call Allocator
    ↓
Telecom Provider

## Pacing Engine

Two modes are supported.

### Progressive

Requests only according to currently available agents.

### Predictive

Uses:

- available agents
- active calls
- answer rate
- average talk time
- provider health
- safety margin

The predictive engine only makes a recommendation.

It cannot directly contact the telecom provider.

## Safety Controller

The Safety Controller is an independent hard boundary.

It can:

- approve
- reduce
- reject
- fallback to progressive

## Call Allocator

The allocator:

1. reserves an agent
2. reserves a borrower
3. creates the call
4. initiates provider call
5. handles provider events

A provider call cannot happen without an agent reservation.

## Database

SQLite is the source of truth.

It stores:

- agents
- borrowers
- calls
- provider events

## Concurrency

Agent reservation uses an atomic state condition:

UPDATE agents
SET state='RESERVED'
WHERE id=? AND state='AVAILABLE';

Therefore two workers cannot reserve the same agent.

## Provider events

Provider events are idempotent using event IDs.

Out-of-order events are rejected using monotonic
call-state progression.

## Recovery

Reservations have leases.

A recovery process finds expired calls and:

- marks the call CANCELLED
- releases the borrower
- releases the agent

## Scaling

At 100 agents SQLite is sufficient for this prototype.

At 1,000+ agents:

- reservation contention
- provider callbacks
- event processing

become larger concerns.

At 10,000+ agents the database becomes the major bottleneck.

The logical architecture can remain the same while
replacing the storage/event infrastructure.
