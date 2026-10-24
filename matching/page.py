"""Streamlit page for the explainable job-match analysis.

All scoring lives in ``matching.job_match`` / ``matching.bullet_coach`` (pure, tested).
This module only collects input, calls them, and renders the result with native
Streamlit widgets. User text is never injected into raw HTML.
"""
from __future__ import annotations

import streamlit as st

from ui_components import page_header
from .bullet_coach import analyze_bullets
from .history import append_history, build_history_entry, history_as_csv
from .job_match import ESTIMATE_DISCLAIMER, analyze_match
from .report import build_markdown_report
from .resume_io import ResumeFileError, extract_resume_text

SAMPLE_RESUME = """Alex Morgan
alex.morgan@example.com | github.com/alexmorgan

SUMMARY
Computer science graduate interested in backend and data engineering.

SKILLS
Python, SQL, Flask, PostgreSQL, Git, Docker, Pandas

EXPERIENCE
Software Engineering Intern, Example Labs (Jun 2024 - Aug 2024)
- Responsible for managing a Flask REST API used by the internal support team
- Wrote SQL queries and Pandas scripts to clean weekly export files
- Helped with deploying the service in Docker containers

PROJECTS
Expense Tracker
- Built a Flask and PostgreSQL web app for tracking personal spending
- Wrote unit tests with pytest for the budgeting logic

EDUCATION
B.Tech in Computer Science, Example University (2021 - 2025)
"""

SAMPLE_JOB = """Backend Engineer

Requirements:
- 2+ years of experience building backend services
- Strong Python and SQL skills
- Experience with REST APIs and PostgreSQL
- Familiarity with Docker and CI/CD pipelines
- Experience with AWS

Nice to have:
- Kubernetes
- Kafka
"""

_DEFAULTS = {"jm_resume_text": "", "jm_job_text": "", "jm_job_title": "", "jm_result": None,
             "jm_bullets": None, "jm_error": ""}


def _init_state() -> None:
    for key, value in _DEFAULTS.items():
        st.session_state.setdefault(key, value)
    st.session_state.setdefault("jm_history", [])


def _load_sample() -> None:
    st.session_state.jm_resume_text = SAMPLE_RESUME
    st.session_state.jm_job_text = SAMPLE_JOB
    st.session_state.jm_job_title = "Backend Engineer (sample)"
    st.session_state.jm_result = None
    st.session_state.jm_bullets = None
    st.session_state.jm_error = ""


def _clear() -> None:
    for key, value in _DEFAULTS.items():
        st.session_state[key] = value
    st.session_state["jm_upload_nonce"] = st.session_state.get("jm_upload_nonce", 0) + 1


def _run_analysis(upload) -> None:
    """Resolve the resume text (uploaded file wins over pasted text), then analyse."""
    st.session_state.jm_error = ""
    resume_text = st.session_state.jm_resume_text
    if upload is not None:
        try:
            resume_text = extract_resume_text(upload.name, upload.getvalue())
        except ResumeFileError as exc:
            st.session_state.jm_result = None
            st.session_state.jm_bullets = None
            st.session_state.jm_error = str(exc)
            return
    result = analyze_match(resume_text, st.session_state.jm_job_text)
    st.session_state.jm_result = result
    st.session_state.jm_bullets = analyze_bullets(resume_text) if result["status"] == "ok" else None
    if result["status"] == "ok":
        entry = build_history_entry(result, st.session_state.jm_job_title, resume_text)
        st.session_state.jm_history = append_history(st.session_state.jm_history, entry)


def _render_inputs():
    nonce = st.session_state.get("jm_upload_nonce", 0)
    left, right = st.columns(2, gap="large")
    with left:
        st.subheader("1. Your resume")
        upload = st.file_uploader("Upload a PDF or DOCX (max 5 MB)", type=["pdf", "docx"],
                                  key=f"jm_upload_{nonce}")
        st.text_area("Or paste the resume text", key="jm_resume_text", height=230,
                     placeholder="Paste your resume here if you are not uploading a file.",
                     help="If you upload a file, the file is used instead of this text.")
        if upload is not None and st.session_state.jm_resume_text.strip():
            st.caption("A file is uploaded, so the pasted text will be ignored.")
    with right:
        st.subheader("2. The job description")
        st.text_input("Job title (optional)", key="jm_job_title")
        st.text_area("Paste the full job posting", key="jm_job_text", height=230,
                     placeholder="Include the requirements section. Put nice-to-haves under a "
                                 "'Nice to have' or 'Preferred' heading so they are scored separately.")
    run, sample, clear, _ = st.columns([1.2, 1.2, 1, 3])
    run.button("Analyze match", type="primary", width='stretch',
               on_click=_run_analysis, args=(upload,))
    sample.button("Try sample data", width='stretch', on_click=_load_sample,
                  help="Fills both boxes with a fictional resume and job posting.")
    clear.button("Clear", width='stretch', on_click=_clear)


