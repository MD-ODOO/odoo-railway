from pathlib import Path


def test_no_legacy_sql_constraints():
    root = Path(__file__).parents[1]
    assert not any("_sql_constraints" in p.read_text() for p in (root / "models").glob("*.py"))

def test_no_depends_id():
    root = Path(__file__).parents[1]
    assert not any('@api.depends("id")' in p.read_text() for p in (root / "models").glob("*.py"))
