"""Create or update one GitHub issue per topic from syllabus/issues.yaml + data/pyqs. Idempotent.

    python scripts/create_issues.py --dry-run         # validate + print what would change
    python scripts/create_issues.py                   # create missing issues, update changed bodies
    python scripts/create_issues.py --only GS2-POL-04 # limit to some topics
    python scripts/create_issues.py --scaffold GS2-POL-04   # write note + pyqs.md skeletons locally (no GitHub)

Never closes or reopens issues. Never writes PYQ text; it is copied from data/pyqs as-is.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time

from common import (MILESTONES, ROOT, TITLE_ID_RE, TOPIC_ID_RE, answers_dir, load_pyqs, load_topics, note_path,
                    pyqs_for, topics_by_id)

DOD = """1. Notes in your own words have a `## mN · …` section for every micro-topic (≥80 words or ≥5 bullets each), with ≥2 data points/reports and recent events worked in.
2. Every PYQ below (text imported) has a `## <PYQ-ID>` section in `pyqs.md`: the question quoted verbatim and a scan of your timed, handwritten answer (7 min / 10-marker, 11 min / 15-marker).
3. `completeness`, `lint` and `site-build` are green.
4. Every AI review thread is resolved — fixed, or answered with your reasoning. Rubric ≥ 9/12, no open factual errors."""


def official_lines() -> dict[str, str]:
    text = (ROOT / "syllabus/official.md").read_text()
    return {m.group(1): m.group(2).strip() for m in re.finditer(r"^- \*\*(GS[123]-L\d+)\*\* (.+)$", text, re.M)}


def labels_for(t: dict) -> list[str]:
    return [t["paper"], f"subj:{t['subject']}", f"priority:{t['priority']}", f"size:{t['size']}"]


def render_body(t: dict) -> str:
    lines = official_lines()
    tid = t["topic_id"]
    out = [f"<!-- topic-id: {tid} -->", "", "### Syllabus", ""]
    out += [f"> **{l}** {lines[l]}" for l in t["syllabus_lines"]] + [""]
    out += ["### Micro-topics", "", "Each needs a `## mN · …` section in "
            f"`notes/{t['paper']}/{t['subject']}/{tid}.md`.", ""]
    out += [f"- [ ] **{m['id']}** · {m['text']}" for m in t["micro_syllabus"]] + [""]
    qs = pyqs_for(tid)
    out += [f"### PYQs ({len(qs)})", ""]
    if qs:
        out += [f"Answer each in `answers/{t['paper']}/{tid}/pyqs.md`. ⚠️ = not yet checked against the official "
                "UPSC PDF; ⏳ = text not imported yet (not required by CI).", "",
                "| ID | Year | Marks | Question | |", "|---|---|---|---|---|"]
        for q in qs:
            if q.get("text"):
                text = q["text"].replace("|", "\\|")
                flag = "✅" if q.get("verified") else "⚠️"
            else:
                text, flag = f"*Text pending import — see [{q['source_url']}]({q['source_url']})*", "⏳"
            out.append(f"| `{q['id']}` | {q['year']} | {q['marks']}M/{q['words']}w | {text} | {flag} |")
    else:
        out.append("No PYQs in the bank yet.")
    out += ["", "### Sources", ""] + [f"- {s}" for s in t["sources"]]
    if t.get("strategy"):
        out += ["", "### Strategy", "", t["strategy"]]
    out += ["", "### Definition of done", "", DOD, "",
            f"**Due:** {t['due']:%a %d %b %Y} · **Milestone:** {t['milestone']} · "
            f"**Priority:** {t['priority']} · **Size:** {t['size']}", "",
            f"Start: `git switch -c study/{tid} && python scripts/create_issues.py --scaffold {tid}`"]
    body = "\n".join(out) + "\n"
    sha = hashlib.sha256(body.encode()).hexdigest()[:12]
    return body + f"<!-- body-sha: {sha} -->\n"


def validate() -> list[str]:
    errs = []
    ids = [t["topic_id"] for t in load_topics()]
    for tid in ids:
        if not TOPIC_ID_RE.match(tid):
            errs.append(f"bad topic id {tid}")
    if len(ids) != len(set(ids)):
        errs.append("duplicate topic ids")
    known = set(ids)
    errs += [f"PYQ {q['id']} → unknown topic {q['topic_id']}" for q in load_pyqs() if q["topic_id"] not in known]
    errs += [f"{t['topic_id']}: unknown milestone {t['milestone']}" for t in load_topics() if t["milestone"] not in MILESTONES]
    lines = official_lines()
    errs += [f"{t['topic_id']}: unknown syllabus line {l}" for t in load_topics() for l in t["syllabus_lines"] if l not in lines]
    return errs


def gh(*args: str, capture: bool = True) -> str:
    return subprocess.run(["gh", *args], capture_output=capture, text=True, check=True).stdout


def existing_issues() -> dict[str, dict]:
    issues = json.loads(gh("issue", "list", "--state", "all", "--limit", "500", "--json", "number,title,body"))
    found = {}
    for i in issues:
        m = TITLE_ID_RE.match(i["title"]) or re.search(r"<!-- topic-id: (\S+) -->", i["body"] or "")
        if m:
            found[m.group(1)] = i
    return found


def sync(only: set[str] | None, dry_run: bool) -> None:
    try:
        existing = existing_issues()
    except subprocess.CalledProcessError as e:
        if not dry_run:
            raise
        print(f"(could not list issues — {e.stderr.strip() or 'no GitHub repo yet'}; assuming none exist)\n")
        existing = {}
    created = updated = same = 0
    for t in load_topics():
        tid = t["topic_id"]
        if only and tid not in only:
            continue
        title = f"[{tid}] {t['title']}"
        body = render_body(t)
        cur = existing.get(tid)
        if cur and (cur["body"] or "").strip() == body.strip():
            same += 1
            continue
        if dry_run:
            print(f"{'UPDATE #' + str(cur['number']) if cur else 'CREATE'}  {title}  labels={','.join(labels_for(t))}  "
                  f"milestone={t['milestone']}")
            created += cur is None
            updated += cur is not None
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(body)
        if cur:
            gh("issue", "edit", str(cur["number"]), "--body-file", f.name)
            updated += 1
            print(f"updated #{cur['number']} {title}")
        else:
            url = gh("issue", "create", "--title", title, "--body-file", f.name, "--milestone", t["milestone"],
                     "--label", ",".join(labels_for(t))).strip()
            created += 1
            print(f"created {url} {title}")
            time.sleep(1)
    verb = "would create" if dry_run else "created"
    print(f"\n{verb} {created}, {'would update' if dry_run else 'updated'} {updated}, unchanged {same}")


def scaffold(tid: str) -> None:
    t = topics_by_id().get(tid)
    if t is None:
        sys.exit(f"unknown topic {tid}")
    np = note_path(t)
    if np.exists():
        print(f"exists, left alone: {np.relative_to(ROOT)}")
    else:
        np.parent.mkdir(parents=True, exist_ok=True)
        src = "\n".join(f"  - {json.dumps(s, ensure_ascii=False)}" for s in t["sources"])
        body = "\n\n".join(f"## {m['id']} · {m['text']}\n\n" for m in t["micro_syllabus"])
        np.write_text(f"---\ntopic_id: {tid}\ntitle: {json.dumps(t['title'], ensure_ascii=False)}\nstatus: draft\nsources:\n{src}\n---\n\n{body}")
        print(f"wrote {np.relative_to(ROOT)}")
    qs = pyqs_for(tid, required_only=True)
    ad = answers_dir(t)
    ap = ad / "pyqs.md"
    if not qs:
        print("no PYQs with imported text; no pyqs.md needed yet")
    elif ap.exists():
        print(f"exists, left alone: {ap.relative_to(ROOT)}")
    else:
        (ad / "img").mkdir(parents=True, exist_ok=True)
        blocks = [f"## {q['id']}\n\n> {q['text']}\n>\n> (Mains {q['year']}, {q['marks']}M/{q['words']}w)\n\n"
                  f"![answer](img/{q['id']}.jpg)\n\n**Key points / self-critique:**\n" for q in qs]
        ap.write_text(f"# {tid} · PYQ answers\n\n" + "\n".join(blocks))
        print(f"wrote {ap.relative_to(ROOT)} — save scans as {ad.relative_to(ROOT)}/img/<PYQ-ID>.jpg")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", nargs="+", metavar="TOPIC_ID")
    ap.add_argument("--scaffold", metavar="TOPIC_ID")
    ap.add_argument("--print", metavar="TOPIC_ID", help="print one rendered issue body")
    args = ap.parse_args()
    errs = validate()
    if errs:
        print("\n".join(f"❌ {e}" for e in errs))
        return 1
    if args.scaffold:
        scaffold(args.scaffold)
    elif args.print:
        print(render_body(topics_by_id()[args.print]))
    else:
        sync(set(args.only) if args.only else None, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
