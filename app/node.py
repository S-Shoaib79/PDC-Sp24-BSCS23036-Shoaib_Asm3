"""Base Node class for the leader-election simulation.

Each Node is a `threading.Thread` running its own message loop. Nodes
communicate ONLY by pushing `Message` objects onto each other's queues
(no shared mutable state, no global variables for algorithm data --
satisfies the assignment's "No Shared Memory" constraint).

The send() method injects a 50 ms WAN-latency sleep BEFORE delivery, as
required by section 3 of the assignment spec.
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

SEND_DELAY_S: float = 0.050  # 50 ms WAN latency simulation


@dataclass
class Message:
    type: str           # 'TRIGGER' | 'ELECTION' | 'OK' | 'COORDINATOR' | 'STOP'
    sender: int
    receiver: int
    payload: Any = None
    hop: int = 0        # causal depth assigned by sender


class Node(threading.Thread):
    """Base node providing message I/O, hop bookkeeping, and metrics hooks.

    Subclasses (BullyNode, RingNode) implement `_handle(msg)`.
    """

    POLL_INTERVAL_S = 0.05

    def __init__(
        self,
        node_id: int,
        queues: Dict[int, "queue.Queue[Message]"],
        metrics,
        alive: bool = True,
        name: Optional[str] = None,
    ) -> None:
        super().__init__(daemon=True, name=name or f"Node-{node_id}")
        self.id = node_id
        self.queues = queues
        self.in_q = queues[node_id]
        self.metrics = metrics
        self.alive = alive
        self.leader: Optional[int] = None
        self.stopped = threading.Event()

    # ------------------------------------------------------------------ #
    # Messaging
    # ------------------------------------------------------------------ #
    def send(self, msg_type: str, receiver: int, payload: Any = None, hop: int = 1) -> None:
        """Send a message to `receiver`. Blocks SEND_DELAY_S to simulate WAN.

        Failed-node queues exist but have no consumer; sending to them counts
        as a network message (it went "on the wire") but produces no reply.
        """
        msg = Message(
            type=msg_type, sender=self.id, receiver=receiver, payload=payload, hop=hop
        )
        time.sleep(SEND_DELAY_S)
        self.metrics.record_send(msg)
        try:
            self.queues[receiver].put(msg)
        except KeyError:
            pass  # unknown peer -- treat as a dropped packet

    def receive(self, timeout: Optional[float] = None) -> Optional[Message]:
        try:
            msg = self.in_q.get(timeout=timeout)
        except queue.Empty:
            return None
        self.metrics.record_recv(msg)
        return msg

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def stop(self) -> None:
        self.stopped.set()

    def run(self) -> None:  # pragma: no cover - replaced by subclasses if needed
        while not self.stopped.is_set():
            msg = self.receive(timeout=self.POLL_INTERVAL_S)
            if msg is None:
                continue
            if msg.type == "STOP":
                self.stop()
                return
            self._handle(msg)

    def _handle(self, msg: Message) -> None:  # pragma: no cover - subclass hook
        raise NotImplementedError
