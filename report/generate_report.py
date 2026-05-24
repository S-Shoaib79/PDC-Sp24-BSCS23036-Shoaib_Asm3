"""Build report/report.pdf from results/results.json.

Run AFTER `python run_experiments.py`. Output is constrained to <= 2 pages
per the assignment spec (section 5.3).

    python report/generate_report.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

REPORT_DIR = Path(__file__).parent
ROOT = REPORT_DIR.parent
RESULTS = ROOT / "results" / "results.json"
OUT_PATH = REPORT_DIR / "report.pdf"


# --------------------------------------------------------------------------- #
# Styles
# --------------------------------------------------------------------------- #
styles = getSampleStyleSheet()

H_TITLE = ParagraphStyle(
    "h_title",
    parent=styles["Heading1"],
    fontSize=14,
    leading=17,
    spaceAfter=2,
    textColor=colors.HexColor("#0b1d3a"),
)
H_META = ParagraphStyle(
    "h_meta",
    parent=styles["Normal"],
    fontSize=8.5,
    textColor=colors.HexColor("#3a3a3a"),
    spaceAfter=8,
)
H_PART = ParagraphStyle(
    "h_part",
    parent=styles["Heading2"],
    fontSize=11.5,
    leading=14,
    spaceBefore=6,
    spaceAfter=3,
    textColor=colors.HexColor("#0b1d3a"),
)
H_SUB = ParagraphStyle(
    "h_sub",
    parent=styles["Heading3"],
    fontSize=10,
    leading=12,
    spaceBefore=4,
    spaceAfter=1,
    textColor=colors.HexColor("#11366b"),
)
BODY = ParagraphStyle(
    "body",
    parent=styles["BodyText"],
    fontSize=9.3,
    leading=11.6,
    alignment=TA_JUSTIFY,
    spaceAfter=3,
)
BULLET = ParagraphStyle(
    "bullet",
    parent=BODY,
    leftIndent=11,
    bulletIndent=2,
    spaceAfter=1,
    alignment=TA_LEFT,
)
CAPTION = ParagraphStyle(
    "caption",
    parent=styles["Italic"],
    fontSize=8.5,
    leading=10,
    spaceBefore=2,
    spaceAfter=4,
    textColor=colors.HexColor("#444"),
)


def P(text: str, style: ParagraphStyle = BODY) -> Paragraph:
    return Paragraph(text, style)


def B(text: str) -> Paragraph:
    return Paragraph(f"&bull;&nbsp; {text}", BULLET)


# --------------------------------------------------------------------------- #
# Tables
# --------------------------------------------------------------------------- #
def build_metrics_table(rows: List[Dict[str, object]]) -> Table:
    header = ["Algorithm", "Scenario", "Initiator", "Messages", "Hops", "Wall-clock (ms)"]
    data = [header]
    for r in rows:
        data.append([
            r["algorithm"],
            r["scenario"].capitalize() + "-case",
            f"N{r['initiator']}",
            str(r["messages"]),
            str(r["hops"]),
            f"{r['elapsed_ms']:.2f}",
        ])
    tbl = Table(
        data,
        colWidths=[0.85*inch, 1.05*inch, 0.85*inch, 0.90*inch, 0.65*inch, 1.40*inch],
        hAlign="LEFT",
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#11366b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.8),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (2, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#eef2f8"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tbl


def build_theory_table() -> Table:
    """Closed-form complexity for N=10, 1 dead leader, 50 ms per hop."""
    data = [
        ["Algorithm", "Messages (best)", "Messages (worst)", "Hops", "Time lower bound"],
        ["Bully", "N  = 10", "O(N^2)  ~= 90", "2 - 4", "2 * 50 ms = 100 ms + OK-timeout"],
        ["Ring",  "2(N-1) = 18", "2(N-1) = 18", "2(N-1) = 18", "2(N-1) * 50 ms = 900 ms"],
    ]
    tbl = Table(
        data,
        colWidths=[0.80*inch, 1.15*inch, 1.30*inch, 0.75*inch, 2.10*inch],
        hAlign="LEFT",
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#11366b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#eef2f8"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tbl


# --------------------------------------------------------------------------- #
# Document
# --------------------------------------------------------------------------- #
def build() -> None:
    rows: List[Dict[str, object]] = json.loads(RESULTS.read_text(encoding="utf-8"))

    # quick lookups
    by_key = {(r["algorithm"], r["scenario"]): r for r in rows}
    bb = by_key[("Bully", "best")]
    bw = by_key[("Bully", "worst")]
    rb = by_key[("Ring",  "best")]
    rw = by_key[("Ring",  "worst")]

    doc = BaseDocTemplate(
        str(OUT_PATH),
        pagesize=LETTER,
        leftMargin=0.7*inch,
        rightMargin=0.7*inch,
        topMargin=0.55*inch,
        bottomMargin=0.55*inch,
        title="PDC Assignment 3 -- Saleha Shoaib (BSCS23036)",
        author="Saleha Shoaib",
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
        id="main", showBoundary=0,
    )
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame])])

    story = []

    # ----- Header ----- #
    story += [
        P("PDC Assignment 3 &mdash; Distributed Leader Election: "
          "Bully vs Ring", H_TITLE),
        P("<b>Saleha Shoaib</b> &nbsp;|&nbsp; BSCS23036 &nbsp;|&nbsp; "
          "Parallel and Distributed Computing &nbsp;|&nbsp; "
          "Repo: PDC-Sp24-BSCS23036-Shoaib", H_META),
    ]

    # ----- 1. Setup ----- #
    story += [P("1. Experimental Setup", H_PART)]
    story += [P(
        "10 nodes (IDs 1&hellip;10) each run as an independent "
        "<i>threading.Thread</i> with a private <i>queue.Queue</i> inbox. "
        "Nodes share <b>no</b> mutable state &mdash; the only inter-node "
        "interaction is enqueuing a <i>Message</i> on a peer's inbox, "
        "satisfying section 2.1's no-shared-memory rule. Every call to "
        "<i>Node.send()</i> sleeps for <b>50&nbsp;ms</b> before delivery to "
        "simulate WAN latency (section 3, metric 3). Node 10 (the current "
        "leader) is killed before the run; a surviving node receives a "
        "<i>TRIGGER</i> message from the simulator and starts the election."
    )]

    # ----- 2. Measured metrics ----- #
    story += [P("2. Measured Metrics (4 scenarios)", H_PART)]
    story += [build_metrics_table(rows)]
    story += [P(
        "Figure 1. Measured Messages, Hops and Wall-clock Time per scenario. "
        "Per-run message-by-message traces are in <i>logs/&lt;algo&gt;_&lt;scenario&gt;.log</i>; "
        "the raw numbers are also in <i>results/results.json</i>.",
        CAPTION,
    )]

    # ----- 3. Closed-form vs measured ----- #
    story += [P("3. Closed-Form Complexity (sanity check)", H_PART)]
    story += [build_theory_table()]
    story += [P(
        "Figure 2. Theoretical complexity for the failed-leader scenario "
        "(N=10, one dead node). Measured numbers match exactly: "
        f"Bully best = {bb['messages']} (1 ELECTION to N10 + 9 COORDINATOR "
        f"broadcasts), Bully worst = {bw['messages']} (45 ELECTION + 36 OK + "
        f"9 COORDINATOR; see <i>logs/bully_worst.log</i>), and "
        f"Ring best = Ring worst = {rb['messages']} "
        "(9 ELECTION around the ring + 9 COORDINATOR around the ring).",
        CAPTION,
    )]

    # ----- 4. Analysis ----- #
    story += [P("4. Analysis &mdash; Bully vs Ring", H_PART)]

    story += [P("4.1 Message Complexity", H_SUB)]
    story += [P(
        f"Bully is <b>cheaper than Ring when the initiator is close to the "
        f"top of the hierarchy</b> ({bb['messages']} vs {rb['messages']} "
        "messages in the best case) because N9 only needs to probe N10, "
        "time out, and broadcast. As soon as the initiator is far from the "
        f"top, Bully's recursive cascade explodes &mdash; every Ni receiving "
        f"ELECTION starts its own election to all Nj&gt;i, giving "
        "&#931;<sub>i=1..N-1</sub>(N-i) = N(N-1)/2 ELECTIONs, plus an OK for "
        "every ELECTION that hits an alive node, plus the leader's final "
        f"COORDINATOR broadcast. Our measured {bw['messages']} matches this "
        "O(N&sup2;) bound exactly. Ring is <b>scenario-independent</b>: it "
        "always sends 2(N-1) = 18 messages regardless of who initiates, "
        "because the topology is fixed and each phase (ELECTION sweep, "
        "COORDINATOR sweep) traverses every alive node exactly once."
    )]

    story += [P("4.2 Network Hops (sequential depth)", H_SUB)]
    story += [P(
        f"Bully wins decisively here: just {bb['hops']} hops best, "
        f"{bw['hops']} hops worst. The algorithm exploits parallelism &mdash; "
        "the initiator <i>broadcasts</i> ELECTION in one logical wave, the "
        "receivers reply OK <i>and</i> launch their own elections in a "
        "second wave, and the surviving highest-ID node broadcasts "
        "COORDINATOR in a third wave. No matter how big N gets, the depth "
        "stays a small constant. Ring's depth, by contrast, is "
        f"<b>2(N-1) = {rb['hops']} hops</b> for both scenarios, because the "
        "ring is fundamentally serial &mdash; each forward must wait for "
        "the previous one to arrive."
    )]

    story += [P("4.3 Wall-Clock Latency", H_SUB)]
    story += [P(
        f"With the 50&nbsp;ms injected delay, hop count is the dominant "
        f"term. Ring takes ~{rb['elapsed_ms']/1000:.2f}&nbsp;s (best) and "
        f"~{rw['elapsed_ms']/1000:.2f}&nbsp;s (worst), tracking the "
        "18&times;50&nbsp;ms = 900&nbsp;ms hop-floor closely. Bully's "
        f"best-case wall-clock ({bb['elapsed_ms']/1000:.2f}&nbsp;s) is "
        "dominated by the 1.5&nbsp;s OK-timeout (the price of waiting to "
        "confirm N10 really is dead) plus the 9-message COORDINATOR "
        f"broadcast. Bully worst ({bw['elapsed_ms']/1000:.2f}&nbsp;s) is "
        "the same timeout plus a much larger COORDINATOR phase competing "
        "for thread time against the 90-message cascade. The take-away: "
        "<b>Bully's latency is paid in seconds of failure-detection "
        "timeout, Ring's is paid in serial hops</b> &mdash; on a high-RTT "
        "WAN the timeout matters less, on a fast LAN the hops matter less."
    )]

    story += [P("4.4 When to pick which", H_SUB)]
    story += [
        B("<b>Bully</b> &mdash; small clusters, stable membership, "
          "topology that supports broadcast / full-mesh reachability, and "
          "where minimizing <i>turnaround rounds</i> matters more than "
          "minimizing message count (e.g. low-latency LANs in HPC / "
          "in-memory DB primaries)."),
        B("<b>Ring</b> &mdash; large or geographically distributed "
          "clusters where each node only knows its successor, where "
          "uniform / predictable message cost matters, and where you "
          "want the worst case to equal the best case (no &quot;election "
          "storms&quot;). The Chubby/ZAB family of real-world coordinator "
          "elections is closer in spirit to Ring + quorum than to Bully."),
        B("<b>Failure-detection timeout</b> is the hidden cost in Bully: "
          "we used <i>OK_TIMEOUT_S = 1.5&nbsp;s</i> because with the "
          "cascade a higher node's OK can be delayed by ~900&nbsp;ms "
          "while it drains its inbox. Too short -&gt; split-brain (multiple "
          "leaders); too long -&gt; slow recovery. Ring has no such tuning "
          "knob."),
    ]

    story += [P("5. Reproduction", H_PART)]
    story += [P(
        "<font face='Courier' size='8.5'>"
        "python -m venv .venv &amp;&amp; .venv\\Scripts\\activate.bat<br/>"
        "pip install -r requirements.txt<br/>"
        "python run_experiments.py        # writes logs/ + results/<br/>"
        "python report/generate_report.py # rebuilds this PDF"
        "</font>"
    )]

    doc.build(story)
    print(f"wrote {OUT_PATH}  ({OUT_PATH.stat().st_size:,} bytes)")


if __name__ == "__main__":
    build()
