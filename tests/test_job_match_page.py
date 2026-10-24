"""UI flow tests for the Job Match page, run headlessly with Streamlit's AppTest."""
import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from matching.page import SAMPLE_JOB, SAMPLE_RESUME  # noqa: E402


def _page():
    from matching.page import render_job_match
    render_job_match()


def _app():
    at = AppTest.from_function(_page, default_timeout=30)
    return at.run()


def _button(at, label):
    return next(b for b in at.button if b.label == label)


def test_empty_state_has_no_error():
    at = _app()
    assert not at.exception
    assert any("Try sample data" in i.value for i in at.info)


def test_sample_data_flow_end_to_end():
    at = _app()
    _button(at, "Try sample data").click().run()
    assert at.text_area(key="jm_resume_text").value == SAMPLE_RESUME
    assert at.text_area(key="jm_job_text").value == SAMPLE_JOB
    _button(at, "Analyze match").click().run()
    assert not at.exception
    assert not at.error
    assert [t.label for t in at.tabs] == ["Overview", "Skills", "Bullet coach", "Next steps"]
    score = at.metric[0]
    assert score.label == "Estimated match"
    assert 0 <= int(score.value.split("/")[0]) <= 100
    # The estimate disclaimer must always be visible next to the score.
    assert any("not an official ATS score" in c.value for c in at.caption)


def test_missing_job_description_shows_warning_not_crash():
    at = _app()
    at.text_area(key="jm_resume_text").set_value(SAMPLE_RESUME).run()
    _button(at, "Analyze match").click().run()
    assert not at.exception
    assert any("job description" in w.value.lower() for w in at.warning)


def test_empty_resume_shows_warning():
    at = _app()
    at.text_area(key="jm_job_text").set_value(SAMPLE_JOB).run()
    _button(at, "Analyze match").click().run()
    assert not at.exception
    assert any("resume" in w.value.lower() for w in at.warning)


def test_clear_resets_results():
    at = _app()
    _button(at, "Try sample data").click().run()
    _button(at, "Analyze match").click().run()
    _button(at, "Clear").click().run()
    assert not at.exception
    assert at.text_area(key="jm_resume_text").value == ""
    assert len(at.tabs) == 0
