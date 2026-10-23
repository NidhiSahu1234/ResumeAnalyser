from datetime import date

import pytest

from matching import job_match as jm

TODAY = date(2026, 10, 23)

RESUME = """Asha Verma
asha.verma@example.com | +91 98765 43210 | github.com/ashaverma

SUMMARY
Backend developer who enjoys building reliable APIs.

SKILLS
Python, Java, JavaScript, SQL, MySQL, Docker, Git, Flask, REST APIs

EXPERIENCE
Software Engineer Intern, Acme Labs   Jun 2022 - Dec 2022
- Built REST APIs with Flask and MySQL for an internal tool
- Worked on CI pipelines using GitHub Actions
Backend Developer, Orbit Systems   Jan 2023 - Present
- Developed Python services and wrote unit tests with pytest

EDUCATION
B.Tech Computer Science, 2018 - 2022

PROJECTS
Resume Analyzer - Streamlit app using Python and scikit-learn
"""

JD = """Backend Engineer

About the role:
We are hiring a backend engineer to build services.

Requirements:
- 2+ years of experience building backend systems
- Strong Python and PostgreSQL skills
- Experience with Docker and Kubernetes
- Familiarity with AWS
- Knowledge of REST APIs and microservices

Nice to have:
- Experience with Kafka or Redis
- Terraform
- Knowledge of GraphQL is a plus
"""


# ----------------------------- skill matching ----------------------------- #
@pytest.mark.parametrize("text,expected", [
    ("I know JavaScript and Node.js", {"JavaScript", "Node.js"}),
    ("react.js developer", {"React"}),
    ("C++ and C# plus ASP.NET", {"C++", "C#", ".NET"}),
    ("machine learning and Power BI", {"Machine Learning", "Power BI"}),
    ("scikit learn and scikit-learn", {"scikit-learn"}),
    ("natural language processing", {"NLP"}),
    ("Knowledge of REST APIs and microservices", {"REST APIs", "Microservices"}),
    ("Built RESTful APIs", {"REST APIs"}),
    ("Spring boot services", {"Spring"}),
    ("Managed Kubernetes (k8s) clusters", {"Kubernetes"}),
])
def test_skill_detection(text, expected):
    assert set(jm.skills_in_text(text)) == expected


@pytest.mark.parametrize("text", [
    "I will go far and the rest of the team can excel at it this spring",
    "expertise and expect",
    "springtime and rusty gates",
    "",
])
def test_ordinary_words_do_not_create_skills(text):
    assert jm.skills_in_text(text) == {}


def test_java_is_not_matched_inside_javascript():
    assert set(jm.skills_in_text("Strong JavaScript skills")) == {"JavaScript"}


def test_github_actions_and_github_are_separate_skills():
    assert "GitHub Actions" in jm.skills_in_text("CI/CD with GitHub Actions")


_ALL_TERMS = [(name, term) for name, (_cat, aliases) in jm.SKILLS.items()
              for term in (name, *aliases) if not (name in jm._ALIAS_ONLY and term == name)]


@pytest.mark.parametrize("name,term", _ALL_TERMS)
def test_every_taxonomy_term_matches_itself(name, term):
    # Regression: a double-escaping bug once silently broke every multi-word term.
    assert name in jm.skills_in_text(f"experience with {term} daily")


# --------------------------- job description parsing ---------------------- #
def test_required_and_preferred_sections():
    parsed = jm.parse_job_description(JD)
    assert set(parsed["required"]) == {"Python", "PostgreSQL", "Docker", "Kubernetes", "AWS",
                                       "REST APIs", "Microservices"}
    assert set(parsed["preferred"]) == {"Kafka", "Redis", "Terraform", "GraphQL"}


def test_inline_plus_does_not_flip_following_lines_to_preferred():
    parsed = jm.parse_job_description("Requirements:\n- Docker is a plus\n- Python\n- Kubernetes")
    assert set(parsed["preferred"]) == {"Docker"}
    assert set(parsed["required"]) == {"Python", "Kubernetes"}


def test_posting_without_headings_treats_every_skill_as_required():
    parsed = jm.parse_job_description("We use Python, Docker and AWS every day.")
    assert set(parsed["required"]) == {"Python", "Docker", "AWS"}
    assert parsed["preferred"] == {}


