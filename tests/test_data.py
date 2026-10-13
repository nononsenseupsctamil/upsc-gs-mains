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
