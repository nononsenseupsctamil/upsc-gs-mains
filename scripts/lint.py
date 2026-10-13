"""Required check `lint`: data schema, note front-matter, relative links, images and PYQ text integrity.

    python scripts/lint.py                 # everything; PYQ-text diff against origin/main
    python scripts/lint.py --base <sha>    # diff PYQ text against a specific commit (CI passes the PR base)
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import date

import yaml

from common import (IMAGE_EXTS, IMAGE_LINK_RE, MAX_IMAGE_BYTES, MILESTONES, PAPERS, PYQ_ID_RE, ROOT, SUBJECT_TITLES,
                    TOPIC_ID_RE, load_pyqs, load_topics, split_front_matter, topics_by_id)

LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
GENERATED_PAGES = {"revise-today.md", "progress.md"}  # written into build/docs by build_site.py
CONFIDENCE = {"official", "cross-checked", "single-source", "text-pending"}
errors: list[str] = []


def err(where: str, msg: str) -> None:
    errors.append(f"{where}: {msg}")


def syllabus_line_ids() -> set[str]:
    return set(re.findall(r"\*\*(GS[123]-L\d+)\*\*", (ROOT / "syllabus/official.md").read_text()))


def lint_topics() -> None:
    lines = syllabus_line_ids()
    seen = set()
    for t in load_topics():
        tid = t.get("topic_id", "?")
        w = f"issues.yaml {tid}"
        if not TOPIC_ID_RE.match(tid):
            err(w, "bad topic_id")
        if tid in seen:
            err(w, "duplicate topic_id")
        seen.add(tid)
        if t.get("paper") != tid[:3].lower():
            err(w, f"paper {t.get('paper')} does not match id")
        if t.get("subject") not in SUBJECT_TITLES:
            err(w, f"unknown subject {t.get('subject')}")
        for k in ("title", "sources", "micro_syllabus", "syllabus_lines"):
            if not t.get(k):
                err(w, f"missing {k}")
        ids = [m.get("id") for m in t.get("micro_syllabus") or []]
        if ids != [f"m{i}" for i in range(1, len(ids) + 1)]:
            err(w, f"micro_syllabus ids must be m1..mN in order, got {ids}")
        for m in t.get("micro_syllabus") or []:
            if not str(m.get("text", "")).strip():
                err(w, f"{m.get('id')} has empty text")
        for l in t.get("syllabus_lines") or []:
            if l not in lines:
                err(w, f"syllabus line {l} not in syllabus/official.md")
        if t.get("priority") not in {"high", "med", "low"}:
            err(w, "priority must be high|med|low")
        if t.get("size") not in {"S", "M", "L"}:
            err(w, "size must be S|M|L")
        if t.get("milestone") not in MILESTONES:
            err(w, f"unknown milestone {t.get('milestone')}")
        due = t.get("due")
        if not isinstance(due, date):
            err(w, "due must be a YYYY-MM-DD date")
        elif t.get("milestone") in MILESTONES and due > MILESTONES[t["milestone"]]:
            err(w, f"due {due} is after its milestone {t['milestone']}")


def lint_pyqs() -> None:
    topics = topics_by_id()
    seen = set()
    for q in load_pyqs():
        pid = q.get("id", "?")
        w = f"pyqs {pid}"
        m = PYQ_ID_RE.match(pid)
        if not m:
            err(w, "id must be <TOPIC-ID>-M<YEAR>-Q<NN>")
            continue
        if pid in seen:
            err(w, "duplicate id")
        seen.add(pid)
        tid, year, qno = m.group(1), int(m.group(2)), int(m.group(3))
        if q.get("topic_id") != tid or tid not in topics:
            err(w, f"topic_id {q.get('topic_id')} must equal {tid} and exist in issues.yaml")
        if q.get("year") != year or q.get("qno") != qno or q.get("paper") != tid[:3]:
            err(w, "year/qno/paper fields disagree with id")
        exp = (10, 150) if qno <= 10 else (15, 250)
        if (q.get("marks"), q.get("words")) != exp:
            err(w, f"marks/words must be {exp[0]}/{exp[1]} for Q{qno}")
        if q.get("confidence") not in CONFIDENCE:
            err(w, f"confidence must be one of {sorted(CONFIDENCE)}")
        if not isinstance(q.get("verified"), bool):
            err(w, "verified must be true/false")
        if (q.get("confidence") == "text-pending") == bool(q.get("text")):
            err(w, "text must be empty exactly when confidence is text-pending")


def lint_pyq_text_changes(base: str | None) -> None:
    """A PR may change PYQ text only if it also sets verified: true or changes the entry's notes."""
    if not base:
        return
    for p in PAPERS:
        path = f"data/pyqs/{p}.yaml"
        old = subprocess.run(["git", "show", f"{base}:{path}"], cwd=ROOT, capture_output=True, text=True)
        if old.returncode != 0:
            continue
        before = {q["id"]: q for q in yaml.safe_load(old.stdout) or []}
        for q in yaml.safe_load((ROOT / path).read_text()) or []:
            b = before.get(q["id"])
            if b and b.get("text") and b.get("text") != q.get("text"):
                if not (q.get("verified") is True or (q.get("notes") and q.get("notes") != b.get("notes"))):
                    err(f"pyqs {q['id']}", "text changed without verified: true or a new notes: entry")


