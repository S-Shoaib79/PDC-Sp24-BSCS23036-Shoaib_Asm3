"""Bully Algorithm 

Node detects the failure -> sends ELECTION to every higher-ID peer.
    * If any higher peer answers OK, the initiator gives up its claim and
      waits for a COORDINATOR announcement from somebody bigger.
    * If no OK arrives within OK_TIMEOUT_S, the initiator declares itself
      the new coordinator and broadcasts COORDINATOR to every other node.

Every node receiving ELECTION from a lower peer replies OK and starts its
own election (the recursion is bounded because a node only starts ONE
election round per failure event -- see `in_election` guard).
"""

from __future__ import annotations

import threading
import time
from typing import List

from app.node import Message, Node

# Conservative timeout: must exceed the worst-case round-trip *including* the
# time a higher-ID node may spend draining a queue of cascaded ELECTIONs.
# For N=10 with 50 ms send delay this round-trip can hit ~900 ms, so 1.5 s is
# safe and matches the textbook "wait long enough that only the highest-alive
# node ever times out" rule.
OK_TIMEOUT_S: float = 1.5


class BullyNode(Node):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._election_lock = threading.Lock()
        self.in_election = False
        self.received_ok = False
        self.coord_received = threading.Event()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def run(self) -> None:
        while not self.stopped.is_set():
            msg = self.receive(timeout=self.POLL_INTERVAL_S)
            if msg is None:
                continue
            if msg.type == "STOP":
                self.stop()
                return
            self._handle(msg)

    # ------------------------------------------------------------------ #
    # Handlers
    # ------------------------------------------------------------------ #
    def _handle(self, msg: Message) -> None:
        if msg.type == "TRIGGER":
            self.metrics.record_event(self.id, "detects leader failure, starting Bully election")
            self._start_election(start_hop=msg.hop + 1)

        elif msg.type == "ELECTION":
            response_hop = msg.hop + 1
            self.send("OK", msg.sender, hop=response_hop)
            self.metrics.record_event(
                self.id, f"replies OK to N{msg.sender} (its ID {msg.sender} < mine {self.id})"
            )
            self._start_election(start_hop=response_hop)

        elif msg.type == "OK":
            self.received_ok = True
            self.metrics.record_event(
                self.id, f"received OK from N{msg.sender}; will await COORDINATOR"
            )

        elif msg.type == "COORDINATOR":
            self.leader = msg.payload
            self.metrics.record_event(self.id, f"acknowledges new leader = N{self.leader}")
            self.coord_received.set()
            self.stop()

    # ------------------------------------------------------------------ #
    # Election state machine
    # ------------------------------------------------------------------ #
    def _start_election(self, start_hop: int) -> None:
        """Send ELECTION to every higher-ID peer; schedule timeout-victory."""
        with self._election_lock:
            if self.in_election:
                return
            self.in_election = True
            self.received_ok = False

        higher = sorted(n for n in self.queues if n > self.id)
        self.metrics.record_event(
            self.id,
            f"starts election @hop={start_hop}, ELECTION -> {higher}" if higher
            else f"no higher peers -- becomes leader immediately",
        )

        if not higher:
            self._become_leader(hop=start_hop)
            return

        for h in higher:
            self.send("ELECTION", h, hop=start_hop)

        # Wait for OK in a side thread so the message loop keeps processing.
        threading.Thread(
            target=self._await_ok_then_decide,
            args=(start_hop + 1,),
            daemon=True,
            name=f"N{self.id}-OK-timer",
        ).start()

    def _await_ok_then_decide(self, coord_hop: int) -> None:
        time.sleep(OK_TIMEOUT_S)
        if self.coord_received.is_set():
            return
        if self.received_ok:
            return
        self._become_leader(hop=coord_hop)

    def _become_leader(self, hop: int) -> None:
        self.leader = self.id
        others: List[int] = sorted(n for n in self.queues if n != self.id)
        self.metrics.record_event(
            self.id, f"WINS election; broadcasting COORDINATOR -> {others}"
        )
        for o in others:
            self.send("COORDINATOR", o, payload=self.id, hop=hop)
        self.coord_received.set()
        self.stop()
