"""Ring (Chang-Roberts style) Leader Election.

Logical ring of alive nodes. The initiator sends ELECTION carrying its
own ID to the next alive neighbour. Each forwarder appends its own ID to
the payload list and forwards. When the initiator sees its ID back in
the payload, the message has gone full-circle: it picks max(ids) as the
new leader and starts a COORDINATOR message around the ring. The same
node stops the COORDINATOR cycle when it returns.
"""

from __future__ import annotations

import threading
from typing import List

from app.node import Message, Node


class RingNode(Node):
    def __init__(
        self,
        node_id: int,
        queues,
        metrics,
        ring_order: List[int],
        alive: bool = True,
        name=None,
    ) -> None:
        super().__init__(node_id, queues, metrics, alive, name)
        self.ring_order = ring_order  # list of ALIVE ids in ring order
        idx = self.ring_order.index(self.id)
        self.next_alive = self.ring_order[(idx + 1) % len(self.ring_order)]
        self.coord_initiator = False

    def run(self) -> None:
        while not self.stopped.is_set():
            msg = self.receive(timeout=self.POLL_INTERVAL_S)
            if msg is None:
                continue
            if msg.type == "STOP":
                self.stop()
                return
            self._handle(msg)

    def _handle(self, msg: Message) -> None:
        if msg.type == "TRIGGER":
            self.metrics.record_event(
                self.id,
                f"detects leader failure, starts Ring election -> next=N{self.next_alive}",
            )
            self.send("ELECTION", self.next_alive, payload=[self.id], hop=msg.hop + 1)

        elif msg.type == "ELECTION":
            ids: List[int] = list(msg.payload)
            next_hop = msg.hop + 1
            if self.id in ids:
                self.leader = max(ids)
                self.coord_initiator = True
                self.metrics.record_event(
                    self.id,
                    f"ELECTION returned full circle ids={ids}; new leader = N{self.leader}",
                )
                self.send(
                    "COORDINATOR",
                    self.next_alive,
                    payload=self.leader,
                    hop=next_hop,
                )
            else:
                ids.append(self.id)
                self.metrics.record_event(
                    self.id, f"forwards ELECTION {ids} -> N{self.next_alive}"
                )
                self.send("ELECTION", self.next_alive, payload=ids, hop=next_hop)

        elif msg.type == "COORDINATOR":
            new_leader = msg.payload
            next_hop = msg.hop + 1
            if self.coord_initiator:
                self.metrics.record_event(
                    self.id, "COORDINATOR returned full circle; Ring election complete"
                )
                self.stop()
            else:
                self.leader = new_leader
                self.metrics.record_event(
                    self.id, f"acknowledges leader = N{new_leader}, forwarding"
                )
                self.send(
                    "COORDINATOR",
                    self.next_alive,
                    payload=new_leader,
                    hop=next_hop,
                )
                self.stop()
