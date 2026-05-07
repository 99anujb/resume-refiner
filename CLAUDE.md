# CLAUDE.md — Resume Refiner Wizard Instructions

You are running inside this user's resume-refiner project. The user wants to tailor 1-page ATS-aware resumes + cover letters to specific job descriptions. **You (Claude) do all the LLM work inline.** The renderer + tracker are Python tools called via `cli.py`. No external LLM API needed.

---

## Workflow Overview

```
User opens this dir in Claude Code
        ↓
You read CLAUDE.md (this file) — you have the instructions
        ↓
First time? → Run wizard: build the user's master profile
        ↓
Each JD → Score it → Confirm → Tailor → Render PDF → Log
```

---

## First-Time Setup Wizard (run if `data/master_profile.json` doesn't exist)

When user first opens this dir in Claude Code, walk them through these steps in order. **Save profile only if user opts in.**

### Step 1 — API key check
- This project does NOT need an API key when running through Claude Code.
- The Streamlit + Gemini path in `app.py` is optional/legacy and not needed.

### Step 2 — Upload base resumes
Ask: "Drop the path(s) to your base resume(s). PDF or DOCX."
- Read each via `python-docx` (DOCX) or `pypdf` (PDF).
- Extract: contact, summary, skills, experience, projects, education, achievements.
- If user has multiple variants (e.g., DA-focused, DS-focused), merge into one master profile with role-specific framings under each experience and project.

### Step 3 — GitHub username (optional)
Ask: "GitHub username? (skip if private)"
- If provided: hit `https://api.github.com/users/<user>/repos?per_page=100&sort=updated`
- For each repo: fetch README via `https://api.github.com/repos/<user>/<repo>/readme` (Accept: application/vnd.github.raw)
- Filter: skip forks, archived, profile-readme repos, non-data-projects (e.g., portfolio sites unless they want them in)
- Add real public projects to the project bank with proper tech tags + GitHub URL

### Step 4 — Visa & location form
Ask in order:
1. "What is your work authorization status? (US citizen / Permanent resident / OPT / H-1B / TN / other)"
2. "Do you need sponsorship NOW?" — yes/no
3. "Will you need sponsorship in the FUTURE?" — yes/no
4. "Eligible to work in which countries?" — list
5. "Open to relocation?" — yes/no
6. "Preferred locations?" — list (or "Anywhere in the US")
7. "Earliest start date?"
8. "Hard deal-breakers?" — multi-select (e.g., "no clearance roles", "no onsite outside US", "no roles that won't sponsor when needed")

Save to `master_profile.json` → `constraints` block.

### Step 5 — Save preference
Ask: "Save profile to disk for future sessions, or keep in-memory only?"
- **Save**: write `data/master_profile.json` (gitignored, never committed).
- **In-memory**: hold profile in conversation context only; user must re-upload next session.

### Step 6 — Confirm summary
Show user a 6-field summary (name, contact, role targets, top 3 skills, top 3 experiences, top 3 projects). Ask "looks right?" — let them edit before locking.

---

## Per-JD Workflow (every JD the user pastes)

1. **Read the JD carefully.** Identify: company, role title, location, salary if posted, must-have keywords, nice-to-have keywords, visa requirements, domain.

2. **Visa check first.** If JD says "no sponsorship now or in the future" AND user needs future sponsorship → flag as **STOP**. Don't tailor unless user overrides explicitly. Same for citizenship-only or onsite-outside-eligible-countries roles.

3. **PERM-style red flags.** If JD has "post-baccalaureate experience" + BA+6yr/MS+4yr alternative + enumerated "position requires X years in [list]" → tell user this is likely a green-card placeholder ad with low external hire probability.

4. **Score 6 dimensions (0-5 each):**
   | Dim | Weight |
   |---|---|
   | Keyword coverage | 30% |
   | Experience relevance | 25% |
   | Tech stack overlap | 20% |
   | Seniority fit | 10% |
   | Domain fit | 10% |
   | Education fit | 5% |
   
   Verdicts: ≥4.0 APPLY · 2.5-3.9 STRETCH · <2.5 SKIP.

5. **Show user the snapshot + score + recommendation.** Wait for "yes" / "tailor" before proceeding.

