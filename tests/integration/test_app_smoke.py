from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_initializes_without_api_key() -> None:
    app = AppTest.from_file(Path(__file__).resolve().parents[2] / "app.py").run()
    assert not app.exception
    assert app.title[0].value == "CSV Data Quality Triage Agent"
