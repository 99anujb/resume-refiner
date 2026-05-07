"""Tailor master profile to JD using Claude. Produces final structured resume JSON."""
from __future__ import annotations

import json
from typing import Any

from .llm import call_json, load_profile

SYSTEM = """You tailor an existing professional profile to a specific job description.

You will receive:
1. A master profile JSON (canonical: skills, multi-variant bullets per job, multi-framing projects).
2. A JD analysis JSON with role_category, must_have_keywords, nice_to_have_keywords.

Produce a STRICT JSON tailored resume optimized for ATS keyword density and 1-page fit:

{
  "contact": { ... copy from master ... },
  "target_title": str,
  "summary": str,
  "skills": {"<category_label>": [str, ...], ...},
  "experience": [{"company": str, "location": str, "title": str, "start": str, "end": str, "bullets": [str, ...]}],
  "projects": [{"title": str, "subtitle": str | null, "tech": [str, ...], "github": str, "description": str}],
  "education": [{"school": str, "degree": str, "gpa": str | null, "start": str, "end": str, "coursework": [str, ...]}],
  "achievements": [str, ...],
  "keyword_coverage": {"must_have_hit": [str], "must_have_missed": [str]}
}

MANDATORY (do NOT skip any):
- ALL THREE experience entries from master.experience MUST appear, each with 2-3 bullets minimum (Vedantu MUST have bullets — never empty).
- "projects" array MUST contain 3-4 projects.
- "education" array MUST contain BOTH master.education entries (UMass Dartmouth + Punjab Technical University). UMass MUST include coursework (5-7 items).
- "achievements" MUST contain 1-2 items from master.achievements.
- "skills" MUST have 5 categories.
- "summary" MUST be 3-4 sentences embedding 6-8 must_have_keywords.

Hard rules:
- Use ONLY facts in master_profile. NEVER invent dates, metrics, tools, projects.
- Choose bullets from master.experience[*].bullets[<role_category>] as the base; rephrase to embed must_have_keywords but preserve numeric facts exactly.
- Pick projects ranked by JD relevance. Use master.projects[*].framings[<role_category>] as base.
- Skills: re-order so JD-must-haves appear FIRST in each category.
- target_title should mirror JD title closely.
- 1-page-fit aware: total bullet count across experience ≤ 8. Each bullet ≤ 22 words.
- keyword_coverage: be honest. List unhad must-haves in must_have_missed.
- Output ONLY the JSON object. No prose, no fences. Validate completeness before responding."""


def tailor_resume(jd_analysis: dict[str, Any], profile: dict[str, Any] | None = None,
                  notes: str | None = None) -> dict[str, Any]:
    profile = profile or load_profile()
    user = f"""<master_profile>
{json.dumps(profile, indent=2)}
</master_profile>

<jd_analysis>
{json.dumps(jd_analysis, indent=2)}
</jd_analysis>
"""
    if notes:
        user += f"\n<user_notes>\n{notes}\n</user_notes>\n"
    user += "\nProduce the tailored resume JSON now."
    return call_json(SYSTEM, user, max_tokens=12000)
