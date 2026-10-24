import re

import pytest

from matching import bullet_coach as bc


def codes(result):
    return [issue["code"] for issue in result["issues"]]


def tokens(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


@pytest.mark.parametrize("bullet,expected", [
    ("- Responsible for managing the deployment pipeline for the internal tool",
     "Managed the deployment pipeline for the internal tool"),
    ("Was responsible for testing the payments API before each release",
     "Tested the payments API before each release"),
    ("In charge of running the nightly build for the team",
     "Ran the nightly build for the team"),
    ("- I developed a REST API using Flask for the team", "Developed a REST API using Flask for the team"),
])
def test_faithful_mechanical_rewrites(bullet, expected):
    result = bc.analyze_bullet(bullet)
    assert result["suggested_rewrite"] == expected


@pytest.mark.parametrize("bullet", [
    "- Responsible for managing the deployment pipeline for the internal tool",
    "- Was responsible for testing the payments API before each release 3 times",
    "- I developed a REST API using Flask and MySQL for 3 teams",
    "- Responsible for supporting various customers etc",
])
def test_rewrites_never_add_words_or_numbers(bullet):
    """The core honesty guarantee: a rewrite may swap the opener only."""
    result = bc.analyze_bullet(bullet)
    rewrite = result["suggested_rewrite"]
    assert rewrite is not None
    added = tokens(rewrite) - tokens(result["original"])
    assert len(added) <= 1                                   # at most the new verb
    assert not any(ch.isdigit() for token in added for ch in token)
    assert rewrite.split(" ", 1)[1] in result["original"]    # tail is copied verbatim


@pytest.mark.parametrize("bullet", [
    "- Worked on the login page for the portal",
    "- Helped develop an inventory app for a local shop",
    "- Participated in daily standups with the platform team",
    "- Responsible for gardening the codebase now and then",   # unknown gerund
])
def test_ambiguous_openers_get_options_not_a_guessed_rewrite(bullet):
    result = bc.analyze_bullet(bullet)
    assert "weak_opener" in codes(result)
    assert result["suggested_rewrite"] is None
    assert result["verb_options"] and set(result["verb_options"]) <= set(bc.NEUTRAL_VERB_OPTIONS)


def test_neutral_options_do_not_claim_outcomes():
    claims = {"improved", "reduced", "increased", "led", "launched", "managed", "saved", "grew", "boosted"}
    assert not {v.lower() for v in bc.NEUTRAL_VERB_OPTIONS} & claims


def test_no_metrics_prompt_never_fabricates_numbers():
    result = bc.analyze_bullet("- Built a Flask API for the internal reporting tool")
    assert "no_numbers" in codes(result)
    assert result["suggested_rewrite"] is None
    message = next(i for i in result["issues"] if i["code"] == "no_numbers")
    assert "never estimate" in message["why"].lower()


def test_pronoun_is_judged_separately_from_the_verb():
    result = bc.analyze_bullet("- I developed a REST API using Flask and MySQL for 3 teams")
    assert "first_person" in codes(result) and "no_action_verb" not in codes(result)


def test_strong_bullet_has_no_serious_issues():
    result = bc.analyze_bullet("- Built a Flask API serving 1200 requests per day for the billing team")
    assert result["issues"] == [] and result["needs_work"] is False


def test_noun_phrase_opener_and_length_checks():
    assert "no_action_verb" in codes(bc.analyze_bullet("- Backend API for payments using Flask"))
    assert "too_long" in codes(bc.analyze_bullet("- Built " + "a very detailed system " * 12))
    assert "too_short" in codes(bc.analyze_bullet("- Fixed bugs"))
    assert "passive_voice" in codes(bc.analyze_bullet("- The dashboard was developed using React and Node"))
    assert "vague_words" in codes(bc.analyze_bullet("- Built various tools for many clients using Python"))


@pytest.mark.parametrize("value", [None, "", "   ", "-", "• "])
def test_empty_bullet_input_is_safe(value):
    result = bc.analyze_bullet(value)
    assert result["issues"] == [] and result["suggested_rewrite"] is None and result["needs_work"] is False


# ------------------------------ bullet extraction ------------------------- #
RESUME = """EXPERIENCE
Backend Developer, Orbit Systems   Jan 2023 - Present
- Responsible for managing the deployment pipeline
• Developed Python services and wrote unit tests with
  pytest for the billing module
 Developed a caching layer for 40k daily users
- Developed an admin dashboard in React
EDUCATION
- Graduated with honours from the university
"""


def test_extracts_only_experience_bullets_and_joins_wrapped_lines():
    bullets = bc.extract_bullets(RESUME)
    assert len(bullets) == 4
    assert "Developed Python services and wrote unit tests with pytest for the billing module" in bullets
    assert not any("Graduated" in b for b in bullets)


def test_falls_back_to_sentence_lines_when_there_are_no_bullet_markers():
    text = "Built a payments service in Python for an online retailer\nShort line\nJan 2020 - Dec 2021 Acme Corp Engineer"
    assert bc.extract_bullets(text) == ["Built a payments service in Python for an online retailer"]


def test_duplicates_removed_and_limit_applied():
    text = "- Built a thing for the team\n- built a thing for the team\n" + "".join(f"- Built item {i} for team\n" for i in range(50))
    bullets = bc.extract_bullets(text, limit=10)
    assert len(bullets) == 10 and len({b.lower() for b in bullets}) == 10


def test_analyze_bullets_summary_and_repeated_openers():
    result = bc.analyze_bullets(RESUME)
    assert result["status"] == "ok"
    assert result["summary"]["total"] == 4
    assert result["summary"]["needs_work"] == 1
    assert result["summary"]["with_numbers"] == 1
    assert result["repeated_openers"] == [{"verb": "developed", "count": 3}]


@pytest.mark.parametrize("text", ["", None, "   \n  ", "EXPERIENCE\n"])
def test_no_bullets_found_is_reported_gracefully(text):
    result = bc.analyze_bullets(text)
    assert result["status"] == "no_bullets" and result["message"] and result["bullets"] == []
