"""Render a ConformanceReport as a human-readable table.

Read-only presentation, in the spirit of the store inspector: it turns the
per-criterion verdicts into a table a third party can read at a glance and —
faithful to §13's "from traces alone" stance — surfaces the EVIDENCE BASIS of
each claim, so a reader sees which verdicts the `[event]` log confirms and which
rest on structural, declared or third-party guarantees it cannot read.

Ported from dil-core, first against DIL protocol v0.3.3 (the package
implements `dil.DIL_PROTOCOL_VERSION`).
"""

from typing import Final

from .checker import ConformanceReport, ConformanceVerdict, EvidenceBasis

_MARK: Final[dict[ConformanceVerdict, str]] = {
    "pass": "PASS",
    "partial": "PART",
    "fail": "FAIL",
    "unverifiable": "N/V ",
}

_CLAIM_MARK: Final[dict[ConformanceVerdict, str]] = {
    "pass": "✓",
    "partial": "~",
    "fail": "✗",
    "unverifiable": "?",
}

_BASES: Final[tuple[EvidenceBasis, ...]] = (
    "trace",
    "structural",
    "declared",
    "third-party",
)


def render_conformance(report: ConformanceReport) -> str:
    s = report.summary
    header = (
        f"Conformance (§13) — {s['pass']} pass, {s['partial']} partial, "
        f"{s['fail']} fail, {s['unverifiable']} n/v"
    )

    # Evidence line: how many claims of each basis, and how many criteria are
    # confirmable from the [event] log ALONE — every claim `trace`. The honest
    # answer to §13's "reading only its externally verifiable traces".
    tally: dict[EvidenceBasis, int] = {
        "trace": 0,
        "structural": 0,
        "declared": 0,
        "third-party": 0,
    }
    for r in report.results:
        for c in r.claims:
            tally[c.basis] += 1

    trace_only = sum(
        1
        for r in report.results
        if r.claims and all(c.basis == "trace" for c in r.claims)
    )

    evidence = (
        "  Evidence — "
        + ", ".join(f"{tally[b]} {b}" for b in _BASES)
        + f" claim(s); {trace_only}/{len(report.results)} criteria confirmable "
        "from [event] alone"
    )

    lines: list[str] = []
    for r in report.results:
        lines.append(f"  [{_MARK[r.verdict]}] §13.{r.id} {r.title}: {r.detail}")
        lines.append(
            "         "
            + "  ·  ".join(
                f"{_CLAIM_MARK[c.verdict]} [{c.basis}] {c.claim}" for c in r.claims
            )
        )

    return "\n".join([header, evidence, *lines])
