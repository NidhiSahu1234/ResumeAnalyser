"""Privacy-conscious, session-only snapshots for comparing job-match runs."""
from __future__ import annotations

import csv
import hashlib
import io
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from .job_match import ESTIMATE_DISCLAIMER

MAX_HISTORY_ENTRIES = 20


def build_history_entry(result: Dict[str, object], job_title: str, resume_text: str,
                        created_at: Optional[str] = None) -> Dict[str, object]:
    """Keep comparison metadata only; never retain a resume or job-description body."""
    if result.get("status") != "ok":
        raise ValueError("Only successful analyses can be added to history.")
    normalized_resume = " ".join((resume_text or "").split())
    if not normalized_resume:
        raise ValueError("Resume text is required to add an analysis to history.")

    required = result["required"]
    preferred = result["preferred"]
    components = result["components"]
    fingerprint = hashlib.sha256(normalized_resume.encode("utf-8")).hexdigest()
    return {
        "id": uuid4().hex,
        "created_at": created_at or datetime.now().astimezone().isoformat(timespec="seconds"),
        "job_title": (job_title or "Untitled role").strip()[:120] or "Untitled role",
        "overall_score": int(result["overall_score"]),
        "band": str(result["band"]),
        "resume_fingerprint": fingerprint,
        "required_matched": len(required["matched"]),
        "required_total": len(required["matched"]) + len(required["missing"]),
        "missing_required": [item["skill"] for item in required["missing"]],
        "missing_preferred": [item["skill"] for item in preferred["missing"]],
        "component_scores": {
            component["label"]: component["score"] if component["applicable"] else None
            for component in components
        },
    }


def append_history(history: List[Dict[str, object]], entry: Dict[str, object],
                   limit: int = MAX_HISTORY_ENTRIES) -> List[Dict[str, object]]:
    """Return newest-first history bounded to a small in-memory list."""
    if limit < 1:
        return []
    return [entry, *history][:limit]


def history_as_csv(history: List[Dict[str, object]]) -> str:
    """Export the comparison data without resume text, job text, or its fingerprint."""
    output = io.StringIO(newline="")
    fields = ("created_at", "job_title", "overall_score", "estimate_type", "band", "required_matched",
              "required_total", "missing_required", "missing_preferred")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for entry in history:
        row = {key: entry.get(key, "") for key in fields}
        row["estimate_type"] = ESTIMATE_DISCLAIMER
        row["missing_required"] = "; ".join(entry.get("missing_required", []))
        row["missing_preferred"] = "; ".join(entry.get("missing_preferred", []))
        writer.writerow(row)
    return output.getvalue()
