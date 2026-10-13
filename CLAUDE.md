# CLAUDE.md — upsc-gs-mains

Learning-in-public repo for UPSC CSE Mains GS1–GS3. One issue = one topic; one PR closes one issue.

## Workflow
- Branches: `study/<TOPIC-ID>` for topics, `chore/<slug>` for maintenance. Only `main` is long-lived. Squash-merge only.
- Every study PR body contains `Closes #N` (exactly one issue). Maintenance PRs carry the `chore` label instead.
- Start a topic: `git switch -c study/<ID> && python scripts/create_issues.py --scaffold <ID>`.
- Before pushing, run:
  - `python scripts/check_completeness.py --local <ID>`
  - `python scripts/lint.py`
  - `python scripts/build_site.py && zensical serve` (preview at http://localhost:8000)

## Layout
- `syllabus/issues.yaml` — topics, micro-topics (`m1…mN`, stable ids: append, never renumber), due dates. Source of truth for issues.
- `data/pyqs/gs{1,2,3}.yaml` — PYQ bank. **Human-maintained; scripts only read it.**
- `notes/<paper>/<subject>/<ID>.md` — front-matter (`topic_id`, `title`, `status: draft|done`, `sources`) + one `## mN · …` section per micro-topic.
- `answers/<paper>/<ID>/pyqs.md` — one `## <PYQ-ID>` section per PYQ: verbatim quote + `![answer](img/<PYQ-ID>.jpg)`.
- `answers/<paper>/<ID>/img/` — scans (jpg/png/webp ≤ 1.5 MB; `scripts/compress_images.sh` converts HEIC).
- `site/index.md` — hand-written home page. Everything else on the site is generated into `build/` (git-ignored).

## Hard rules
- **Never generate, paraphrase or edit PYQ text.** Copy it only from `data/pyqs`. Flag suspected errors with a `pyq-unverified` issue.
- Do not write the author's notes or answers for them. Reviewing means applying `.github/REVIEW_RUBRIC.md`.
- Never commit to `main` directly; never force-push.