def _skill_list(items, missing: bool) -> None:
    if not items:
        st.caption("None")
        return
    for item in items:
        extra = ""
        if missing and item["related_in_resume"]:
            extra = f"  \n<small>Related on your resume: {', '.join(item['related_in_resume'])}</small>"
        if not missing and item["demonstrated_in_experience"] is False:
            extra = "  \n<small>Listed, but not shown in an experience or project bullet</small>"
        mark = "✗" if missing else "✓"
        st.markdown(f"**{mark} {item['skill']}**{extra}", unsafe_allow_html=True)
        if not missing and item["evidence"]:
            st.caption(f"Found in: \"{item['evidence']}\"")


def _render_overview(result) -> None:
    score_col, text_col = st.columns([1, 3])
    score_col.metric("Estimated match", f"{result['overall_score']}/100")
    with text_col:
        st.markdown(f"### {result['band']}")
        st.progress(result["overall_score"] / 100)
        st.caption(ESTIMATE_DISCLAIMER)
    st.markdown("#### How the estimate is calculated")
    rows = [{"Component": c["label"],
             "Score": f"{c['score']}/100" if c["applicable"] else "n/a",
             "Weight": f"{c['effective_weight']}%" if c["applicable"] else "not used",
             "Why": c["detail"]} for c in result["components"]]
    st.table(rows)  # st.table wraps long text; st.dataframe truncates it
    st.caption("Components that do not apply to this posting are left out and the remaining weights "
               "are rescaled to 100%.")
    for note in result["notes"]:
        st.caption(f"• {note}")


def _render_skills(result) -> None:
    for key, title in (("required", "Required skills"), ("preferred", "Preferred skills")):
        group = result[key]
        st.markdown(f"#### {title}")
        if not group["matched"] and not group["missing"]:
            st.caption("The posting lists none in this group.")
            continue
        matched_col, missing_col = st.columns(2)
        with matched_col:
            st.markdown(f"**Matched ({len(group['matched'])})**")
            _skill_list(group["matched"], missing=False)
        with missing_col:
            st.markdown(f"**Missing ({len(group['missing'])})**")
            _skill_list(group["missing"], missing=True)
    exp = result["experience"]
    st.markdown("#### Experience")
    years = exp["resume_years_estimate"]
    st.write(f"Estimated from your dates: **{years if years is not None else 'unknown'}** years "
             f"({exp['estimate_scope']}). Posting mentions: "
             f"**{', '.join(map(str, exp['posting_years_mentions'])) or 'no stated years'}**.")
    if result["extra_skills"]:
        st.markdown("#### Other skills on your resume")
        st.write(", ".join(result["extra_skills"]))


def _render_bullets(bullets) -> None:
    if not bullets or bullets["status"] != "ok":
        st.info((bullets or {}).get("message") or "No bullet points were found in the resume.")
        return
    summary = bullets["summary"]
    st.write(f"**{summary['needs_work']} of {summary['total']}** bullets have a medium-priority issue; "
             f"{summary['with_numbers']} contain a number.")
    st.caption("Suggestions never add facts. A rewritten opening appears only when it just rephrases your "
               "own words; everything else is feedback for you to act on truthfully.")
    for entry in bullets["repeated_openers"]:
        st.warning(f"\"{entry['verb']}\" starts {entry['count']} bullets. Vary your opening verbs.")
    for entry in bullets["bullets"]:
        if not entry["issues"]:
            continue
        with st.expander(entry["original"][:90] + ("…" if len(entry["original"]) > 90 else "")):
            st.text(entry["original"])
            if entry["suggested_rewrite"]:
                st.success(f"Suggested opening: {entry['suggested_rewrite']}")
            if entry["verb_options"]:
                st.caption("Neutral verbs to consider if one is accurate: " + ", ".join(entry["verb_options"]))
            for issue in entry["issues"]:
                st.markdown(f"- **{issue['message']}** {issue['why']}")


