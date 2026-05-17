import pytest

from nv_engine.align import Aligner


def test_factory_raises_clear_error_without_stable_whisper(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "stable_whisper":
            raise ImportError("no stable_whisper")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    from nv_engine.align_stable import make_stable_aligner

    with pytest.raises(RuntimeError, match="stable-ts"):
        make_stable_aligner(model="small")


def test_stable_aligner_satisfies_protocol_when_available():
    sw = pytest.importorskip("stable_whisper")  # skip if not installed
    from nv_engine.align_stable import make_stable_aligner

    aligner = make_stable_aligner(model="tiny")
    assert isinstance(aligner, Aligner)  # structural Protocol check
