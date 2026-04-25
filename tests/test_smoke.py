from pathlib import Path


def test_repo_entrypoints_exist():
    root = Path(__file__).resolve().parents[1]
    assert (root / "frinkloop.py").exists()
    assert (root / "core" / "loop.py").exists()
