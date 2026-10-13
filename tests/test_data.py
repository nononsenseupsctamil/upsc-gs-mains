"""The real syllabus and PYQ bank satisfy the schema."""
import common
import lint


def test_bank_and_syllabus_lint_clean():
    common.load_topics.cache_clear()
    common.load_pyqs.cache_clear()
    lint.errors.clear()
    lint.lint_topics()
    lint.lint_pyqs()
    assert lint.errors == []


def test_counts():
    topics = common.load_topics()
    assert [sum(t["paper"] == p for t in topics) for p in common.PAPERS] == [32, 29, 27]
    for p in common.PAPERS:
        for year in (2022, 2023, 2024, 2025):
            qs = [q for q in common.load_pyqs() if q["paper"] == p.upper() and q["year"] == year]
            assert sorted(q["qno"] for q in qs) == list(range(1, 21))


def test_every_topic_has_strategy_and_it_renders():
    strategy = common.load_strategy()
    assert set(strategy) == {t["topic_id"] for t in common.load_topics()}
    md = common.strategy_markdown("GS1-GEO-02")
    assert "very high" in md and "7 questions" in md and "**Read for:**" in md


def test_strategy_shows_names_not_ids():
    md = common.strategy_markdown("GS1-HIS-01")
    assert "*Why the Company won* is the core" in md
    assert not common.MICRO_REF_RE.search(md)
