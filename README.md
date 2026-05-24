Saleha Shoaib — BSCS23036

# PDC Assignment 3 — Distributed Leader Election (Bully vs Ring)

Simulated distributed system of **N = 10** independent nodes, each running
as its own `threading.Thread` with a private `queue.Queue` inbox. Nodes
share no mutable state — every interaction is a `Message` enqueued on a
peer's inbox (satisfies spec section 2.1: *no shared memory*). Every send
sleeps **50 ms** to simulate WAN latency (spec section 3, metric 3).

Two classic leader-election algorithms are implemented and benchmarked:

- **Bully** (Garcia-Molina, 1982) — `app/bully.py`
- **Ring** (Chang–Roberts style) — `app/ring.py`

Both are evaluated under the two initiator scenarios required by section 4
of the spec (failed leader = N10):

| Scenario   | Initiator |
| ---------- | --------- |
| Best-case  | N9 (second-highest ID) |
| Worst-case | N1 (lowest ID) |

## Headline result

```
Algorithm  Scenario   Initiator    Messages   Hops    Time (ms)
---------------------------------------------------------------
Bully      best       N9                 10      2      2083.54
Bully      worst      N1                 90      3      2641.23
Ring       best       N9                 18     18      1060.01
Ring       worst      N1                 18     18      1071.22
```

Message and hop counts are **deterministic** (match the closed-form
expectations exactly); wall-clock fluctuates by a few tens of ms run-to-run
depending on OS thread scheduling.

Full discussion is in [`report/report.pdf`](report/report.pdf) (2 pages).

## Repository layout

```
PDC-Sp24-BSCS23036-Shoaib/
├── app/
│   ├── node.py          # base Node, Message, 50 ms send delay
│   ├── metrics.py       # thread-safe message/hop/time collector
│   ├── bully.py         # Bully algorithm node
│   ├── ring.py          # Ring algorithm node
│   └── simulator.py     # wires nodes together, drives one election
├── logs/
│   ├── bully_best.log   # message-by-message trace of each run
│   ├── bully_worst.log
│   ├── ring_best.log
│   └── ring_worst.log
├── results/
│   ├── results.json     # machine-readable metrics
│   └── comparison_table.txt
├── report/
│   ├── generate_report.py
│   └── report.pdf       # 2-page analysis
├── run_experiments.py   # runs all 4 scenarios, writes logs + results
├── requirements.txt     # reportlab only (used for the PDF)
└── README.md
```

## How to run (Windows CMD)

### 1. Install

```cmd
cd /d D:\path\to\PDC-Sp24-BSCS23036-Shoaib
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

(macOS / Linux: replace step 2 with `source .venv/bin/activate`.)

`reportlab` is only needed for the PDF — the simulation itself uses
nothing but the Python standard library (`threading`, `queue`, `time`,
`dataclasses`).

### 2. Run the simulation (writes logs/ + results/)

```cmd
python run_experiments.py
```

Expected console output (numbers may shift by a few ms run-to-run):

```
==> Running Bully | best-case | initiator=N9
    messages= 10   hops= 2   elapsed= 2083.54 ms   log=logs/bully_best.log
==> Running Bully | worst-case | initiator=N1
    messages= 90   hops= 3   elapsed= 2641.23 ms   log=logs/bully_worst.log
==> Running Ring | best-case | initiator=N9
    messages= 18   hops=18   elapsed= 1060.01 ms   log=logs/ring_best.log
==> Running Ring | worst-case | initiator=N1
    messages= 18   hops=18   elapsed= 1071.22 ms   log=logs/ring_worst.log
```

### 3. Rebuild the PDF report

```cmd
python report/generate_report.py
```

This reads `results/results.json` and rewrites `report/report.pdf`.

## What each metric measures (per spec section 3)

| Metric | Where it lives | Definition |
| ------ | -------------- | ---------- |
| Total messages | `MetricsCollector.messages` | Every call to `Node.send()` is counted (including messages sent to the dead N10, which go onto its queue with no consumer — exactly what would happen on a real wire). |
| Network hops   | `MetricsCollector.max_hop`  | Each `Message` carries a `hop` field. A receiver handles a message at `msg.hop` and stamps its outgoing replies with `msg.hop + 1`. The reported metric is `max(hop)` over all messages, i.e. the **sequential causal depth** of the election. Per-spec definition: "A → B, then B → C and B → D simultaneously" = 2 hops. |
| Wall-clock time | `MetricsCollector.elapsed_s` | `perf_counter()` from the TRIGGER send up to the *last* `COORDINATOR` reception in the cluster. With 50 ms injected per send, this directly reflects the simulated WAN latency. |

## Implementation notes (for the grader)

- **No global state, no shared variables**: each node only mutates its
  own instance attributes; cross-node interaction is exclusively through
  `queues[receiver].put(msg)`. The `MetricsCollector` is an external
  observer (think Wireshark), not a communication channel between nodes.
- **Failed node**: N10 is not started as a thread, but its queue exists,
  so sends *to* it are still counted as on-the-wire messages (no reply).
- **Bully OK timeout** is tuned to **1.5 s** (`app/bully.py:OK_TIMEOUT_S`).
  Under the cascade, a higher-ID node can spend ~900 ms draining its
  inbox before its OK reaches a lower-ID peer; a shorter timeout causes
  split-brain (multiple nodes simultaneously declare themselves leader).
  Discussion is in section 4.4 of the PDF report.
- **Ring** uses the (alive-only) sorted ring `[1,2,...,9]`; the dead N10
  is skipped from the topology so the ring closes cleanly.
- Repo is named exactly `PDC-Sp24-BSCS23036-Shoaib` per assignment convention.