def _render_results() -> None:
    if st.session_state.jm_error:
        st.error(st.session_state.jm_error)
        return
    result = st.session_state.jm_result
    if result is None:
        st.info("Add your resume and a job description, then press **Analyze match**. "
                "Not sure where to start? Press **Try sample data**.")
        return
    if result["status"] != "ok":
        st.warning(result["message"])
        return
    overview, skills, bullets, steps = st.tabs(["Overview", "Skills", "Bullet coach", "Next steps"])
    with overview:
        _render_overview(result)
    with skills:
        _render_skills(result)
    with bullets:
        _render_bullets(st.session_state.jm_bullets)
    with steps:
        for i, tip in enumerate(result["recommendations"], 1):
            st.markdown(f"{i}. {tip}")
        if not result["recommendations"]:
            st.success("No gaps found against the skills this tool recognises.")
    st.download_button("Download report (Markdown)",
                       build_markdown_report(result, st.session_state.jm_bullets,
                                             st.session_state.jm_job_title),
                       file_name="job_match_report.md", mime="text/markdown")


def _render_history() -> None:
    history = st.session_state.get("jm_history", [])
    st.divider()
    st.subheader("Match history")
    st.caption("Your last 20 successful comparisons stay in this app session only. Resume and job text are not saved here.")
    st.caption(ESTIMATE_DISCLAIMER)
    if not history:
        st.info("Your completed comparisons will appear here.")
        return

    export_col, clear_col, _ = st.columns([1.5, 1, 4])
    export_col.download_button(
        "Download history (CSV)", history_as_csv(history),
        file_name="careerfit_match_history.csv", mime="text/csv",
        help="Exports role names, scores, and skill gaps. It does not include resume text.",
    )
    if clear_col.button("Clear history", key="jm_clear_history"):
        st.session_state.jm_history = []
        st.rerun()

    labels = {
        entry["id"]: f'{entry["created_at"][:16].replace("T", " ")} · '
                      f'{entry["job_title"]} · {entry["overall_score"]}/100'
        for entry in history
    }
    by_id = {entry["id"]: entry for entry in history}
    if len(history) >= 2:
        first_col, second_col = st.columns(2)
        first_id = first_col.selectbox("First comparison", list(labels), format_func=labels.get,
                                       key="jm_compare_first")
        second_options = [entry_id for entry_id in labels if entry_id != first_id]
        second_id = second_col.selectbox("Second comparison", second_options,
                                         format_func=labels.get,
                                         key=f"jm_compare_second_{first_id}")
        first, second = by_id[first_id], by_id[second_id]
        same_resume = first["resume_fingerprint"] == second["resume_fingerprint"]
        delta = int(second["overall_score"]) - int(first["overall_score"]) if same_resume else None
        score_cols = st.columns(2)
        score_cols[0].metric("First estimate", f'{first["overall_score"]}/100',
                             delta=f"{ -delta:+d} pts" if delta is not None else None,
                             delta_color="off")
        score_cols[1].metric("Second estimate", f'{second["overall_score"]}/100',
                             delta=f"{delta:+d} pts" if delta is not None else None,
                             delta_color="off")
        if same_resume:
            st.caption("The same normalized resume text was used, so the point difference compares these job postings.")
        else:
            st.caption("The resume text changed between these runs. Compare the estimates side by side; the difference also reflects the resume change.")
        st.markdown("**Missing skills**")
        gap_cols = st.columns(2)
        for col, entry, key in ((gap_cols[0], first, "missing_required"),
                                (gap_cols[1], second, "missing_required")):
            col.markdown(f'**{entry["job_title"]} · required**')
            col.write(", ".join(entry[key]) or "No required skill gaps found")
        for col, entry in ((gap_cols[0], first), (gap_cols[1], second)):
            col.markdown(f'**{entry["job_title"]} · preferred**')
            col.write(", ".join(entry["missing_preferred"]) or "No preferred skill gaps found")

    with st.expander(f"All saved comparisons ({len(history)})", expanded=len(history) < 2):
        st.dataframe(
            [{"Analyzed": entry["created_at"][:16].replace("T", " "),
              "Job": entry["job_title"], "Estimate": f'{entry["overall_score"]}/100',
              "Required matched": f'{entry["required_matched"]}/{entry["required_total"]}',
              "Missing required": ", ".join(entry["missing_required"]) or "None",
              "Missing preferred": ", ".join(entry["missing_preferred"]) or "None"}
             for entry in history],
            hide_index=True, use_container_width=True,
        )


def render_job_match() -> None:
    """Entry point used by app.py."""
    _init_state()
    page_header("Job Match", "See how your resume lines up with a specific job, and why")
    _render_inputs()
    st.divider()
    _render_results()
    _render_history()
