# ADR-001: Simple Transactional Core + Safety Boundary

## Status

Accepted

## Context

The assignment allows different technology choices and
explicitly values simple architecture.

## Decision

Use:

- Python
- SQLite

Keep these logical components separate:

- Pacing Engine
- Safety Controller
- Call Allocator
- Telecom Provider
- Event Handler

## Why SQLite?

The prototype needs:

- durable state
- transactions
- atomic updates
- simple local setup

SQLite provides these without requiring:

- Redis
- Kafka
- RabbitMQ
- Kubernetes

## Advantages

- Easy to run
- Easy to test
- Easy to inspect
- Transaction support
- Atomic reservation

## Disadvantages

SQLite will eventually become a bottleneck because of:

- write contention
- limited horizontal scaling
- limited multi-region capability

## Future architecture

At larger scale:

- distributed transactional database
- campaign partitioning
- worker sharding
- provider event stream
- outbox pattern
- provider health monitoring

The logical Safety Controller boundary remains unchanged.