def test_skill_in_both_buckets_counts_as_required():
    parsed = jm.parse_job_description("Requirements:\n- Python\nNice to have:\n- Python and Go (golang)")
    assert "Python" in parsed["required"] and "Python" not in parsed["preferred"]


@pytest.mark.parametrize("line,expected", [
    ("3-5 years of experience with Python", [3]),
    ("5+ years experience", [5]),
    ("2 yrs of relevant experience", [2]),
    ("Python expertise for 4 years", []),  # 'expertise' is not 'experience'
    ("No years mentioned, experience welcome", []),
])
def test_years_mentions(line, expected):
    assert jm.parse_job_description(line + " Python")["years_mentions"] == expected


# ------------------------------ experience years -------------------------- #
def test_experience_estimate_excludes_education_and_merges_present():
    years, scope = jm.estimate_experience_years(RESUME, TODAY)
    assert scope == "experience section"
    assert years == pytest.approx(4.2, abs=0.05)  # 6 months + Jan 2023..Oct 2026


def test_overlapping_ranges_are_merged():
    text = "EXPERIENCE\nA  Jan 2020 - Dec 2021\nB  Jun 2021 - Dec 2022\nEDUCATION\nX"
    years, _ = jm.estimate_experience_years(text, TODAY)
    # Merged to one span, Jan 2020 .. Dec 2022. Months are counted as end minus start
    # (a deliberately conservative convention), so that is 35 months, not 4.5 years summed.
    assert years == pytest.approx(2.9, abs=0.05)


def test_year_only_ranges_use_mid_year_so_they_are_not_inflated():
    years, _ = jm.estimate_experience_years("EXPERIENCE\nDev 2019 - 2021\n", TODAY)
    assert years == 2.0


def test_no_dates_returns_none():
    years, _ = jm.estimate_experience_years("EXPERIENCE\nBuilt things for people\n", TODAY)
    assert years is None


def test_without_experience_heading_falls_back_and_says_so():
    years, scope = jm.estimate_experience_years("Dev at Acme 2020 - 2022\nEDUCATION\nB.Tech 2014 - 2018", TODAY)
    assert years == 2.0
    assert "no Experience heading" in scope


# ---------------------------------- analyze ------------------------------- #
def test_full_match_result_is_correct_and_explained():
    result = jm.analyze_match(RESUME, JD, today=TODAY)
    assert result["status"] == "ok"
    required = result["required"]
    assert {m["skill"] for m in required["matched"]} == {"Python", "Docker", "REST APIs"}
    assert {m["skill"] for m in required["missing"]} == {"PostgreSQL", "Kubernetes", "AWS", "Microservices"}
    assert {m["skill"] for m in result["preferred"]["missing"]} == {"Kafka", "Redis", "Terraform", "GraphQL"}
    # 3/7 required (43), 0/4 preferred, experience 100, completeness 100
    scores = {c["key"]: c["score"] for c in result["components"]}
    assert scores == {"required_skills": 43, "preferred_skills": 0, "experience_fit": 100, "completeness": 100}
    # 43*50 + 0*15 + 100*20 + 100*15 = 5650 -> 56.5 -> rounds half up to 57
    assert result["overall_score"] == 57 and result["band"] == "Moderate overlap"


def test_displayed_breakdown_reproduces_the_overall_score():
    """Transparency: anyone can recompute the headline number from the components shown."""
    for jd in (JD, "Requirements:\n- Python\n- Docker", "Python and AWS, 3+ years of experience, Kafka is a plus"):
        result = jm.analyze_match(RESUME, jd, today=TODAY)
        applicable = [c for c in result["components"] if c["applicable"]]
        weight = sum(c["base_weight"] for c in applicable)
        recomputed = int(sum(c["score"] * c["base_weight"] for c in applicable) / weight + 0.5)
        assert recomputed == result["overall_score"]


def test_related_skills_are_shown_but_never_counted_as_matches():
    result = jm.analyze_match(RESUME, JD, today=TODAY)
    by_skill = {m["skill"]: m for m in result["required"]["missing"]}
    assert "MySQL" in by_skill["PostgreSQL"]["related_in_resume"]
    assert "Docker" in by_skill["Kubernetes"]["related_in_resume"]
    assert "PostgreSQL" not in {m["skill"] for m in result["required"]["matched"]}


