"""Drives a single election run for either algorithm.

A run creates N independent threads (one per ALIVE node), wires them
together by per-node queues, fires a TRIGGER at the chosen initiator,
waits for every alive node to learn the new leader, and returns the
populated MetricsCollector.
"""

from __future__ import annotations

import queue
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from app.bully import BullyNode
from app.metrics import MetricsCollector
from app.node import Message
from app.ring import RingNode

DEFAULT_N = 10
DEFAULT_FAILED: Sequence[int] = (10,)


def _build_queues(n_nodes: int) -> Dict[int, "queue.Queue[Message]"]:
    return {i: queue.Queue() for i in range(1, n_nodes + 1)}


def run_bully(
    initiator_id: int,
    n_nodes: int = DEFAULT_N,
    failed_nodes: Sequence[int] = DEFAULT_FAILED,
    log_file: Optional[Path] = None,
    run_label: str = "Bully",
    join_timeout_s: float = 30.0,
) -> MetricsCollector:
    queues = _build_queues(n_nodes)
    metrics = MetricsCollector(log_file=log_file, run_label=run_label)

    nodes: List[BullyNode] = []
    for i in range(1, n_nodes + 1):
        if i in failed_nodes:
            continue
        nodes.append(BullyNode(i, queues, metrics))

    metrics.start()
    for f in failed_nodes:
        metrics.record_event(f, "(node is DOWN -- not participating)")
    for n in nodes:
        n.start()

    queues[initiator_id].put(
        Message(type="TRIGGER", sender=0, receiver=initiator_id, hop=0)
    )

    deadline = time.perf_counter() + join_timeout_s
    for n in nodes:
        remaining = max(0.01, deadline - time.perf_counter())
        n.join(timeout=remaining)

    metrics.stop()
    return metrics


def run_ring(
    initiator_id: int,
    n_nodes: int = DEFAULT_N,
    failed_nodes: Sequence[int] = DEFAULT_FAILED,
    log_file: Optional[Path] = None,
    run_label: str = "Ring",
    join_timeout_s: float = 30.0,
) -> MetricsCollector:
    queues = _build_queues(n_nodes)
    metrics = MetricsCollector(log_file=log_file, run_label=run_label)

    alive_ids = [i for i in range(1, n_nodes + 1) if i not in failed_nodes]
    ring_order = sorted(alive_ids)  # natural ID order, dead nodes skipped

    nodes: List[RingNode] = []
    for i in range(1, n_nodes + 1):
        if i in failed_nodes:
            continue
        nodes.append(RingNode(i, queues, metrics, ring_order=ring_order))

    metrics.start()
    for f in failed_nodes:
        metrics.record_event(f, "(node is DOWN -- not participating)")
    for n in nodes:
        n.start()

    queues[initiator_id].put(
        Message(type="TRIGGER", sender=0, receiver=initiator_id, hop=0)
    )

    deadline = time.perf_counter() + join_timeout_s
    for n in nodes:
        remaining = max(0.01, deadline - time.perf_counter())
        n.join(timeout=remaining)

    metrics.stop()
    return metrics
