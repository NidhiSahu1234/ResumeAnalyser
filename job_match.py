"""Explainable resume <-> job description matching.

Deterministic and offline: no network calls, no ML models, standard library only.
Every number returned can be traced to a visible rule. The result is a heuristic
estimate of keyword/skill overlap -- it is NOT an ATS score and does not predict
what any employer's software or recruiter will do.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Dict, List, Optional, Tuple

ESTIMATE_DISCLAIMER = (
    "Heuristic estimate of skill and keyword overlap. This is not an official ATS "
    "score and does not predict how any employer's system or recruiter will respond."
)

# --------------------------------------------------------------------------- #
# Skill taxonomy: display name -> (category, extra aliases)
# The lower-cased display name is always matched too. Short or ambiguous words
# ("go", "r", "c", "express", "spring", "excel") are deliberately matched only
# through unambiguous aliases so ordinary prose does not create false matches.
# --------------------------------------------------------------------------- #
SKILLS: Dict[str, Tuple[str, Tuple[str, ...]]] = {
    # Languages
    "Python": ("language", ()),
    "Java": ("language", ()),
    "JavaScript": ("language", ("js", "ecmascript", "es6")),
    "TypeScript": ("language", ()),
    "C++": ("language", ("cpp",)),
    "C#": ("language", ("csharp", "c sharp")),
    "C": ("language", ("c programming", "c language")),
    "Go": ("language", ("golang",)),
    "Rust": ("language", ()),
    "Kotlin": ("language", ()),
    "Swift": ("language", ("swiftui", "swift programming", "swift language")),
    "PHP": ("language", ()),
    "Ruby": ("language", ("ruby on rails", "rails")),
    "Scala": ("language", ()),
    "R": ("language", ("r programming", "r language", "rstudio")),
    "MATLAB": ("language", ()),
    "SQL": ("language", ("t-sql", "pl/sql", "plsql", "pl-sql")),
    "Bash": ("language", ("shell scripting", "shell script", "shell scripts")),
    "HTML": ("frontend", ("html5",)),
    "CSS": ("frontend", ("css3", "scss", "sass")),
    "Dart": ("language", ()),
    # Frontend / mobile
    "React": ("frontend", ("react.js", "reactjs")),
    "Angular": ("frontend", ("angularjs", "angular.js")),
    "Vue": ("frontend", ("vue.js", "vuejs")),
    "Next.js": ("frontend", ("nextjs",)),
    "Redux": ("frontend", ()),
    "Tailwind CSS": ("frontend", ("tailwind",)),
    "Bootstrap": ("frontend", ()),
    "jQuery": ("frontend", ()),
    "Flutter": ("mobile", ()),
    "React Native": ("mobile", ()),
    "Android": ("mobile", ()),
    "iOS": ("mobile", ()),
    # Backend
    "Node.js": ("backend", ("node", "nodejs", "node js")),
    "Express.js": ("backend", ("expressjs", "express js")),
    "Django": ("backend", ()),
    "Flask": ("backend", ()),
    "FastAPI": ("backend", ()),
    "Spring": ("backend", ("spring boot", "spring framework", "spring mvc")),
    ".NET": ("backend", ("dotnet", "asp.net", ".net core")),
    "GraphQL": ("backend", ()),
    "REST APIs": ("backend", ("rest api", "restful", "restful api", "restful apis")),
    "Microservices": ("backend", ("microservice",)),
    "Kafka": ("backend", ("apache kafka",)),
    "RabbitMQ": ("backend", ()),
    # Data / ML
    "Machine Learning": ("data_ml", ("ml",)),
    "Deep Learning": ("data_ml", ()),
    "NLP": ("data_ml", ("natural language processing",)),
    "Computer Vision": ("data_ml", ()),
    "TensorFlow": ("data_ml", ()),
    "PyTorch": ("data_ml", ()),
    "Keras": ("data_ml", ()),
    "scikit-learn": ("data_ml", ("sklearn", "scikit learn")),
    "Pandas": ("data_ml", ()),
    "NumPy": ("data_ml", ()),
    "Data Analysis": ("data_ml", ("data analytics",)),
    "Data Visualization": ("data_ml", ("data visualisation",)),
    "Statistics": ("data_ml", ("statistical analysis",)),
    "Power BI": ("data_ml", ("powerbi",)),
    "Tableau": ("data_ml", ()),
    "Spark": ("data_ml", ("apache spark", "pyspark", "spark sql", "spark streaming")),
    "Hadoop": ("data_ml", ()),
    "Airflow": ("data_ml", ("apache airflow",)),
    "ETL": ("data_ml", ("data pipelines", "data pipeline")),
    "LLMs": ("data_ml", ("llm", "large language models", "large language model")),
    "Excel": ("data_ml", ("microsoft excel", "ms excel", "advanced excel", "pivot tables")),
    # Databases
    "PostgreSQL": ("database", ("postgres",)),
    "MySQL": ("database", ()),
    "SQLite": ("database", ()),
    "SQL Server": ("database", ("mssql", "microsoft sql server")),
    "Oracle": ("database", ("oracle db", "oracle database")),
    "MongoDB": ("database", ("mongo",)),
    "Redis": ("database", ()),
    "Elasticsearch": ("database", ("elastic search",)),
    "DynamoDB": ("database", ()),
    "Cassandra": ("database", ()),
    "Firebase": ("database", ()),
    # Cloud / DevOps
    "AWS": ("cloud_devops", ("amazon web services",)),
    "Azure": ("cloud_devops", ("microsoft azure",)),
    "GCP": ("cloud_devops", ("google cloud", "google cloud platform")),
    "Docker": ("cloud_devops", ()),
    "Kubernetes": ("cloud_devops", ("k8s",)),
    "Terraform": ("cloud_devops", ()),
    "Ansible": ("cloud_devops", ()),
    "CI/CD": ("cloud_devops", ("cicd", "continuous integration", "continuous delivery",
                                "continuous deployment")),
    "Jenkins": ("cloud_devops", ()),
    "GitHub Actions": ("cloud_devops", ()),
    "GitLab CI": ("cloud_devops", ("gitlab ci/cd",)),
    "Linux": ("cloud_devops", ("unix",)),
    "Nginx": ("cloud_devops", ()),
    "Serverless": ("cloud_devops", ("aws lambda", "lambda functions")),
    # Tools / practices
    "Git": ("tools", ()),
    "GitHub": ("tools", ()),
    "Jira": ("tools", ()),
    "Postman": ("tools", ()),
    "Figma": ("tools", ()),
    "Unit Testing": ("practice", ("unit tests", "unit test", "pytest", "junit", "jest")),
    "Test Automation": ("practice", ("selenium", "cypress", "automated testing")),
    "TDD": ("practice", ("test-driven development", "test driven development")),
    "Agile": ("practice", ()),
    "Scrum": ("practice", ()),
    "Kanban": ("practice", ()),
    "System Design": ("practice", ("distributed systems", "software architecture")),
    "Data Structures": ("practice", ("data structures and algorithms", "dsa")),
    "Algorithms": ("practice", ()),
    "OOP": ("practice", ("object-oriented", "object oriented", "object-oriented programming")),
    "Design Patterns": ("practice", ()),
    "Code Review": ("practice", ("code reviews", "pull requests")),
    "Cybersecurity": ("practice", ("information security", "application security", "owasp")),
    "OAuth": ("practice", ("oauth2", "jwt")),
    "Streamlit": ("tools", ()),
}

# Skills that are "close cousins" -- shown as related experience, never counted as a match.
RELATED_GROUPS: List[Tuple[str, ...]] = [
    ("PostgreSQL", "MySQL", "SQL Server", "Oracle", "SQLite", "SQL"),
    ("MongoDB", "DynamoDB", "Cassandra", "Firebase", "Redis"),
    ("AWS", "Azure", "GCP"),
    ("React", "Angular", "Vue", "Next.js"),
    ("TensorFlow", "PyTorch", "Keras"),
    ("Django", "Flask", "FastAPI"),
    ("Jenkins", "GitHub Actions", "GitLab CI", "CI/CD"),
    ("Docker", "Kubernetes"),
    ("Power BI", "Tableau", "Data Visualization"),
    ("Spring", "Django", "Flask", "FastAPI", "Express.js", ".NET", "Node.js"),
    ("Scrum", "Agile", "Kanban"),
    ("Java", "C#", "Kotlin", "C++"),
    ("Pandas", "NumPy", "Data Analysis"),
]

# --------------------------------------------------------------------------- #
# Skill matching
# --------------------------------------------------------------------------- #
_LOOKBEHIND = r"(?<![A-Za-z0-9+#.])"
_LOOKAHEAD = r"(?![A-Za-z0-9+#])"


def _term_to_regex(term: str) -> str:
    """Whole-token regex for a skill term. Spaces and hyphens inside a term match each other
    ("scikit-learn" == "scikit learn"). Built by split-and-join so nothing is escaped twice."""
    parts = [re.escape(part) for part in re.split(r"[ \-]+", term.lower()) if part]
    return _LOOKBEHIND + r"[\s\-]+".join(parts) + _LOOKAHEAD


# Names that are ordinary English words or single letters. Matching the bare name would
# create false positives ("will go far", "this spring", "excel at"), so for these skills
# only the explicit aliases are matched.
_ALIAS_ONLY = {"Go", "C", "R", "Spring", "Excel", "Swift", "Oracle", "Spark"}


def _build_patterns() -> Dict[str, "re.Pattern[str]"]:
    patterns: Dict[str, "re.Pattern[str]"] = {}
    for name, (_category, aliases) in SKILLS.items():
        terms = {a.lower() for a in aliases}
        if name not in _ALIAS_ONLY:
            terms.add(name.lower())
        # Longest first so "spring boot" wins over a shorter overlapping term.
        ordered = sorted(terms, key=len, reverse=True)
        patterns[name] = re.compile("|".join(_term_to_regex(t) for t in ordered), re.IGNORECASE)
    return patterns


_PATTERNS = _build_patterns()


def skills_in_text(text: str) -> Dict[str, int]:
    """Return {skill: mention_count} for every taxonomy skill found in ``text``."""
    found: Dict[str, int] = {}
    if not text:
        return found
    for name, pattern in _PATTERNS.items():
        count = len(pattern.findall(text))
        if count:
            found[name] = count
    return found


def skill_category(skill: str) -> str:
    return SKILLS.get(skill, ("other", ()))[0]


# --------------------------------------------------------------------------- #
# Resume sections
# --------------------------------------------------------------------------- #
_SECTION_HEADERS: Dict[str, Tuple[str, ...]] = {
    "summary": ("summary", "professional summary", "profile", "objective",
                "career objective", "about me", "about"),
    "experience": ("experience", "work experience", "professional experience", "employment",
                   "employment history", "work history", "internships", "internship",
                   "internship experience", "career history", "relevant experience"),
    "education": ("education", "academic background", "academics", "educational qualifications",
                  "academic qualifications", "qualifications"),
    "skills": ("skills", "technical skills", "core competencies", "key skills",
               "skills and tools", "technologies", "tech stack", "technical proficiencies"),
    "projects": ("projects", "personal projects", "academic projects", "key projects",
                 "selected projects", "project work"),
    "certifications": ("certifications", "certificates", "licenses and certifications",
                       "courses"),
    "achievements": ("achievements", "awards", "honors", "honours", "accomplishments",
                     "awards and achievements"),
}
_HEADER_LOOKUP = {alias: section for section, aliases in _SECTION_HEADERS.items()
                  for alias in aliases}


def _normalize_header(line: str) -> str:
    cleaned = re.sub(r"[^a-z& ]", " ", line.lower()).replace("&", " and ")
    return re.sub(r"\s+", " ", cleaned).strip()


def split_sections(text: str) -> Dict[str, str]:
    """Split resume text into known sections by header lines. Unknown text is ignored."""
    sections: Dict[str, List[str]] = {}
    current: Optional[str] = None
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped and len(stripped) <= 40:
            section = _HEADER_LOOKUP.get(_normalize_header(stripped))
            if section:
                current = section
                sections.setdefault(section, [])
                continue
        if current is not None:
            sections[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)")
_LINK_RE = re.compile(r"(linkedin\.com/in/|github\.com/)[\w-]+", re.IGNORECASE)


def has_contact_info(text: str) -> bool:
    return bool(_EMAIL_RE.search(text) or _PHONE_RE.search(text) or _LINK_RE.search(text))


# --------------------------------------------------------------------------- #
# Experience estimate (heuristic)
# --------------------------------------------------------------------------- #
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_MONTH_PATTERN = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"
_RANGE_RE = re.compile(
    rf"""(?:(?P<sm>{_MONTH_PATTERN}|\d{{1,2}}[/.])\s*,?\s*)?(?P<sy>(?:19|20)\d{{2}})
         \s*(?:-|–|—|to|until|till)\s*
         (?:(?:(?P<em>{_MONTH_PATTERN}|\d{{1,2}}[/.])\s*,?\s*)?(?P<ey>(?:19|20)\d{{2}})
            |(?P<pres>present|current|now|ongoing|till\s+date|to\s+date))""",
    re.IGNORECASE | re.VERBOSE,
)


def _month_number(token: Optional[str]) -> Optional[int]:
    if not token:
        return None
    token = token.strip().lower().rstrip("./")
    if token.isdigit():
        value = int(token)
        return value if 1 <= value <= 12 else None
    return _MONTHS.get(token[:3])


def estimate_experience_years(text: str, today: Optional[date] = None) -> Tuple[Optional[float], str]:
    """Estimate years of experience from date ranges. Returns (years or None, scope note).

    Only the Experience section is used when one can be found; otherwise the whole
    document minus Education is used and the note says so. Overlapping ranges are merged.
    Missing months are treated as mid-year so the estimate is not inflated.
    """
    today = today or date.today()
    sections = split_sections(text)
    if sections.get("experience"):
        scope_text, scope = sections["experience"], "experience section"
    else:
        scope_text = text or ""
        if sections.get("education"):
            scope_text = scope_text.replace(sections["education"], " ")
        scope = "whole document (no Experience heading found)"

    intervals: List[Tuple[int, int]] = []
    for match in _RANGE_RE.finditer(scope_text):
        start_year = int(match.group("sy"))
        start_month = _month_number(match.group("sm")) or 6
        if match.group("pres"):
            end_year, end_month = today.year, today.month
        else:
            end_year = int(match.group("ey"))
            end_month = _month_number(match.group("em")) or 6
        start, end = start_year * 12 + start_month, end_year * 12 + end_month
        if end > start and end_year <= today.year + 1 and start_year >= 1970:
            intervals.append((start, min(end, today.year * 12 + today.month)))

    if not intervals:
        return None, scope
    intervals.sort()
    merged = [list(intervals[0])]
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    months = sum(end - start for start, end in merged)
    return round(months / 12, 1), scope


# --------------------------------------------------------------------------- #
# Job description parsing
# --------------------------------------------------------------------------- #
# Cues that switch the section for every following line (only checked on heading-like lines).
_REQUIRED_HEADER_CUES = ("requirement", "required", "must have", "must-have", "qualification",
                         "what you'll need", "what you will need", "what we're looking for",
                         "minimum", "you have", "you bring", "essential", "responsibilit",
                         "about the role", "what you'll do", "what you will do")
_PREFERRED_HEADER_CUES = ("preferred", "nice to have", "nice-to-have", "bonus", "good to have",
                          "desired", "added advantage")
# Cues that mark only the line they appear on.
_INLINE_PREFERRED_CUES = _PREFERRED_HEADER_CUES + ("is a plus", "are a plus", "a plus", "ideally")
_BULLET_START = re.compile(r"^\s*[-*•‣▪●◦⁃∙➢→–—]")
_YEARS_RE = re.compile(r"(\d{1,2})\s*\+?\s*(?:-|–|to)?\s*(?:\d{1,2})?\s*\+?\s*(?:years?|yrs?)\b",
                       re.IGNORECASE)
_EXPERIENCE_WORD_RE = re.compile(r"\bexperience\b|\bexp\b", re.IGNORECASE)


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 60 or _BULLET_START.match(stripped):
        return False
    return stripped.endswith(":") or len(stripped.split()) <= 4


def _line_mode(line: str, current: str) -> str:
    """Section the following lines belong to. Only heading-like lines can change it."""
    if not _is_heading(line):
        return current
    lowered = line.lower()
    if any(cue in lowered for cue in _PREFERRED_HEADER_CUES):
        return "preferred"
    if any(cue in lowered for cue in _REQUIRED_HEADER_CUES):
        return "required"
    return current


def parse_job_description(text: str) -> Dict[str, object]:
    """Extract required/preferred skills and years-of-experience mentions.

    Skills under a "preferred / nice to have / bonus" heading (or on a line saying so)
    are *preferred*. Everything else is treated as *required* -- including postings that
    have no headings at all. That rule is shown to the user in the result notes.
    """
    required: Dict[str, int] = {}
    preferred: Dict[str, int] = {}
    mode = "required"
    years: List[int] = []
    for line in (text or "").splitlines():
        if not line.strip():
            continue
        mode = _line_mode(line, mode)
        inline_preferred = any(cue in line.lower() for cue in _INLINE_PREFERRED_CUES)
        line_mode = "preferred" if inline_preferred else mode
        for skill, count in skills_in_text(line).items():
            bucket = preferred if line_mode == "preferred" else required
            bucket[skill] = bucket.get(skill, 0) + count
        if _EXPERIENCE_WORD_RE.search(line):
            years.extend(int(m.group(1)) for m in _YEARS_RE.finditer(line)
                         if 0 < int(m.group(1)) <= 20)
    for skill in list(preferred):
        if skill in required:  # required wins
            del preferred[skill]
    return {"required": required, "preferred": preferred, "years_mentions": sorted(set(years))}


# --------------------------------------------------------------------------- #
# Unscored keyword hints
# --------------------------------------------------------------------------- #
_STOPWORDS = set("""
about above ability across after also and any are around based been being between both
build building but can candidate candidates company could create day dedicated deliver
different do does each strong will with within without work working works would year years
experience experienced knowledge skills skill team teams role roles looking join position
positions responsibilities responsibility requirements required preferred including include
includes etc must have has had you your our their they them this that these those than then
there from for into over under more most other such like well good great excellent plus
bonus ideal ideally nice using use used make makes help helps need needs new part full time
opportunity opportunities environment business high level large small able own who what
when where how why which while per via should may might shall one two three four five
""".split())


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z\-]{3,}", (text or "").lower())


def missing_keywords(jd_text: str, resume_text: str, known_skill_terms: set, limit: int = 8) -> List[str]:
    """Words repeated (2+ times) in the posting but absent from the resume. Unscored hints."""
    counts: Dict[str, int] = {}
    for token in _tokens(jd_text):
        if token in _STOPWORDS or token in known_skill_terms:
            continue
        counts[token] = counts.get(token, 0) + 1
    resume_tokens = set(_tokens(resume_text))
    ranked = sorted(((c, t) for t, c in counts.items() if c >= 2 and t not in resume_tokens),
                    key=lambda item: (-item[0], item[1]))
    return [token for _count, token in ranked[:limit]]


# --------------------------------------------------------------------------- #
# Matching
# --------------------------------------------------------------------------- #
WEIGHTS = {"required_skills": 50, "preferred_skills": 15, "experience_fit": 20, "completeness": 15}
_MIN_RESUME_WORDS = 15


def _evidence_line(resume_text: str, skill: str) -> str:
    pattern = _PATTERNS[skill]
    for line in resume_text.splitlines():
        if pattern.search(line):
            snippet = re.sub(r"\s+", " ", line).strip()
            return snippet if len(snippet) <= 140 else snippet[:137].rstrip() + "..."
    return ""


def _related_in_resume(skill: str, resume_skills: Dict[str, int]) -> List[str]:
    related: List[str] = []
    for group in RELATED_GROUPS:
        if skill in group:
            related.extend(s for s in group if s != skill and s in resume_skills and s not in related)
    return related[:3]


def _completeness(resume_text: str, sections: Dict[str, str]) -> Tuple[int, List[str], List[str]]:
    checks = [
        ("Contact details (email, phone, LinkedIn or GitHub)", 25, has_contact_info(resume_text)),
        ("Skills section", 25, "skills" in sections),
        ("Education section", 20, "education" in sections),
        ("Experience section", 20, "experience" in sections),
        ("Projects section", 10, "projects" in sections),
    ]
    score = sum(weight for _label, weight, ok in checks if ok)
    present = [label for label, _w, ok in checks if ok]
    absent = [label for label, _w, ok in checks if not ok]
    return score, present, absent


def _pct(value: float) -> int:
    """Round half up (Python's round() is half-to-even, which surprises in score displays)."""
    return int(value + 0.5)


def _band(score: int) -> str:
    if score >= 75:
        return "Strong overlap"
    if score >= 55:
        return "Moderate overlap"
    if score >= 35:
        return "Partial overlap"
    return "Low overlap"


def analyze_match(resume_text: Optional[str], job_description: Optional[str],
                  today: Optional[date] = None) -> Dict[str, object]:
    """Compare a resume with a job description and explain the result.

    Always returns a dict with a ``status``:
      ``ok``                          -- full result
      ``empty_resume`` / ``resume_too_short`` / ``empty_job_description``
      ``no_skills_in_job_description`` -- posting has no skills this tool recognises
    Non-ok results carry a user-facing ``message`` and no score.
    """
    resume_text = (resume_text or "").strip()
    job_description = (job_description or "").strip()
    base: Dict[str, object] = {"disclaimer": ESTIMATE_DISCLAIMER}

    if not resume_text:
        return {**base, "status": "empty_resume", "message": "Add your resume (upload a file or paste the text)."}
    if len(resume_text.split()) < _MIN_RESUME_WORDS:
        return {**base, "status": "resume_too_short",
                "message": "The resume text is too short to analyse. Paste or upload the full resume."}
    if not job_description:
        return {**base, "status": "empty_job_description",
                "message": "Paste the job description you want to compare against."}

    jd = parse_job_description(job_description)
    required: Dict[str, int] = jd["required"]  # type: ignore[assignment]
    preferred: Dict[str, int] = jd["preferred"]  # type: ignore[assignment]
    years_mentions: List[int] = jd["years_mentions"]  # type: ignore[assignment]
    if not required and not preferred:
        return {**base, "status": "no_skills_in_job_description",
                "message": ("No recognisable skills were found in the job description. Paste the full "
                            "posting, including the requirements section.")}

    resume_skills = skills_in_text(resume_text)
    sections = split_sections(resume_text)
    evidence_text = "\n".join(sections.get(name, "") for name in ("experience", "projects"))
    sections_found = bool(evidence_text.strip())

    def describe(skills: Dict[str, int]) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
        matched, missing = [], []
        for skill in sorted(skills, key=lambda s: (-skills[s], s)):
            if skill in resume_skills:
                demonstrated = bool(_PATTERNS[skill].search(evidence_text)) if sections_found else None
                matched.append({"skill": skill, "category": skill_category(skill),
                                "evidence": _evidence_line(resume_text, skill),
                                "demonstrated_in_experience": demonstrated,
                                "mentions_in_posting": skills[skill]})
            else:
                missing.append({"skill": skill, "category": skill_category(skill),
                                "related_in_resume": _related_in_resume(skill, resume_skills),
                                "mentions_in_posting": skills[skill]})
        return matched, missing

    matched_req, missing_req = describe(required)
    matched_pref, missing_pref = describe(preferred)

    resume_years, scope = estimate_experience_years(resume_text, today)
    required_years = min(years_mentions) if years_mentions else None
    completeness_score, present, absent = _completeness(resume_text, sections)

    components: List[Dict[str, object]] = []

    def add(key: str, label: str, score: Optional[float], detail: str) -> None:
        components.append({"key": key, "label": label, "base_weight": WEIGHTS[key],
                           "score": None if score is None else _pct(score),
                           "applicable": score is not None, "detail": detail})

    add("required_skills", "Required skills coverage",
        100 * len(matched_req) / len(required) if required else None,
        f"{len(matched_req)} of {len(required)} skills the posting treats as required appear in your resume."
        if required else "No required skills detected in the posting.")
    add("preferred_skills", "Preferred skills coverage",
        100 * len(matched_pref) / len(preferred) if preferred else None,
        f"{len(matched_pref)} of {len(preferred)} nice-to-have skills appear in your resume."
        if preferred else "The posting lists no separate nice-to-have skills.")
    if required_years is None:
        add("experience_fit", "Experience level fit", None, "The posting does not state years of experience.")
    elif resume_years is None:
        add("experience_fit", "Experience level fit", None,
            f"The posting mentions {required_years}+ years, but years could not be estimated from your dates.")
    else:
        add("experience_fit", "Experience level fit", 100 * min(resume_years / required_years, 1.0),
            f"Posting mentions {required_years}+ years; your dated roles add up to about {resume_years} "
            f"years (from the {scope}).")
    add("completeness", "Resume completeness", float(completeness_score),
        "Checks for standard sections. Present: " + (", ".join(present) or "none")
        + (". Missing: " + ", ".join(absent) if absent else "."))

    applicable_weight = sum(c["base_weight"] for c in components if c["applicable"])  # type: ignore[misc]
    for c in components:
        c["effective_weight"] = _pct(100 * c["base_weight"] / applicable_weight) if c["applicable"] else 0  # type: ignore[operator]
    overall = _pct(sum(c["score"] * c["base_weight"] for c in components if c["applicable"])  # type: ignore[operator]
                   / applicable_weight)

    known_terms = {t.lower() for name, (_c, aliases) in SKILLS.items() for t in (name, *aliases)}
    result: Dict[str, object] = {
        **base,
        "status": "ok",
        "overall_score": overall,
        "band": _band(overall),
        "components": components,
        "required": {"matched": matched_req, "missing": missing_req},
        "preferred": {"matched": matched_pref, "missing": missing_pref},
        "extra_skills": sorted(s for s in resume_skills if s not in required and s not in preferred),
        "experience": {"resume_years_estimate": resume_years, "estimate_scope": scope,
                       "posting_years_mentions": years_mentions},
        "missing_keywords": missing_keywords(job_description, resume_text, known_terms),
        "sections_found": sorted(sections),
        "completeness": {"present": present, "missing": absent},
        "notes": [
            "Skills under a 'preferred' / 'nice to have' / 'bonus' heading count as preferred; "
            "every other skill in the posting counts as required.",
            "Only skills in this tool's built-in list are recognised; soft skills and niche tools are not scored.",
        ],
    }
    result["recommendations"] = build_recommendations(result)
    return result


def build_recommendations(result: Dict[str, object]) -> List[str]:
    """Turn the analysis into truthful next steps. Never suggests claiming a skill you lack."""
    tips: List[str] = []
    required = result["required"]  # type: ignore[index]
    for item in required["missing"][:5]:  # type: ignore[index]
        skill = item["skill"]
        related = item["related_in_resume"]
        if related:
            tips.append(
                f"The posting asks for {skill}. Your resume shows related experience ({', '.join(related)}). "
                f"If you have also genuinely used {skill}, add it with a bullet showing how; if not, point out "
                f"the transferable overlap instead of listing {skill}.")
        else:
            tips.append(
                f"The posting asks for {skill} and it is not on your resume. Add it only if you have real "
                f"experience with it; otherwise treat it as a learning gap to address in your cover letter or "
                f"a small project.")

    listed_only = [m["skill"] for group in (required["matched"], result["preferred"]["matched"])  # type: ignore[index]
                   for m in group if m["demonstrated_in_experience"] is False]
    if listed_only:
        tips.append(
            "These matched skills appear in your resume but not in any experience or project bullet: "
            f"{', '.join(listed_only[:6])}. If true, back each one with a bullet showing what you did with it.")

    for component in result["components"]:  # type: ignore[index]
        if component["key"] == "experience_fit" and component["applicable"] and component["score"] < 100:
            tips.append("Your dated experience looks shorter than the posting's stated years. Lead with your most "
                        "relevant projects and internships, and make sure start and end dates are clearly written.")
    missing_parts = result["completeness"]["missing"]  # type: ignore[index]
    if missing_parts:
        tips.append("Add the standard resume parts that are missing: " + ", ".join(missing_parts) + ".")

    if result["missing_keywords"]:
        tips.append("Words the posting repeats that your resume never uses: "
                    f"{', '.join(result['missing_keywords'][:6])}. Use them only where they describe work you did.")  # type: ignore[index]
    return tips
