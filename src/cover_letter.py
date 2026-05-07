"""Cover letter generator. 1-page, keyword-aware, role-specific tone."""
from __future__ import annotations

import json
from typing import Any

from .llm import call_text

SYSTEM = """You write 1-page cover letters for a candidate applying to a specific role.

Inputs:
- tailored_resume JSON (use this as the source of truth for facts)
- jd_analysis JSON (company, role_title, must_have_keywords, tone_signals)

Produce a single cover letter as plain text with the following structure:

[Date placeholder: leave as "{{DATE}}"]

[Hiring Manager / Hiring Team line. If company name known, address to "<Company> Hiring Team"; else "Hiring Manager"]

Opening paragraph (2-3 sentences):
- State the role you are applying to and where you saw it (use placeholder "{{SOURCE}}" if unspecified).
- Lead with the strongest 1-line pitch tied to the role_category and JD must-haves.

Body paragraph 1 (3-5 sentences):
- Concrete recent work with metrics that maps to the JD's top responsibilities.
- Embed 4-6 must-have keywords naturally.

Body paragraph 2 (3-5 sentences):
- Second proof point: a project or earlier role that fills a different JD signal.
- Embed 3-5 additional must-have keywords.

Closing paragraph (2-3 sentences):
- Tie to the company/team mission if tone_signals or domain hints are available.
- Clear call to action; invite to discuss; thank.

Sign-off:
Sincerely,
Anuj Bansal
99anujbansal@gmail.com | (508) 965-2806

Hard rules:
- Use ONLY facts from the tailored_resume. Do not invent metrics or tools.
- Total length: ~280-360 words. Must fit on one US Letter page with 0.6in margins, 11pt body.
- No bullet points. Cohesive prose.
- Confident but not boastful. No filler ("I am writing to express", "I am excited to apply").
- Do not repeat the resume verbatim - reframe with narrative.
- Output the letter text only. No commentary, no markdown, no headings."""


def generate_cover_letter(tailored: dict[str, Any], jd_analysis: dict[str, Any],
                          notes: str | None = None) -> str:
    user = f"""<tailored_resume>
{json.dumps(tailored, indent=2)}
</tailored_resume>

<jd_analysis>
{json.dumps(jd_analysis, indent=2)}
</jd_analysis>
"""
    if notes:
        user += f"\n<user_notes>\n{notes}\n</user_notes>\n"
    user += "\nWrite the cover letter now."
    return call_text(SYSTEM, user, max_tokens=2000)