6. **Tailor.** Write tailored resume to `data/tailored/<basename>_resume.json` and cover to `data/tailored/<basename>_cover.txt`.
   - **Basename:** `FirstLast_<RoleSlug>_<CompanySlug>_<YYYYMMDD>`
   - Use ONLY facts from `master_profile.json`. Never invent metrics, tools, dates, projects.
   - Standard density: **4 bullets Scaler / 3 each Unacademy / 3 Vedantu** (or equivalent for user's experience entries — typically 3-4 bullets at most recent role, 3 each at older roles).
   - **4 projects**, ranked by JD relevance, with subtitle + tech list + GitHub URL + 1-2 sentence description.
   - Skills: 5-6 categories, JD must-haves first.
   - Education: include all schools, coursework on highest degree.
   - Cover letter: 4 paragraphs, 280-360 words, mirror JD vocabulary, sign with name + email + phone.
   - **`keyword_coverage` block:** be honest. List true `must_have_hit` and `must_have_missed`.

7. **Render via cli.py** (auto-cleans previous tailored files):
   ```bash
   source .venv/bin/activate
   python3 cli.py render data/tailored/<base>_resume.json data/tailored/<base>_cover.txt <base>
   ```

8. **Log to tracker:**
   ```bash
   python3 cli.py log <base> --company X --role Y --role-category data_analyst --seniority mid --fit-score 4.5 --verdict apply --notes "..."
   ```

9. **Append to SESSION_LOG.md** if it exists:
   ```
   [YYYY-MM-DD HH:MM] tailored <Company> <Role> — score X.X verdict, logged id=N
   ```

10. When user says "applied to #N", run:
    ```bash
    sqlite3 data/tracker.db "UPDATE applications SET status='applied', applied_date='YYYY-MM-DD' WHERE id=N;"
    ```

---

## Resume Output Standards (HARD)

- **1 page** — never overflow. Compression ladder picks max font that fits.
- **0.1" margins** all sides.
- **9-9.5pt body** typical (ladder: 11.5pt → 8.25pt; lands 9pt-ish with full content).
- **Hyperlinks active:** phone (`tel:`), email (`mailto:`), LinkedIn, GitHub, Portfolio, project titles → repo URL.
- **Section headers:** ALL CAPS, 0.5pt rule below.
- **Bullet style:** disc, hanging indent, justified.
- **Density:** force page fill — add bullets/projects until ladder lands at 9-10.5pt with no big bottom whitespace.

---

## Cover Letter Standards

- **1 page**, 0.6" margins, 11pt body.
- ~280-360 words, 4 paragraphs:
  1. Opening — role + 1-line pitch, mirror JD vocabulary.
  2. Body 1 — concrete recent work + metrics, embed 4-6 must-haves.
  3. Body 2 — portfolio bridge / second proof point.
  4. Closing — visa status (if relevant) + location + ramp-on-missing-tools + invite.
- Sign-off: `Sincerely,\n<Name>\n<email> | <phone>`

---

## Anti-Patterns (Don't Do)

1. **Don't fabricate.** Never invent tools, dates, metrics, projects, employers. If JD wants something the user lacks → list in `must_have_missed` + cover letter "ramping on" honest framing.
2. **No clichés.** Avoid: "results-driven", "highly analytical", "passionate", "synergies", "intra year", "deeply experienced".
3. **No fluff.** Drop "I am writing to express", "I am excited to apply".
4. **Don't wipe** `data/tracker.db` — persistent log.
5. **Don't run `app.py`** unless user explicitly asks for Streamlit + Gemini path.
6. **Default-clean tailored folder** on every render — only one resume in `data/tailored/` at a time. Override with `--no-clean`.
7. **Confirm before tailoring** — show fit score first, wait for "yes".

---

## CLI Quick Reference

```bash
# show master profile
python3 cli.py show-profile

# render resume + cover from JSON/TXT (default: clean prev outputs)
python3 cli.py render <resume.json> <cover.txt> <basename>
python3 cli.py render <files> <base> --no-clean

# log application
python3 cli.py log <basename> --company X --role Y \
    --role-category {business_analyst|data_analyst|data_scientist} \
    --seniority {entry|junior|mid|senior|lead} \
    --fit-score 4.5 --verdict {apply|stretch|skip} \
    --notes "..."

# list all logged applications
python3 cli.py list
```

Activate venv first: `source .venv/bin/activate`

---

## Scoring Rubric Detail

For each dimension, score 0-5:

- **Keyword coverage:** how many JD must-have keywords the candidate can credibly claim. 5 = nearly all; 0 = almost none.
- **Experience relevance:** years + role-type alignment. Mid-level analyst → mid-level analyst = 5. Junior → senior = 2.
- **Tech stack overlap:** candidate's tools ∩ JD tools / JD tools. Score = ratio × 5.
- **Seniority fit:** 5 = exact match. Underqualified by 1 level = 3. By 2 levels = 1. Overqualified by 1 = 4.
- **Domain fit:** same industry = 5. Adjacent = 3-4. Unrelated = 1-2.
- **Education fit:** meets stated min = 5. Above = 5 (cap). Below = 2-3 if substituted by experience.

Weighted total = Σ(score × weight). Round to one decimal.

---

## Auto-Memory Convention

User wants memory updated automatically — never asks "save this", expects it.

**Triggers — update memory immediately when:**
- New profile fact learned → edit `data/master_profile.json` (only if user opted to save)
- New JD scored / tailored / logged → tracker auto-updates via `cli.py log`; append a row to "Already-Logged Applications" table in this file IF user wants persistent CV of their search
- User feedback on style → update "Resume Output Standards" or "Anti-Patterns" sections
- New deal-breaker / preference → update `constraints` in master profile

**Append-only log:** `SESSION_LOG.md` (gitignored). One line per significant event:
```
[YYYY-MM-DD HH:MM] <action> — <context>
```

**Don't ask to save** — just save. User authorized this convention.

---

## Caveman / Terse Mode (Optional)

User can request terse responses ("caveman mode"): drop articles, fillers, pleasantries. Fragments OK. Code/commits/security written normally.

---

## You're Set

Read the user's master profile (if it exists), greet them, ask what they want to do (run wizard, score a JD, update something). Stay terse, technical, honest.
