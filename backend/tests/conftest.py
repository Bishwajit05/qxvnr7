from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(autouse=True)
def isolated_data_provider(request, monkeypatch):
    """Existing historical regressions explicitly use the bundled test fixture.

    Live contract tests replace only urllib's upstream boundary and start with an
    empty provider. Production has no test/offline environment switch.
    """
    from app import service
    from app.elexon import ElexonProvider, load_snapshot

    if request.path.name == "test_live_api.py":
        selected = ElexonProvider()
    else:
        def unavailable():
            raise RuntimeError("Explicit historical test fixture")
        selected = ElexonProvider(loader=unavailable, fallback_loader=lambda: load_snapshot(service.DATA_DIR))
    monkeypatch.setattr(service, "provider", selected)
