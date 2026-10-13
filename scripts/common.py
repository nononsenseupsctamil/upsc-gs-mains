"""Shared helpers: repo paths, YAML loading and markdown parsing. Read-only with respect to the PYQ bank."""
from __future__ import annotations

import re
import subprocess
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
IST = timezone(timedelta(hours=5, minutes=30))

TOPIC_ID_RE = re.compile(r"^GS[123]-[A-Z]{2,3}-\d{2}$")
PYQ_ID_RE = re.compile(r"^(GS[123]-[A-Z]{2,3}-\d{2})-M(\d{4})-Q(\d{2})$")
TITLE_ID_RE = re.compile(r"^\[(GS[123]-[A-Z]+-\d{2})\]")
WORD_RE = re.compile(r"\b[\w'-]+\b")
BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\S")
PLACEHOLDER_RE = re.compile(r"\b(TODO|TBD|FIXME|placeholder)\b", re.IGNORECASE)
IMAGE_LINK_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
MICRO_HEADING_RE = re.compile(r"^m(\d+)\b")

PAPERS = ["gs1", "gs2", "gs3"]
SUBJECT_TITLES = {
    "history": "Modern History", "world-history": "World History", "culture": "Art & Culture",
    "geography": "Geography", "society": "Society", "polity": "Polity", "governance": "Governance",
    "social-justice": "Social Justice", "ir": "International Relations", "economy": "Economy",
    "agriculture": "Agriculture", "science-tech": "Science & Technology", "environment": "Environment",
    "disaster": "Disaster Management", "security": "Internal Security",
}
MILESTONES = {"M1 · Nov 13": date(2026, 11, 13), "M2 · Dec 13": date(2026, 12, 13),
              "M3 · Jan 13": date(2027, 1, 13), "M4 · Feb 13": date(2027, 2, 13)}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_BYTES = 1_500_000


@lru_cache(maxsize=None)
def load_topics() -> list[dict]:
    return yaml.safe_load((ROOT / "syllabus/issues.yaml").read_text()) or []


@lru_cache(maxsize=None)
def load_pyqs() -> list[dict]:
    out = []
    for p in PAPERS:
        out += yaml.safe_load((ROOT / f"data/pyqs/{p}.yaml").read_text()) or []
    return out


def topics_by_id() -> dict[str, dict]:
    return {t["topic_id"]: t for t in load_topics()}


def pyqs_for(topic_id: str, required_only: bool = False) -> list[dict]:
    """PYQs for a topic, newest first. required_only drops entries whose text is not imported yet."""
    qs = [q for q in load_pyqs() if q["topic_id"] == topic_id]
    if required_only:
        qs = [q for q in qs if q.get("confidence") != "text-pending" and q.get("text")]
    return sorted(qs, key=lambda q: (-q["year"], q["qno"]))


def note_path(t: dict) -> Path:
    return ROOT / "notes" / t["paper"] / t["subject"] / f"{t['topic_id']}.md"


def answers_dir(t: dict) -> Path:
    return ROOT / "answers" / t["paper"] / t["topic_id"]


def split_front_matter(text: str) -> tuple[dict | None, str]:
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 4)
    if end == -1:
        return None, text
    try:
        meta = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError:
        return None, text
    return (meta if isinstance(meta, dict) else None), text[end + 4:].lstrip("\n")


def h2_sections(text: str) -> dict[str, str]:
    """Map each '## heading' to the body text up to the next '## ' heading. Fenced code is ignored."""
    sections: dict[str, str] = {}
    current, buf, fenced = None, [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        if not fenced and line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(buf)
            current, buf = line[3:].strip(), []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf)
    return sections


def normalise(s: str) -> str:
    s = s.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip()


def merge_dates() -> dict[str, date]:
    """Date (IST) each note first landed in git history, keyed by topic id. Needs full history (fetch-depth: 0)."""
    out = subprocess.run(["git", "log", "--diff-filter=A", "--name-only", "--format=@%cI", "--", "notes/"],
                         cwd=ROOT, capture_output=True, text=True, check=False).stdout
    dates: dict[str, date] = {}
    when = None
    for line in out.splitlines():
        if line.startswith("@"):
            when = datetime.fromisoformat(line[1:]).astimezone(IST).date()
        elif line.strip().endswith(".md") and when and (ROOT / line.strip()).exists():
            tid = Path(line.strip()).stem
            dates[tid] = when  # log is newest first, so the last write wins: the first add
    return dates


def today_ist() -> date:
    return datetime.now(IST).date()
