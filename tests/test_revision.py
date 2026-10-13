from datetime import date

import revision_schedule as rs


def test_due_on_intervals():
    merged = {"GS1-HIS-01": date(2026, 10, 20), "GS1-HIS-02": date(2026, 10, 14), "GS1-HIS-03": date(2026, 10, 20)}
    assert rs.due_on(date(2026, 10, 21), merged) == [("GS1-HIS-01", 1), ("GS1-HIS-03", 1), ("GS1-HIS-02", 7)]
    assert rs.due_on(date(2026, 11, 19), merged) == [("GS1-HIS-01", 30), ("GS1-HIS-03", 30)]
    assert rs.due_on(date(2027, 1, 18), merged) == [("GS1-HIS-01", 90), ("GS1-HIS-03", 90)]
    assert rs.due_on(date(2026, 10, 22), merged) == []


def test_render_sections():
    md = rs.render(date(2026, 10, 21), {"GS1-HIS-01": date(2026, 10, 20), "GS1-HIS-02": date(2026, 10, 13)})
    assert "### D+1" in md and "gs1/history/GS1-HIS-01.md" in md
    assert "## Missed (last 3 days)" in md and "GS1-HIS-02" in md   # D+7 fell on Oct 20
    assert "## Next 7 days" in md
