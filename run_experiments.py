"""Run all four required scenarios and emit logs + a comparison table.

Scenarios (per spec section 4):
    Bully  + Best-Case  (Node 9 initiates)
    Bully  + Worst-Case (Node 1 initiates)
    Ring   + Best-Case  (Node 9 initiates)
    Ring   + Worst-Case (Node 1 initiates)

Outputs:
    logs/<algo>_<scenario>.log     -- step-by-step message trace
    results/results.json           -- machine-readable metrics
    results/comparison_table.txt   -- pretty ASCII comparison table
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from app.simulator import run_bully, run_ring

ROOT = Path(__file__).parent
LOG_DIR = ROOT / "logs"
RES_DIR = ROOT / "results"
LOG_DIR.mkdir(exist_ok=True)
RES_DIR.mkdir(exist_ok=True)

FAILED = (10,)  # Node 10 is the dead leader
N_NODES = 10

SCENARIOS = [
    ("Bully", "best",  9, run_bully),
    ("Bully", "worst", 1, run_bully),
    ("Ring",  "best",  9, run_ring),
    ("Ring",  "worst", 1, run_ring),
]


def main() -> None:
    rows: List[Dict[str, object]] = []
    for algo, scenario, initiator, runner in SCENARIOS:
        label = f"{algo} | {scenario}-case | initiator=N{initiator}"
        log_path = LOG_DIR / f"{algo.lower()}_{scenario}.log"
        print(f"\n==> Running {label}")
        metrics = runner(
            initiator_id=initiator,
            n_nodes=N_NODES,
            failed_nodes=FAILED,
            log_file=log_path,
            run_label=label,
        )
        row = {
            "algorithm": algo,
            "scenario": scenario,
            "initiator": initiator,
            "failed_node": FAILED[0],
            "messages": metrics.messages,
            "hops": metrics.max_hop,
            "elapsed_ms": round(metrics.elapsed_s * 1000.0, 2),
            "log": str(log_path.relative_to(ROOT)).replace("\\", "/"),
        }
        rows.append(row)
        print(
            f"    messages={row['messages']:>3}   hops={row['hops']:>2}   "
            f"elapsed={row['elapsed_ms']:>8.2f} ms   log={row['log']}"
        )

    # JSON
    (RES_DIR / "results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

    # Pretty table
    header = (
        f"{'Algorithm':<10} {'Scenario':<10} {'Initiator':<10} "
        f"{'Messages':>10} {'Hops':>6} {'Time (ms)':>12}"
    )
    sep = "-" * len(header)
    lines = [
        "Leader-Election Comparison  (N=10, failed leader = N10, 50 ms WAN delay per send)",
        sep,
        header,
        sep,
    ]
    for r in rows:
        lines.append(
            f"{r['algorithm']:<10} {r['scenario']:<10} N{r['initiator']:<9} "
            f"{r['messages']:>10} {r['hops']:>6} {r['elapsed_ms']:>12.2f}"
        )
    lines.append(sep)
    table = "\n".join(lines) + "\n"
    (RES_DIR / "comparison_table.txt").write_text(table, encoding="utf-8")

    print("\n" + table)
    print(f"JSON     -> {RES_DIR / 'results.json'}")
    print(f"Table    -> {RES_DIR / 'comparison_table.txt'}")
    print(f"Per-run logs in {LOG_DIR}/")


if __name__ == "__main__":
    main()
