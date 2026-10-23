"""Rule-based resume bullet feedback.

Design rule: this module never invents anything. It does not add metrics, skills, employers
or outcomes. A rewrite is offered only when it is a mechanical, meaning-preserving change to
the *opening words* (for example "Responsible for managing X" -> "Managed X"). Everything
else is feedback plus a question the candidate answers truthfully.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Dict, List, Optional

from .job_match import split_sections

_BULLET_MARKER = re.compile(
    r"^\s*(?:[-*•‣▪●◦⁃∙➢→–—]|\d{1,2}[.)])\s+")
_DATE_RANGE = re.compile(
    r"(?:19|20)\d{2}\s*(?:-|–|—|to)\s*(?:(?:[A-Za-z]{3,9}\.?\s+)?(?:19|20)\d{2}|present|current|now)",
    re.IGNORECASE)

# Opening phrases that describe a duty rather than an action.
_WEAK_OPENERS = [
    re.compile(r"^(?:was|were)\s+responsible\s+for\b", re.IGNORECASE),
    re.compile(r"^responsible\s+for\b", re.IGNORECASE),
    re.compile(r"^in\s+charge\s+of\b", re.IGNORECASE),
    re.compile(r"^worked\s+(?:on|with|in)\b", re.IGNORECASE),
    re.compile(r"^helped\b", re.IGNORECASE),
    re.compile(r"^assisted\b", re.IGNORECASE),
    re.compile(r"^involved\s+in\b", re.IGNORECASE),
    re.compile(r"^participated\s+in\b", re.IGNORECASE),
    re.compile(r"^tasked\s+with\b", re.IGNORECASE),
    re.compile(r"^duties\s+(?:included|include)\b", re.IGNORECASE),
    re.compile(r"^(?:was|were)\s+part\s+of\b", re.IGNORECASE),
]
# Only these two openers get an automatic rewrite, because the verb that follows is the
# candidate's own ("responsible for managing X" -> "Managed X"): no meaning is added.
_REWRITABLE = [re.compile(r"^(?:(?:was|were)\s+)?responsible\s+for\s+(\w+)\s+", re.IGNORECASE),
               re.compile(r"^in\s+charge\s+of\s+(\w+)\s+", re.IGNORECASE)]

_GERUND_TO_PAST = {
    "managing": "Managed", "developing": "Developed", "building": "Built", "designing": "Designed",
    "implementing": "Implemented", "maintaining": "Maintained", "testing": "Tested",
    "debugging": "Debugged", "writing": "Wrote", "creating": "Created", "leading": "Led",
    "coordinating": "Coordinated", "analyzing": "Analyzed", "analysing": "Analysed",
    "deploying": "Deployed", "monitoring": "Monitored", "reviewing": "Reviewed",
    "training": "Trained", "mentoring": "Mentored", "organizing": "Organized",
    "organising": "Organised", "planning": "Planned", "documenting": "Documented",
    "configuring": "Configured", "integrating": "Integrated", "optimizing": "Optimized",
    "optimising": "Optimised", "automating": "Automated", "supporting": "Supported",
    "handling": "Handled", "preparing": "Prepared", "conducting": "Conducted",
    "delivering": "Delivered", "running": "Ran", "processing": "Processed", "updating": "Updated",
    "cleaning": "Cleaned", "collecting": "Collected", "researching": "Researched",
    "presenting": "Presented", "scheduling": "Scheduled", "tracking": "Tracked",
    "resolving": "Resolved", "troubleshooting": "Troubleshot", "migrating": "Migrated",
    "refactoring": "Refactored", "administering": "Administered", "overseeing": "Oversaw",
    "supervising": "Supervised", "securing": "Secured", "launching": "Launched",
    "evaluating": "Evaluated", "improving": "Improved", "reporting": "Reported",
}

# Verbs that describe *what you did* without claiming an outcome, so suggesting them cannot
# overstate anything. The candidate must still pick the one that is accurate.
NEUTRAL_VERB_OPTIONS = ["Built", "Developed", "Designed", "Implemented", "Tested", "Debugged",
                        "Maintained", "Documented", "Configured", "Analyzed", "Contributed to"]

_PAST_VERBS = set(w.lower() for w in _GERUND_TO_PAST.values()) | {
    "built", "led", "ran", "wrote", "drove", "took", "made", "won", "taught", "oversaw", "sold",
    "set", "spoke", "chose", "found", "gave", "grew", "kept", "met", "put", "read", "saw", "shipped",
    "launched", "founded", "authored", "spearheaded", "owned", "established", "introduced",
    "engineered", "architected", "streamlined", "published", "collaborated", "negotiated",
    "achieved", "earned", "initiated", "executed", "enhanced", "generated", "increased", "reduced",
    "drafted", "designed", "programmed", "modeled", "modelled", "tuned", "scaled", "visualized",
}
_BASE_VERBS = {
    "build", "develop", "design", "implement", "manage", "lead", "create", "write", "test", "debug",
    "maintain", "deploy", "analyze", "analyse", "automate", "optimize", "optimise", "integrate",
    "configure", "document", "mentor", "coordinate", "deliver", "monitor", "review", "support",
    "architect", "engineer", "migrate", "refactor", "own", "drive", "ship", "launch", "train",
}

_FIRST_PERSON = re.compile(r"\b(?:i|my|me|myself)\b", re.IGNORECASE)
_PASSIVE = re.compile(r"\b(?:was|were)\s+(?:\w+ly\s+)?\w+ed\b", re.IGNORECASE)
_VAGUE = re.compile(r"\b(?:various|numerous|several|many|multiple|etc\.?|a\s+lot\s+of|some)\b", re.IGNORECASE)
_HAS_NUMBER = re.compile(r"\d")
MAX_WORDS = 34
MIN_WORDS = 6


def _issue(code: str, severity: str, message: str, why: str) -> Dict[str, str]:
    return {"code": code, "severity": severity, "message": message, "why": why}


def _strip_marker(line: str) -> str:
    return _BULLET_MARKER.sub("", line, count=1).strip()


def _words(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9+#.'/-]+", text)


def _matching_weak_opener(text: str) -> Optional[str]:
    for pattern in _WEAK_OPENERS:
        match = pattern.match(text)
        if match:
            return match.group(0)
    return None


def _mechanical_rewrite(text: str) -> Optional[str]:
    """Return a rewrite only when it changes nothing but the opening phrase."""
    for pattern in _REWRITABLE:
        match = pattern.match(text)
        if match:
            past = _GERUND_TO_PAST.get(match.group(1).lower())
            if past:
                return f"{past} {text[match.end():].lstrip()}".strip()
    match = re.match(r"^I\s+(\w+)\s+", text)
    if match and (match.group(1).lower() in _PAST_VERBS or match.group(1).lower().endswith("ed")):
        rest = text[match.start(1):]
        return rest[0].upper() + rest[1:]
    return None


def analyze_bullet(text: Optional[str]) -> Dict[str, object]:
    """Feedback for a single bullet. Never adds facts to the candidate's text."""
    original = _strip_marker(text or "")
    if not re.search(r"[A-Za-z0-9]", original):  # empty, or just punctuation such as a lone "-"
        return {"original": "", "issues": [], "suggested_rewrite": None, "verb_options": [], "needs_work": False}

    issues: List[Dict[str, str]] = []
    words = _words(original)
    first = words[0].lower().strip(".,:;") if words else ""
    lead_word = words[0] if words else ""
    if first == "i" and len(words) > 1:  # judge the verb after the pronoun; first_person is flagged separately
        lead_word = words[1]
        first = lead_word.lower().strip(".,:;")
    weak = _matching_weak_opener(original)
    verb_options: List[str] = []

    if weak:
        issues.append(_issue(
            "weak_opener", "medium", f'Starts with "{weak}".',
            "This phrase describes a duty, not something you did. Recruiters skim the first words, "
            "so open with the action itself."))
        verb_options = list(NEUTRAL_VERB_OPTIONS)
    elif first and not (first in _PAST_VERBS or first in _BASE_VERBS or first.endswith("ed")
                        or first.endswith("ing")):
        issues.append(_issue(
            "no_action_verb", "medium", f'Starts with "{lead_word}", which does not read as an action verb.',
            "Leading with a verb (Built, Tested, Led...) shows your contribution in the first two words."))
    if first.endswith("ing") and not weak and first not in _PAST_VERBS:
        issues.append(_issue(
            "tense", "low", f'Starts with "{lead_word}" (an -ing form).',
            "Use past tense for finished roles and present tense only for your current role."))
    if _FIRST_PERSON.search(original):
        issues.append(_issue(
            "first_person", "low", "Uses first-person words (I / my / me).",
            "Resumes conventionally leave these out; the bullet is already about you."))
    if _PASSIVE.search(original):
        issues.append(_issue(
            "passive_voice", "low", "Uses passive voice.",
            "Passive phrasing hides your role. Say what you did, not what was done."))
    vague = sorted({m.group(0).lower() for m in _VAGUE.finditer(original)})
    if vague:
        issues.append(_issue(
            "vague_words", "low", f"Vague wording: {', '.join(vague)}.",
            "Replace vague words with specifics you can back up, such as which tools or how many."))
    if len(words) > MAX_WORDS:
        issues.append(_issue(
            "too_long", "medium", f"{len(words)} words long.",
            "Long bullets are hard to skim. Consider splitting it into two focused bullets."))
    if len(words) < MIN_WORDS:
        issues.append(_issue(
            "too_short", "low", f"Only {len(words)} words.",
            "Very short bullets rarely show what you did or why it mattered. Add the tool or the result if you can."))
    if not _HAS_NUMBER.search(original):
        issues.append(_issue(
            "no_numbers", "low", "No numbers or measurable detail.",
            "Real figures (users, records, time, team size, % change) make impact easier to judge. "
            "Add one only if you can back it up. Never estimate."))

    rewrite = _mechanical_rewrite(original)
    return {
        "original": original,
        "issues": issues,
        "suggested_rewrite": rewrite if rewrite and rewrite != original else None,
        "verb_options": verb_options,
        "needs_work": any(i["severity"] in ("high", "medium") for i in issues),
    }