def lint_notes() -> None:
    topics = topics_by_id()
    for path in sorted((ROOT / "notes").rglob("*.md")):
        rel = path.relative_to(ROOT)
        tid = path.stem
        t = topics.get(tid)
        if t is None:
            err(str(rel), f"filename {tid} is not a topic id")
            continue
        if path.parent != ROOT / "notes" / t["paper"] / t["subject"]:
            err(str(rel), f"must live in notes/{t['paper']}/{t['subject']}/")
        meta, _ = split_front_matter(path.read_text())
        if meta is None:
            err(str(rel), "missing or invalid YAML front-matter")
            continue
        if meta.get("topic_id") != tid:
            err(str(rel), "front-matter topic_id must match the filename")
        if not meta.get("title"):
            err(str(rel), "front-matter needs title")
        if not isinstance(meta.get("sources"), list) or not meta["sources"]:
            err(str(rel), "front-matter sources must be a non-empty list")
        if meta.get("status") != "done":
            err(str(rel), "front-matter status must be `done` before merging (use `draft` while working locally)")


def lint_answers_and_images() -> None:
    topics = topics_by_id()
    for paper_dir in sorted((ROOT / "answers").glob("*")):
        if not paper_dir.is_dir():
            continue
        for d in sorted(paper_dir.iterdir()):
            if not d.is_dir():
                continue
            t = topics.get(d.name)
            if t is None or t["paper"] != paper_dir.name:
                err(str(d.relative_to(ROOT)), "answers/<paper>/<TOPIC-ID>/ must name an existing topic of that paper")
    for f in sorted((ROOT / "answers").rglob("*")):
        if not f.is_file() or f.suffix == ".md" or f.name == ".gitkeep":
            continue
        rel = str(f.relative_to(ROOT))
        ext = f.suffix.lower()
        if ext in {".heic", ".heif"}:
            err(rel, "HEIC is not supported; run scripts/compress_images.sh to convert to JPG")
        elif ext not in IMAGE_EXTS:
            err(rel, f"only {sorted(IMAGE_EXTS)} images are allowed under answers/")
        elif f.stat().st_size > MAX_IMAGE_BYTES:
            err(rel, f"{f.stat().st_size // 1000} KB > 1500 KB; run scripts/compress_images.sh")


def lint_links() -> None:
    for root in ("notes", "answers", "site"):
        for path in sorted((ROOT / root).rglob("*.md")):
            text = path.read_text()
            for target in LINK_RE.findall(text) + IMAGE_LINK_RE.findall(text):
                if re.match(r"^[a-z]+:|^#|^mailto:", target):
                    continue
                file_part = target.split("#", 1)[0]
                if root == "site" and file_part in GENERATED_PAGES:
                    continue
                if file_part and not (path.parent / file_part).exists():
                    err(str(path.relative_to(ROOT)), f"broken relative link `{target}`")


def default_base() -> str | None:
    if base := os.environ.get("BASE_SHA"):
        return base
    r = subprocess.run(["git", "merge-base", "origin/main", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip() or None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", help="commit to diff PYQ text against")
    args = ap.parse_args()
    lint_topics()
    lint_pyqs()
    lint_pyq_text_changes(args.base or default_base())
    lint_notes()
    lint_answers_and_images()
    lint_links()
    out = "\n".join(f"- ❌ {e}" for e in errors) if errors else "- ✅ all lint checks passed"
    print(out)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a") as f:
            f.write(f"### lint\n\n{out}\n")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
