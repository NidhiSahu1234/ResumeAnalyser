import csv
import io

from matching.history import append_history, build_history_entry, history_as_csv


def _result():
    return {
        "status": "ok",
        "overall_score": 72,
        "band": "Good alignment",
        "required": {
            "matched": [{"skill": "Python"}],
            "missing": [{"skill": "PostgreSQL"}],
        },
        "preferred": {"matched": [], "missing": [{"skill": "Kafka"}]},
        "components": [
            {"label": "Skills", "score": 80, "applicable": True},
            {"label": "Experience", "score": None, "applicable": False},
        ],
    }


def test_history_stores_comparison_metadata_without_source_text():
    resume = "Private Candidate Name\ncontact@example.test\nPython and Flask"
    entry = build_history_entry(_result(), "Backend Engineer", resume, "2026-10-24T10:00:00+05:30")

    assert entry["overall_score"] == 72
    assert entry["required_matched"] == 1
    assert entry["missing_required"] == ["PostgreSQL"]
    assert entry["component_scores"] == {"Skills": 80, "Experience": None}
    assert "resume_text" not in entry
    assert resume not in repr(entry)
    assert "contact@example.test" not in repr(entry)


def test_resume_fingerprint_normalizes_whitespace_but_changes_with_content():
    one = build_history_entry(_result(), "Role", "Python\nFlask")
    same = build_history_entry(_result(), "Role", " Python   Flask ")
    different = build_history_entry(_result(), "Role", "Python Flask SQL")

    assert one["resume_fingerprint"] == same["resume_fingerprint"]
    assert one["resume_fingerprint"] != different["resume_fingerprint"]


def test_history_is_bounded_and_newest_first():
    entries = [{"id": str(i)} for i in range(4)]
    updated = append_history(entries, {"id": "new"}, limit=3)

    assert [entry["id"] for entry in updated] == ["new", "0", "1"]
    assert len(entries) == 4


def test_csv_export_omits_fingerprint_and_private_resume_text():
    entry = build_history_entry(_result(), "Backend Engineer", "Sensitive resume contents")
    export = history_as_csv([entry])
    rows = list(csv.DictReader(io.StringIO(export)))

    assert rows[0]["overall_score"] == "72"
    assert "not an official ATS score" in rows[0]["estimate_type"]
    assert "resume_fingerprint" not in export
    assert "Sensitive resume contents" not in export


def test_unsuccessful_analysis_is_not_saved():
    try:
        build_history_entry({"status": "invalid"}, "Role", "Resume")
    except ValueError as exc:
        assert "successful" in str(exc)
    else:
        raise AssertionError("An unsuccessful analysis should not enter history.")
