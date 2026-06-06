import pytest
import connectors.registry as reg


@pytest.fixture(autouse=True)
def reset_registry():
    original = dict(reg._REGISTRY)
    yield
    reg._REGISTRY.clear()
    reg._REGISTRY.update(original)


def _ok_connector(**kwargs) -> dict:
    return {"status": "ok", "data": {"called": True, "kwargs": kwargs}, "error": None}


def test_execute_missing_connector():
    result = reg.execute("nonexistent")
    assert result["status"] == "error"
    assert "not available" in result["error"]


def test_register_and_execute():
    reg.register("test_ok", _ok_connector)
    result = reg.execute("test_ok")
    assert result["status"] == "ok"
    assert result["data"]["called"] is True


def test_execute_passes_kwargs():
    reg.register("echo", _ok_connector)
    result = reg.execute("echo", area="studies")
    assert result["data"]["kwargs"]["area"] == "studies"


def test_available_lists_non_none():
    reg.register("active", _ok_connector)
    reg._REGISTRY["inactive"] = None
    names = reg.available()
    assert "active" in names
    assert "inactive" not in names


def test_execute_catches_connector_exception():
    def broken(**kwargs) -> dict:
        raise RuntimeError("boom")

    reg.register("broken", broken)
    result = reg.execute("broken")
    assert result["status"] == "error"
    assert "boom" in result["error"]
