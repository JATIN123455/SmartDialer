# SmartDialer
Safety-first Progressive and Predictive Smart Dialer prototype with pacing, safety controls, concurrency handling, mock telecom providers, recovery, tests, simulation, and load testing.
# SmartDialer

Safety-first Progressive and Predictive Dialer prototype.

## Features

- Progressive Dialer
- Predictive Pacing Engine
- Safety Controller
- Atomic agent reservation
- Atomic borrower reservation
- Duplicate event handling
- Out-of-order event handling
- Worker crash recovery
- Provider outage handling
- Mock Provider A
- Mock Provider B
- Simulation
- Load test
- Unit tests

## Architecture

Campaign
    ↓
Pacing Engine
    ↓
Safety Controller
    ↓
Call Allocator
    ↓
Telecom Provider

## Requirements

Python 3.11+
Run tests
python -m unittest discover -s tests -v
Progressive mode
PYTHONPATH=src python -m smartdialer.cli \
    --mode progressive \
    --agents 10 \
    --borrowers 100
Predictive mode
PYTHONPATH=src python -m smartdialer.cli \
    --mode predictive \
    --agents 10 \
    --borrowers 100
Provider B
PYTHONPATH=src python -m smartdialer.cli \
    --mode predictive \
    --provider b
Simulation
PYTHONPATH=src python -m smartdialer.simulation
Load test
python load_test.py

## Installation
```bash
pip install -e .

