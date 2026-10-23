"""Plain-text (Markdown) export of a job-match analysis. Pure functions, no Streamlit."""
from __future__ import annotations

from typing import Dict, List, Optional

from .job_match import ESTIMATE_DISCLAIMER


def _skill_lines(items: List[Dict[str, object]], missing: bool) -> List[str]:
    if not items:
        return ["- None"]
    lines = []
    for item in items:
        line = f"- {item['skill']}"
        if missing and item.get("related_in_resume"):
            line += f" (related on your resume: {', '.join(item['related_in_resume'])})"  # type: ignore[arg-type]
        if not missing and item.get("demonstrated_in_experience") is False:
            line += " (listed, but not shown in an experience/project bullet)"
        lines.append(line)
    return lines


def build_markdown_report(result: Dict[str, object], bullets: Optional[Dict[str, object]] = None,
                          job_title: str = "") -> str:
    """Build a downloadable report. Contains analysis output only, never the resume text itself."""
    if result.get("status") != "ok":
        return f"# Job match report\n\n{result.get('message', 'No analysis available.')}\n"

    heading = f"# Job match report{f' - {job_title.strip()}' if job_title.strip() else ''}"
    out: List[str] = [heading, "", f"> {ESTIMATE_DISCLAIMER}", "",
                      f"**Overall estimate: {result['overall_score']}/100 ({result['band']})**", "",
                      "## Score breakdown", "", "| Component | Score | Weight | Detail |", "|---|---|---|---|"]
    for c in result["components"]:  # type: ignore[union-attr]
        score = f"{c['score']}/100" if c["applicable"] else "n/a"
        weight = f"{c['effective_weight']}%" if c["applicable"] else "-"
        out.append(f"| {c['label']} | {score} | {weight} | {c['detail']} |")

    for key, title in (("required", "Required skills"), ("preferred", "Preferred skills")):
        group = result[key]  # type: ignore[index]
        out += ["", f"## {title}", "", "**Matched**", *_skill_lines(group["matched"], False),
                "", "**Missing**", *_skill_lines(group["missing"], True)]

    exp = result["experience"]  # type: ignore[index]
    years = exp["resume_years_estimate"]
    out += ["", "## Experience",
            f"- Estimated from dates on your resume: {years if years is not None else 'could not be estimated'}"
            f" years ({exp['estimate_scope']})",
            f"- Years mentioned in the posting: {', '.join(map(str, exp['posting_years_mentions'])) or 'none'}"]

    if result["extra_skills"]:
        out += ["", "## Other skills on your resume", ", ".join(result["extra_skills"])]  # type: ignore[arg-type]
    out += ["", "## Recommendations", *[f"{i}. {t}" for i, t in enumerate(result["recommendations"], 1)]]  # type: ignore[arg-type]

    if bullets and bullets.get("status") == "ok":
        out += ["", "## Bullet feedback", ""]
        for entry in bullets["bullets"]:  # type: ignore[union-attr]
            if not entry["issues"]:
                continue
            out.append(f"- \"{entry['original']}\"")
            if entry["suggested_rewrite"]:
                out.append(f"  - Suggested opening: \"{entry['suggested_rewrite']}\"")
            out += [f"  - {i['message']} {i['why']}" for i in entry["issues"]]
    out += ["", "---", "Skills outside this tool's built-in list and soft skills are not scored."]
    return "\n".join(out) + "\n"
