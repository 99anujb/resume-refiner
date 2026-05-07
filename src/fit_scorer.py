"""Fit scoring: rate JD vs profile (0-5) with per-dimension breakdown."""
from __future__ import annotations

import json
from typing import Any

from .llm import call_json, load_profile

SYSTEM = """You score how well a candidate fits a job.

Output STRICT JSON:
{
  "overall_score": float,                          // 0.0 - 5.0, one decimal
  "verdict": "apply" | "stretch" | "skip",          // apply >=4, stretch 2.5-3.9, skip <2.5
  "dimensions": {
    "keyword_coverage":   {"score": float, "weight": 0.30, "note": str},
    "experience_relevance":{"score": float, "weight": 0.25, "note": str},
    "tech_stack_overlap": {"score": float, "weight": 0.20, "note": str},
    "seniority_fit":      {"score": float, "weight": 0.10, "note": str},
    "domain_fit":         {"score": float, "weight": 0.10, "note": str},
    "education_fit":      {"score": float, "weight": 0.05, "note": str}
  },
  "strengths": [str],                               // top 3-5 reasons it's a fit
  "weaknesses": [str],                              // top 3-5 honest gaps
  "fix_suggestions": [                              // concrete actions to close gaps
    {"gap": str, "action": str, "effort": "low"|"medium"|"high"}
  ],
  "red_flags": [str],                               // things that may cause auto-rejection
  "recommendation": str                             // 1-2 sentence summary verdict
}

Rules for each dimension (score 0-5 each):
- keyword_coverage: how many JD must-have keywords the candidate can credibly claim. 5 = nearly all; 0 = almost none.
- experience_relevance: years + role-type alignment. Mid-level analyst applying to mid-level analyst = 5. Junior applying to senior = 2.
- tech_stack_overlap: candidate's tools ∩ JD tools / JD tools. Score = ratio * 5.
- seniority_fit: 5 = exact match. Underqualified by 1 level = 3. By 2 levels = 1. Overqualified by 1 = 4.
- domain_fit: same industry = 5. Adjacent = 3-4. Unrelated = 1-2.
- education_fit: meets stated min = 5. Above = 5 (cap). Below = 2-3 if substituted by experience.

overall_score = sum(score_i * weight_i). Round to 1 decimal.
Verdict thresholds: >=4.0 apply, 2.5-3.9 stretch, <2.5 skip.
Be HONEST. Do not inflate. Output ONLY the JSON object."""


def score_fit(jd_analysis: dict[str, Any], profile: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = profile or load_profile()
    skills_flat: list[str] = []
    for v in profile["skills"].values():
        skills_flat.extend(v)
    profile_brief = {
        "experience_years": profile.get("constraints", {}).get("experience_years", 4),
        "experience": [
            {"company": e["company"], "title": e["title"], "start": e["start"], "end": e["end"]}
            for e in profile["experience"]
        ],
        "skills": skills_flat,
        "projects": [{"title": p["title"], "tech": p["tech"], "domain": p.get("domain", [])} for p in profile["projects"]],
        "education": [
            {"degree": e["degree"], "school": e["school"], "gpa": e.get("gpa")}
            for e in profile["education"]
        ],
        "achievements": profile["achievements"],
    }
    user = f"""<candidate_profile>
{json.dumps(profile_brief, indent=2)}
</candidate_profile>

<jd_analysis>
{json.dumps(jd_analysis, indent=2)}
</jd_analysis>

Score the fit. Return JSON."""
    return call_json(SYSTEM, user, max_tokens=2500)
