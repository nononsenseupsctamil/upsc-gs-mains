"""Required check `completeness`: the topic has notes, and every required PYQ is answered with a scan.

Micro-topics in the issue are a reading guide only; CI does not check headings or length.

CI:     GH_TOKEN=… PR_NUMBER=12 python scripts/check_completeness.py
Local:  python scripts/check_completeness.py --local GS2-POL-04
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

from common import (REQUIRED_FROM_YEAR, IMAGE_EXTS, IMAGE_LINK_RE, ROOT, TITLE_ID_RE,
                    WORD_RE, answers_dir, h2_sections, marks_label, normalise, note_path, pyqs_for, split_front_matter,
                    topics_by_id)

CLOSING_RE = re.compile(r"(?i)\b(close[sd]?|fix(e[sd])?|resolve[sd]?)\s+#(\d+)")


def check_topic(topic_id: str) -> list[tuple[str, bool, str]]:
    """Return (item, ok, detail) rows for one topic."""
    t = topics_by_id().get(topic_id)
    if t is None:
        return [("topic", False, f"{topic_id} is not in syllabus/issues.yaml")]
    rows: list[tuple[str, bool, str]] = []

    # --- notes ---------------------------------------------------------------------
    np = note_path(t)
    rel = np.relative_to(ROOT)
    if not np.exists():
        rows.append((f"note `{rel}`", False, "missing"))
    else:
        text = np.read_text()
        _, body = split_front_matter(text)
        # Only headings are stripped before counting, so an empty skeleton does not count as notes.
        words = len(WORD_RE.findall("\n".join(l for l in body.splitlines() if not l.lstrip().startswith("#"))))
        rows.append((f"notes `{rel}`", words > 0, f"{words} words" if words else "only headings so far — no notes yet"))

    # --- answers -------------------------------------------------------------------
    qs = pyqs_for(topic_id, required_only=True)
    every = pyqs_for(topic_id)
    older = sum(q["year"] < REQUIRED_FROM_YEAR for q in every)
    pending = sum(q["year"] >= REQUIRED_FROM_YEAR and not q.get("text") for q in every)
    if older:
        rows.append((f"{older} older PYQ(s) (before {REQUIRED_FROM_YEAR})", True, "practice only, not required"))
    if pending:
        rows.append((f"{pending} PYQ(s) with text pending import", True, "not required yet"))
    if not qs:
        return rows
    ad = answers_dir(t)
    ap = ad / "pyqs.md"
    if not ap.exists():
        rows.append((f"answers `{ap.relative_to(ROOT)}`", False, "missing"))
        return rows
    sections = h2_sections(ap.read_text())
    for q in qs:
        label = f"{q['id']} ({marks_label(q)})"
        sec = next((s for h, s in sections.items() if h.split()[0] == q["id"]), None) if sections else None
        if sec is None:
            rows.append((label, False, f"no `## {q['id']}` section"))
            continue
        quoted = normalise(" ".join(l.lstrip("> ").rstrip() for l in sec.splitlines() if l.lstrip().startswith(">")))
        problems = []
        if normalise(q["text"]) not in quoted:
            problems.append("question not quoted verbatim (`> …`)")
        imgs = [m for m in IMAGE_LINK_RE.findall(sec) if not m.startswith(("http://", "https://"))]
        good = [i for i in imgs if (ad / i).suffix.lower() in IMAGE_EXTS and (ad / i).is_file()]
        if not good:
            problems.append("no scan linked (`![answer](img/….jpg)` pointing at an existing file)")
        rows.append((label, not problems, "; ".join(problems) if problems else f"{len(good)} scan(s)"))
    return rows


def gh_json(*args: str) -> dict:
    return json.loads(subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout)


def report(title: str, rows: list[tuple[str, bool, str]]) -> bool:
    ok = all(r[1] for r in rows)
    lines = [f"### {'✅' if ok else '❌'} completeness — {title}", "", "| | Item | Detail |", "|---|---|---|"]
    lines += [f"| {'✅' if r[1] else '❌'} | {r[0]} | {r[2]} |" for r in rows]
    out = "\n".join(lines) + "\n"
    print(out)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a") as f:
            f.write(out)
    return ok


def pr_mode(number: str) -> bool:
    pr = gh_json("pr", "view", number, "--json", "body,labels,files,closingIssuesReferences")
    labels = {l["name"] for l in pr["labels"]}
    files = [f["path"] for f in pr["files"]]
    if "chore" in labels:
        bad = [f for f in files if f.startswith(("notes/", "answers/"))]
        rows = [("chore PR touches no notes/ or answers/", not bad, ", ".join(bad) or "ok")]
        return report("chore PR", rows)

    issues = [i["number"] for i in pr.get("closingIssuesReferences") or []]
    if not issues:
        issues = [int(m.group(3)) for m in CLOSING_RE.finditer(pr.get("body") or "")]
    if len(issues) != 1:
        return report("PR", [("PR links exactly one issue", False,
                               f"found {len(issues)}; put `Closes #N` in the PR body (or label it `chore`)")])
    issue = gh_json("issue", "view", str(issues[0]), "--json", "title")
    m = TITLE_ID_RE.match(issue["title"])
    if not m:
        return report("PR", [(f"issue #{issues[0]} is a topic issue", False, f"title `{issue['title']}` has no [ID]")])
    return report(f"{m.group(1)} (#{issues[0]})", check_topic(m.group(1)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--local", metavar="TOPIC_ID", help="check one topic against the working tree")
    args = ap.parse_args()
    if args.local:
        return 0 if report(args.local, check_topic(args.local)) else 1
    number = os.environ.get("PR_NUMBER")
    if not number:
        ap.error("set PR_NUMBER (CI) or pass --local TOPIC_ID")
    return 0 if pr_mode(number) else 1


if __name__ == "__main__":
    sys.exit(main())
