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
- `syllabus/strategy.yaml` — PYQ-based strategy per topic (pattern, read for, answer approach, untested). Counts/years are computed from the bank at render time; only judgement lives here. Re-run `python scripts/create_issues.py` after editing it or the bank.
- `data/pyqs/gs{1,2,3}.yaml` — PYQ bank, 2013–2026 (2019 only polity). **Text is copied from sources, never written; scripts only read it** (`import_pyqs.py` fills text-pending entries from a CSV).
  - Ids: `<TOPIC>-M<YEAR>-Q<NN>` when the paper question number is known (2022–25); `<TOPIC>-M<YEAR>-S<NN>` (sequence within topic+year, `qno: null`) when it isn't (2013–21, 2026).
  - CI requires answers only from `REQUIRED_FROM_YEAR` (2022, in `scripts/common.py`); older PYQs are practice.
  - `notes: Topic mapping uncertain: …` marks entries whose topic assignment needs a human check.
- `notes/<paper>/<subject>/<ID>.md` — front-matter (`topic_id`, `title`, `status: draft|done`, `sources`) + one `## mN · …` section per micro-topic.
- `answers/<paper>/<ID>/pyqs.md` — one `## <PYQ-ID>` section per PYQ: verbatim quote + `![answer](img/<PYQ-ID>.jpg)`.
- `answers/<paper>/<ID>/img/` — scans (jpg/png/webp ≤ 1.5 MB; `scripts/compress_images.sh` converts HEIC).
- `site/index.md` — hand-written home page. Everything else on the site is generated into `build/` (git-ignored).

## Hard rules
- **Never generate, paraphrase or edit PYQ text.** Copy it only from `data/pyqs`. Flag suspected errors with a `pyq-unverified` issue.
- Do not write the author's notes or answers for them. Reviewing means applying `.github/REVIEW_RUBRIC.md`.
- **Handwritten notes:** the author often studies from books and shares scans of handwritten notes. Transcribe them faithfully into the topic note under the matching `## mN · …` headings — tidy structure and expand abbreviations, but add no facts that aren't in the scans. List micro-topics that are missing or under the CI minimum (≥80 words or ≥5 bullets) for the author to fill; ask about anything illegible instead of guessing.
- Never commit to `main` directly; never force-push.
