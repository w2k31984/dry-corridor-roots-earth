from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def test_app_renders_verdict_and_demos():
    at = AppTest.from_file(APP, default_timeout=180).run()
    assert not at.exception
    assert any("Veredicto del detective" in m.value for m in at.success) or any(
        "Veredicto del detective" in m.value for m in [*at.info, *at.warning])
    at.button[1].click().run()
    assert not at.exception
    assert at.session_state["var"] == "T2M"
    assert any("Veredicto del detective" in m.value for m in at.success)
