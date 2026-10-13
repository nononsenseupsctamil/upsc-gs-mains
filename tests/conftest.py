import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import common  # noqa: E402


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A scratch copy of the repo's data with empty notes/ and answers/."""
    for d in ("syllabus", "data", "site"):
        shutil.copytree(REPO / d, tmp_path / d)
    (tmp_path / "notes").mkdir()
    (tmp_path / "answers").mkdir()
    import build_site
    import check_completeness
    import lint
    for mod in (common, check_completeness, lint, build_site):
        monkeypatch.setattr(mod, "ROOT", tmp_path, raising=False)
    monkeypatch.setattr(build_site, "DOCS", tmp_path / "build/docs")
    common.load_topics.cache_clear()
    common.load_pyqs.cache_clear()
    common.load_strategy.cache_clear()
    lint.errors.clear()
    yield tmp_path
    common.load_topics.cache_clear()
    common.load_pyqs.cache_clear()
