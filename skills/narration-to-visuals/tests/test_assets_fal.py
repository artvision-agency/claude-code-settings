import pytest

from nv_engine.assets import ImageGenerator


def test_factory_raises_clear_error_without_fal(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "fal_client":
            raise ImportError("no fal_client")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    from nv_engine.assets_fal import make_fal_generator

    with pytest.raises(RuntimeError, match="fal"):
        make_fal_generator()


def test_factory_raises_without_api_key(monkeypatch):
    pytest.importorskip("fal_client")
    monkeypatch.delenv("FAL_KEY", raising=False)
    from nv_engine.assets_fal import make_fal_generator

    with pytest.raises(RuntimeError, match="FAL_KEY"):
        make_fal_generator()


def test_fal_generator_satisfies_protocol_when_available(monkeypatch):
    pytest.importorskip("fal_client")
    monkeypatch.setenv("FAL_KEY", "x")
    from nv_engine.assets_fal import make_fal_generator

    assert isinstance(make_fal_generator(), ImageGenerator)
