"""Progress page: topics done per paper, milestone targets vs actuals, overdue topics, PYQ coverage.

A topic is done when its note is in git history (i.e. merged to main). Reads only YAML and git.
    python scripts/progress_page.py [--today YYYY-MM-DD] [--out build/docs/progress.md]
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from common import MILESTONES, PAPERS, load_pyqs, load_topics, merge_dates, today_ist

BAR = 20


def bar(done: int, total: int) -> str:
    filled = round(BAR * done / total) if total else 0
    return "█" * filled + "░" * (BAR - filled)


def render(today: date, merged: dict[str, date]) -> str:
    topics = load_topics()
    done = {t["topic_id"] for t in topics if t["topic_id"] in merged}
    out = ["# Progress", "", f"Updated {today:%d %b %Y} (IST).", "", "## Papers", "", "```"]
    for p in PAPERS:
        ts = [t for t in topics if t["paper"] == p]
        d = sum(t["topic_id"] in done for t in ts)
        out.append(f"{p.upper()}  {bar(d, len(ts))}  {d:>2}/{len(ts)}")
    out.append(f"ALL  {bar(len(done), len(topics))}  {len(done):>2}/{len(topics)}")
    out += ["```", "", "## Milestones", "", "| Milestone | Target | Done by then | Status |", "|---|---|---|---|"]
    for title, when in MILESTONES.items():
        target = sum(t["due"] <= when for t in topics)
        actual = sum(d <= when for d in merged.values())
        status = "✅" if actual >= target else ("⏳" if today <= when else "❌")
        out.append(f"| {title} | {target} | {actual} | {status} |")

    overdue = sorted((t for t in topics if t["due"] < today and t["topic_id"] not in done), key=lambda t: t["due"])
    out += ["", f"## Overdue ({len(overdue)})", ""]
    out += [f"- **{t['topic_id']}** · {t['title']} — due {t['due']:%d %b} ({(today - t['due']).days} days late)"
            for t in overdue] or ["None. 🎉"]

    upcoming = sorted((t for t in topics if t["due"] >= today and t["topic_id"] not in done), key=lambda t: t["due"])[:5]
    if upcoming:
        out += ["", "## Next up", ""] + [f"- {t['due']:%a %d %b} · **{t['topic_id']}** · {t['title']}" for t in upcoming]

    qs = load_pyqs()
    in_bank = [q for q in qs if q.get("text")]
    answered = [q for q in in_bank if q["topic_id"] in done]
    out += ["", "## PYQs", "", "| | Count |", "|---|---|",
            f"| In bank (text imported) | {len(in_bank)} |",
            f"| Text pending import | {len(qs) - len(in_bank)} |",
            f"| Verified against official PDF | {sum(q.get('verified') is True for q in qs)} |",
            f"| Answered (topic merged) | {len(answered)} |"]
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
