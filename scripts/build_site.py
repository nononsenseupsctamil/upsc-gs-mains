"""Stage the revision site into build/docs and write zensical.toml. Then run `zensical build --clean`.

Each merged topic becomes one page: the note, followed by its PYQ answers with the scans.
Navigation is Paper → Subject → Topic, in syllabus/issues.yaml order.
"""
from __future__ import annotations

import json
import os
import re
import shutil
from datetime import date

import progress_page
import revision_schedule
from common import (IMAGE_LINK_RE, PAPERS, ROOT, SUBJECT_TITLES, answers_dir, load_topics, merge_dates, note_path,
                    split_front_matter, today_ist)

DOCS = ROOT / "build/docs"
PAPER_TITLES = {"gs1": "GS1 · History, Culture, Geography, Society",
                "gs2": "GS2 · Polity, Governance, Social Justice, IR",
                "gs3": "GS3 · Economy, S&T, Environment, Security"}


def toml_str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)  # JSON strings are valid TOML basic strings


def topic_page(t: dict) -> str:
    meta, body = split_front_matter(note_path(t).read_text())
    meta = meta or {}
    lines = [f"# {t['topic_id']} · {meta.get('title') or t['title']}", ""]
    srcs = meta.get("sources") or []
    if srcs:
        lines += ['!!! info "Sources"', ""] + [f"    - {s}" for s in srcs] + [""]
    lines += [body.rstrip(), ""]
    ap = answers_dir(t) / "pyqs.md"
    if ap.exists():
        answers = ap.read_text()
        # pyqs.md links scans as img/…; on the site they sit in <ID>-img/ next to the page.
        answers = IMAGE_LINK_RE.sub(lambda m: m.group(0).replace(f"({m.group(1)})", f"({t['topic_id']}-{m.group(1)})")
                                    if m.group(1).startswith("img/") else m.group(0), answers)
        answers = re.sub(r"^## ", "### ", answers, flags=re.M)
        answers = re.sub(r"^# .*\n?", "", answers, flags=re.M)
        lines += ["---", "", "## PYQ answers", "", answers.strip(), ""]
    return "\n".join(lines)


def build(today: date) -> list:
    if DOCS.exists():
        shutil.rmtree(DOCS)
    DOCS.mkdir(parents=True)
    shutil.copy(ROOT / "site/index.md", DOCS / "index.md")
    merged = merge_dates()
    nav: list = [{"Home": "index.md"}, {"Revise today": "revise-today.md"}, {"Progress": "progress.md"}]
    for paper in PAPERS:
        subjects: dict[str, list] = {}
        for t in load_topics():
            if t["paper"] != paper or not note_path(t).exists():
                continue
            rel = f"{paper}/{t['subject']}/{t['topic_id']}.md"
            (DOCS / rel).parent.mkdir(parents=True, exist_ok=True)
            (DOCS / rel).write_text(topic_page(t))
            img = answers_dir(t) / "img"
            if img.is_dir():
                shutil.copytree(img, DOCS / paper / t["subject"] / f"{t['topic_id']}-img")
            subjects.setdefault(t["subject"], []).append({f"{t['topic_id']} · {t['title']}": rel})
        if subjects:
            nav.append({PAPER_TITLES[paper]: [{SUBJECT_TITLES[s]: pages} for s, pages in subjects.items()]})
    (DOCS / "revise-today.md").write_text(revision_schedule.render(today, merged))
    (DOCS / "progress.md").write_text(progress_page.render(today, merged))
    return nav


def nav_toml(items: list, indent: int = 1) -> str:
    pad = "  " * indent
    parts = []
    for item in items:
        (title, target), = item.items()
        if isinstance(target, str):
            parts.append(f"{pad}{{ {toml_str(title)} = {toml_str(target)} }},")
        else:
            parts.append(f"{pad}{{ {toml_str(title)} = [\n{nav_toml(target, indent + 1)}\n{pad}] }},")
    return "\n".join(parts)


def main() -> None:
    nav = build(today_ist())
    tmpl = (ROOT / "zensical.toml.tmpl").read_text()
    site_url = os.environ.get("SITE_URL", "")
    (ROOT / "zensical.toml").write_text(tmpl.replace("__NAV__", "[\n" + nav_toml(nav) + "\n]")
                                        .replace("__SITE_URL__", toml_str(site_url)))
    pages = sum(1 for _ in DOCS.rglob("*.md"))
    print(f"staged {pages} pages in {DOCS.relative_to(ROOT)}; wrote zensical.toml")


if __name__ == "__main__":
    main()
