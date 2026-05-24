"""Thread-safe metric & log collector for one election run.

Captures the three metrics required by the assignment:
    1. Total messages sent across the cluster.
    2. Network hops  = max causal depth (the `hop` field of any message).
    3. Wall-clock elapsed time from the start of the election until the last
       alive node became aware of the new leader.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class LogEntry:
    t_ms: float
    text: str


class MetricsCollector:
    def __init__(self, log_file: Optional[Path] = None, run_label: str = "") -> None:
        self._lock = threading.Lock()
        self.messages = 0
        self.max_hop = 0
        self.start_time: Optional[float] = None
        self.last_known_t: Optional[float] = None
        self.entries: List[LogEntry] = []
        self.log_file = log_file
        self.run_label = run_label

    def start(self) -> None:
        self.start_time = time.perf_counter()
        self.last_known_t = self.start_time

    def stop(self) -> None:
        if self.log_file is not None:
            self.entries.sort(key=lambda e: e.t_ms)
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write(f"=== {self.run_label} ===\n")
                f.write(f"messages = {self.messages}\n")
                f.write(f"max_hop  = {self.max_hop}\n")
                f.write(f"elapsed  = {self.elapsed_s * 1000:.2f} ms\n")
                f.write("-" * 78 + "\n")
                for e in self.entries:
                    f.write(e.text + "\n")

    @property
    def elapsed_s(self) -> float:
        if self.start_time is None or self.last_known_t is None:
            return 0.0
        return self.last_known_t - self.start_time

    def _now_ms(self) -> float:
        if self.start_time is None:
            return 0.0
        return (time.perf_counter() - self.start_time) * 1000.0

    def _append(self, t_ms: float, text: str) -> None:
        with self._lock:
            self.entries.append(LogEntry(t_ms, text))

    def record_send(self, msg) -> None:
        with self._lock:
            self.messages += 1
            if msg.hop > self.max_hop:
                self.max_hop = msg.hop
        t_ms = self._now_ms()
        payload = "" if msg.payload is None else f" payload={msg.payload}"
        self._append(
            t_ms,
            f"[{t_ms:9.2f} ms] hop={msg.hop:<2} SEND   {msg.type:<12} "
            f"N{msg.sender:<2} -> N{msg.receiver:<2}{payload}",
        )

    def record_recv(self, msg) -> None:
        t_ms = self._now_ms()
        if msg.type == "COORDINATOR":
            with self._lock:
                self.last_known_t = time.perf_counter()
        payload = "" if msg.payload is None else f" payload={msg.payload}"
        self._append(
            t_ms,
            f"[{t_ms:9.2f} ms] hop={msg.hop:<2} RECV   {msg.type:<12} "
            f"N{msg.receiver:<2} <- N{msg.sender:<2}{payload}",
        )

    def record_event(self, node_id: int, text: str) -> None:
        t_ms = self._now_ms()
        self._append(t_ms, f"[{t_ms:9.2f} ms]        EVENT               N{node_id:<2} :: {text}")
