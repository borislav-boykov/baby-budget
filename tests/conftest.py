import pytest

from baby_budget import i18n


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Bulgarian UI, and settings written to a temp dir instead of the real profile."""
    monkeypatch.setenv("BABY_BUDGET_CONFIG_DIR", str(tmp_path / "config"))
    i18n.set_language("bg")
    yield
    i18n.set_language("bg")