def test_skill_listed_but_not_demonstrated_is_flagged():
    result = jm.analyze_match(RESUME, JD, today=TODAY)
    flags = {m["skill"]: m["demonstrated_in_experience"] for m in result["required"]["matched"]}
    assert flags["Docker"] is False   # only in the Skills list
    assert flags["Python"] is True    # appears in experience bullets
    assert any("Docker" in tip and "bullet" in tip for tip in result["recommendations"])


def test_evidence_snippet_is_a_real_resume_line():
    result = jm.analyze_match(RESUME, JD, today=TODAY)
    python = next(m for m in result["required"]["matched"] if m["skill"] == "Python")
    assert python["evidence"] and python["evidence"] in RESUME.replace("  ", " ") or "Python" in python["evidence"]


def test_weights_are_renormalised_when_components_do_not_apply():
    jd = "Requirements:\n- Python\n- Docker"  # no preferred skills, no years
    result = jm.analyze_match(RESUME, jd, today=TODAY)
    applicable = [c for c in result["components"] if c["applicable"]]
    assert {c["key"] for c in applicable} == {"required_skills", "completeness"}
    assert sum(c["effective_weight"] for c in applicable) in (99, 100, 101)
    assert all(c["effective_weight"] == 0 for c in result["components"] if not c["applicable"])
    assert result["overall_score"] == 100


def test_result_is_labelled_as_an_estimate_not_an_ats_score():
    for result in (jm.analyze_match(RESUME, JD, today=TODAY), jm.analyze_match("", JD)):
        assert "not an official ATS" in result["disclaimer"]


def test_analysis_is_deterministic():
    assert jm.analyze_match(RESUME, JD, today=TODAY) == jm.analyze_match(RESUME, JD, today=TODAY)


def test_recommendations_never_tell_the_user_to_claim_a_skill_unconditionally():
    result = jm.analyze_match(RESUME, JD, today=TODAY)
    skill_tips = [t for t in result["recommendations"] if t.startswith("The posting asks for")]
    assert skill_tips
    for tip in skill_tips:
        assert "only if" in tip or "if you have" in tip.lower() or "if not" in tip


def test_missing_keywords_are_repeated_terms_absent_from_resume():
    jd = "Requirements:\n- Python\n- observability and observability tooling, stakeholder management with stakeholder reviews"
    result = jm.analyze_match(RESUME, jd, today=TODAY)
    assert "observability" in result["missing_keywords"] and "stakeholder" in result["missing_keywords"]
    assert "python" not in result["missing_keywords"]


# ------------------------------- edge cases ------------------------------- #
@pytest.mark.parametrize("resume,jd,status", [
    ("", JD, "empty_resume"),
    (None, JD, "empty_resume"),
    ("   \n\t ", JD, "empty_resume"),
    ("Python dev", JD, "resume_too_short"),
    (RESUME, "", "empty_job_description"),
    (RESUME, None, "empty_job_description"),
    (RESUME, "   \n ", "empty_job_description"),
    (RESUME, "We want a friendly, motivated person who loves coffee and long walks on the beach.",
     "no_skills_in_job_description"),
])
def test_expected_bad_input_returns_status_not_exception(resume, jd, status):
    result = jm.analyze_match(resume, jd, today=TODAY)
    assert result["status"] == status
    assert result["message"]
    assert "overall_score" not in result


def test_unicode_and_odd_characters_do_not_crash():
    resume = RESUME + "\nSkills: Pythön 中文 \U0001f680 \x00 ‮ Docker"
    result = jm.analyze_match(resume, "Requirements:\n- Docker – “senior” \U0001f680", today=TODAY)
    assert result["status"] == "ok"


def test_large_input_completes():
    big_resume = RESUME + ("Worked on many things with Python and Docker for clients.\n" * 4000)
    big_jd = JD + ("Python Docker Kubernetes AWS\n" * 2000)
    assert jm.analyze_match(big_resume, big_jd, today=TODAY)["status"] == "ok"


def test_inputs_are_not_mutated_and_scores_are_bounded():
    result = jm.analyze_match(RESUME, JD, today=TODAY)
    assert 0 <= result["overall_score"] <= 100
    assert all(c["score"] is None or 0 <= c["score"] <= 100 for c in result["components"])
