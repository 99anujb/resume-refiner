"""Check JD for visa/location/clearance dealbreakers vs candidate constraints."""
from __future__ import annotations

import json
from typing import Any

from .llm import call_json

SYSTEM = """You check a job description against a candidate's work-authorization and location constraints.

Return STRICT JSON:
{
  "blockers": [                                 // true dealbreakers, candidate cannot apply
    {"reason": str, "evidence": str}
  ],
  "warnings": [                                  // soft mismatches worth noting
    {"reason": str, "evidence": str}
  ],
  "sponsorship_required_by_jd": "yes" | "no" | "unclear",
  "sponsorship_offered_by_jd": "yes" | "no" | "unclear",
  "clearance_required": "yes" | "no" | "unclear",
  "location": {
    "type": "remote" | "hybrid" | "onsite" | "unclear",
    "country": str | "unclear",
    "city": str | null,
    "matches_candidate": bool
  },
  "verdict": "go" | "caution" | "stop"
}

Rules:
- "go": no blockers, no warnings.
- "caution": no blockers but ≥1 warning.
- "stop": ≥1 blocker (e.g., JD requires US citizen + active clearance, JD onsite outside candidate's eligible countries, JD says "no sponsorship" while candidate needs sponsorship).
- "evidence" must quote a short snippet from the JD.
- If a check is genuinely indeterminate, prefer "unclear" + warning over false certainty.
- Output ONLY the JSON object."""


def visa_location_check(jd_text: str, constraints: dict[str, Any]) -> dict[str, Any]:
    user = f"""<candidate_constraints>
{json.dumps(constraints, indent=2)}
</candidate_constraints>

<job_description>
{jd_text}
</job_description>

Run the check and return JSON."""
    return call_json(SYSTEM, user, max_tokens=1500)
