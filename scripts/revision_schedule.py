"""Spaced revision: a topic is due 1, 7, 30 and 90 days after its note was merged.

    python scripts/revision_schedule.py [--today YYYY-MM-DD] [--out build/docs/revise-today.md]
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from common import SUBJECT_TITLES, merge_dates, pyqs_for, today_ist, topics_by_id

INTERVALS = (1, 7, 30, 90)
MISSED_WINDOW = 3
PREVIEW_DAYS = 7


def due_on(day: date, merged: dict[str, date]) -> list[tuple[str, int]]:
    """(topic_id, interval) pairs due on `day`, ordered by interval then id."""
    hits = [(tid, (day - d).days) for tid, d in merged.items() if (day - d).days in INTERVALS]
    return sorted(hits, key=lambda h: (h[1], h[0]))


def link(tid: str) -> str:
    t = topics_by_id()[tid]
    n = len(pyqs_for(tid))
    pyq = f" · {n} PYQ{'s' if n != 1 else ''}" if n else ""
    return f"[{tid} · {t['title']}]({t['paper']}/{t['subject']}/{tid}.md) — {SUBJECT_TITLES[t['subject']]}{pyq}"


def render(today: date, merged: dict[str, date]) -> str:
    merged = {k: v for k, v in merged.items() if k in topics_by_id()}
    out = ["# Revise today", "", f"**{today:%A, %d %B %Y}** (IST). Topics come back 1, 7, 30 and 90 days after their "
           "notes were merged. Revise the note, then re-attempt one PYQ from memory in the time limit.", ""]
    todays = due_on(today, merged)
    out += ["## Due today", ""]
    if todays:
        for interval in INTERVALS:
            group = [tid for tid, i in todays if i == interval]
            if group:
                out += [f"### D+{interval}", ""] + [f"- [ ] {link(tid)}" for tid in group] + [""]
    else:
        out += ["Nothing due today. Pick an older topic and do one timed PYQ.", ""]

    missed = [(today - timedelta(days=k), due_on(today - timedelta(days=k), merged)) for k in range(1, MISSED_WINDOW + 1)]
    missed = [(d, h) for d, h in missed if h]
    if missed:
        out += [f"## Missed (last {MISSED_WINDOW} days)", ""]
        for d, hits in missed:
            out += [f"- {d:%a %d %b}: " + "; ".join(f"{link(tid)} (D+{i})" for tid, i in hits)]
        out += [""]

    out += [f"## Next {PREVIEW_DAYS} days", ""]
    upcoming = [(today + timedelta(days=k), due_on(today + timedelta(days=k), merged)) for k in range(1, PREVIEW_DAYS + 1)]
    rows = [f"| {d:%a %d %b} | " + ", ".join(f"{tid} (D+{i})" for tid, i in hits) + " |" for d, hits in upcoming if hits]
    out += (["| Day | Topics |", "|---|---|"] + rows) if rows else ["Nothing scheduled."]
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--today", type=date.fromisoformat, default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    md = render(args.today or today_ist(), merge_dates())
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md)
    else:
        print(md)


if __name__ == "__main__":
    main()
