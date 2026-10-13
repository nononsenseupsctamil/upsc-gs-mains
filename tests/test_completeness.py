import check_completeness as cc
import common
import lint

TID = "GS2-POL-04"


def write_topic(root, words=90, quote=True, scan=True):
    t = common.topics_by_id()[TID]
    body = "\n\n".join(f"## {m['id']} · {m['text']}\n\n" + ("word " * words) for m in t["micro_syllabus"])
    note = root / "notes/gs2/polity" / f"{TID}.md"
    note.parent.mkdir(parents=True)
    note.write_text(f"---\ntopic_id: {TID}\ntitle: Federalism I\nstatus: done\nsources: [Laxmikanth]\n---\n\n{body}\n")
    ad = root / "answers/gs2" / TID
    (ad / "img").mkdir(parents=True)
    blocks = []
    for q in common.pyqs_for(TID, required_only=True):
        (ad / "img" / f"{q['id']}.jpg").write_bytes(b"\xff\xd8 fake jpeg")
        blocks.append(f"## {q['id']}\n\n" + (f"> {q['text']}\n" if quote else "") +
                      (f"\n![answer](img/{q['id']}.jpg)\n" if scan else ""))
    (ad / "pyqs.md").write_text("\n".join(blocks))
    return t


def failures(rows):
    return [r for r in rows if not r[1]]


def test_complete_topic_passes(repo):
    write_topic(repo)
    assert failures(cc.check_topic(TID)) == []
    lint.lint_notes()
    lint.lint_answers_and_images()
    lint.lint_links()
    assert lint.errors == []


def test_thin_micro_section_fails(repo):
    write_topic(repo, words=10)
    assert any(r[0].startswith("m1 ·") for r in failures(cc.check_topic(TID)))


def test_missing_quote_and_scan_fail(repo):
    write_topic(repo, quote=False, scan=False)
    bad = failures(cc.check_topic(TID))
    assert bad and all("verbatim" in r[2] and "scan" in r[2] for r in bad)


def test_missing_note_fails(repo):
    assert any("missing" in r[2] for r in failures(cc.check_topic(TID)))


def test_draft_status_fails_lint(repo):
    write_topic(repo)
    note = repo / "notes/gs2/polity" / f"{TID}.md"
    note.write_text(note.read_text().replace("status: done", "status: draft"))
    lint.lint_notes()
    assert any("status" in e for e in lint.errors)


def test_build_site_stages_topic_with_scans(repo):
    import build_site
    write_topic(repo)
    nav = build_site.build(common.today_ist())
    page = (repo / "build/docs/gs2/polity" / f"{TID}.md").read_text()
    assert "## PYQ answers" in page and f"({TID}-img/" in page
    assert (repo / "build/docs/gs2/polity" / f"{TID}-img").is_dir()
    assert any("GS2" in list(n)[0] for n in nav)
