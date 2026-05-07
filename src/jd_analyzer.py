"""JD parsing + keyword extraction + gap analysis against master profile."""
from __future__ import annotations

import json
from typing import Any

from .llm import call_json, load_profile

SYSTEM = """You analyze job descriptions for a resume-tailoring system.

Return STRICT JSON with this schema:
{
  "company": str | null,
  "role_title": str,
  "role_category": "business_analyst" | "data_analyst" | "data_scientist",
  "seniority": "intern" | "junior" | "mid" | "senior" | "lead" | "unknown",
  "must_have_keywords": [str],   // technical terms, tools, methods - ATS critical
  "nice_to_have_keywords": [str],
  "domain": [str],                // industry/business context
  "responsibilities_summary": str, // 1-2 sentences
  "tone_signals": [str],          // e.g. "fast-paced startup", "regulated finance", "research-oriented"
  "gaps_vs_profile": [str],       // keywords from JD not present in candidate profile
  "strengths_vs_profile": [str]   // candidate strengths matching JD
}

Rules:
- role_category must be one of the three exact strings.
- must_have_keywords: prefer exact phrasing from JD. Cap at 25.
- Do NOT invent skills the candidate doesn't have when filling strengths.
- gaps_vs_profile: be honest, list real gaps. Cap at 15.
- Output ONLY the JSON object. No prose, no fences.
"""


def analyze_jd(jd_text: str, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = profile or load_profile()
    profile_brief = _profile_brief(profile)
    user = f"""<candidate_profile_brief>
{profile_brief}
</candidate_profile_brief>

<job_description>
{jd_text}
</job_description>

Analyze and return the JSON object."""
    return call_json(SYSTEM, user, max_tokens=2048)


def _profile_brief(profile: dict[str, Any]) -> str:
    skills = []
    for v in profile["skills"].values():
        skills.extend(v)
    exp = [
        f"{e['title']} @ {e['company']} ({e['start']}-{e['end']})"
        for e in profile["experience"]
    ]
    projs = [f"{p['title']} [{', '.join(p['tech'])}]" for p in profile["projects"]]
    return json.dumps(
        {
            "skills": skills,
            "experience": exp,
            "projects": projs,
            "education": [
                f"{e['degree']} @ {e['school']}" for e in profile["education"]
            ],
        },
        indent=2,
    )