def extract_bullets(resume_text: Optional[str], limit: int = 30) -> List[str]:
    """Pull bullet lines from Experience/Projects (or the whole text if those can't be found)."""
    text = resume_text or ""
    sections = split_sections(text)
    source = "\n".join(sections[name] for name in ("experience", "projects") if name in sections) or text

    bullets: List[str] = []
    for line in source.splitlines():
        if not line.strip():
            continue
        if _BULLET_MARKER.match(line):
            bullets.append(_strip_marker(line))
        elif bullets and line.strip()[0].islower():
            bullets[-1] = f"{bullets[-1]} {line.strip()}"  # wrapped continuation line

    if not bullets:  # no bullet characters at all: fall back to sentence-like lines
        for line in source.splitlines():
            stripped = line.strip()
            if len(stripped.split()) >= 8 and not _DATE_RANGE.search(stripped):
                bullets.append(stripped)

    seen, unique = set(), []
    for bullet in bullets:
        key = bullet.lower()
        if bullet and key not in seen:
            seen.add(key)
            unique.append(bullet)
    return unique[:limit]


def analyze_bullets(resume_text: Optional[str], limit: int = 25) -> Dict[str, object]:
    """Analyse every bullet found in a resume."""
    bullets = extract_bullets(resume_text, limit)
    if not bullets:
        return {"status": "no_bullets", "bullets": [], "summary": {"total": 0, "needs_work": 0, "with_numbers": 0},
                "repeated_openers": [],
                "message": "No bullet points were found. Use one line per achievement, starting with a dash or bullet."}
    results = [analyze_bullet(b) for b in bullets]
    openers = Counter(b.split()[0].lower().strip(".,:;") for b in bullets if b.split())
    repeated = [{"verb": verb, "count": count} for verb, count in openers.most_common() if count >= 3]
    return {
        "status": "ok",
        "bullets": results,
        "summary": {"total": len(results),
                    "needs_work": sum(1 for r in results if r["needs_work"]),
                    "with_numbers": sum(1 for b in bullets if _HAS_NUMBER.search(b))},
        "repeated_openers": repeated,
        "message": "",
    }
