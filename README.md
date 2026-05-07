# Resume Refiner

> Tailor 1-page ATS-aware resumes + cover letters to any job description.
> Driven by Claude Code in your terminal. No paid API needed.

## What This Is

A terminal-driven resume tailoring tool that:

- Reads your master profile (built once from your existing resume(s) + GitHub repos)
- Scores any job description against your profile across 6 weighted dimensions
- Flags visa / location / PERM-style red flags before you waste time tailoring
- Generates a 1-page tailored resume + cover letter, embedding JD must-have keywords honestly
- Renders 1-page PDFs at 0.1" margins with auto-fitting compression (max font that fits)
- Tracks every application in a local SQLite log

The LLM doing the tailoring is **Claude in your Claude Code terminal** — no Anthropic / Gemini / OpenAI API key required. (A Streamlit + Gemini path exists in `app.py` but is optional/legacy.)

## Quick Start

### 1. Install Claude Code

https://claude.com/claude-code (free with subscription, or trial)

### 2. Clone this repo

```bash
git clone https://github.com/<you>/resume-refiner.git
cd resume-refiner
```

### 3. Set up Python env

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

WeasyPrint needs system libs on macOS:
```bash
brew install pango gdk-pixbuf libffi
```

On Linux:
```bash
sudo apt install libpango-1.0-0 libpangoft2-1.0-0
```

### 4. Open this directory in Claude Code

```bash
claude
```

Claude reads `CLAUDE.md` automatically and walks you through:

1. **Wizard** — upload your existing resume(s); Claude extracts a master profile
2. **GitHub** — paste your username; Claude fetches public repos for the project bank
3. **Visa / location form** — work auth, sponsorship now/future, eligible countries, deal-breakers
4. **Save preference** — save profile to disk OR keep in-memory only
5. **Done** — paste any JD and Claude scores, tailors, renders PDF, logs the application

### 5. Per-JD usage

Paste a job description into Claude. It will:

- Score the role 0-5 across keyword coverage, experience relevance, tech overlap, seniority fit, domain fit, education fit (weighted)
- Flag visa or PERM-style red flags
- Wait for your **"yes"** before tailoring (no surprises)
- Write `data/tailored/<basename>_resume.json` and `_cover.txt`
- Run `cli.py render` → 1-page PDFs in `data/tailored/`
- Log the application via `cli.py log`

## CLI

For power users / scripts:

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

# list logged apps
python3 cli.py list
```

## Project Layout

```
resume-refiner/
├── CLAUDE.md                          # wizard instructions Claude follows
├── README.md
├── LICENSE                            # MIT
├── PRIVACY.md
├── cli.py                             # render / log / list commands
├── app.py                             # optional Streamlit + Gemini path (legacy)
├── requirements.txt
├── .env.example                       # GEMINI_API_KEY (only for app.py path)
├── .gitignore                         # .env, data/master_profile.json, tracker.db, tailored/
├── src/
│   ├── pdf_render.py                  # WeasyPrint, dense compression ladder
│   ├── tracker.py                     # SQLite CRUD
│   ├── llm.py                         # Gemini wrapper (only used by app.py)
│   ├── jd_analyzer.py / fit_scorer.py / visa_check.py / tailor.py / cover_letter.py
├── templates/
│   ├── resume.html / resume.css       # 0.1" margins, dense layout
│   └── cover_letter.html              # 0.6" margins
├── data/
│   ├── master_profile.example.json    # generic sample profile (replace with your own via wizard)
│   └── tailored/                      # one active tailored resume + cover (auto-cleaned each render)
├── SKILLS_TO_ADD.md                   # free training queue to push fit scores higher
└── SESSION_LOG.md                     # append-only log Claude maintains
```

## Privacy

This tool is local-first.

- Your master profile, application tracker, and tailored output never leave your machine.
- The Streamlit + Gemini path (if you choose to use it) sends JD + profile data to Google's Gemini API — see Google's privacy policy.
- The default Claude Code path keeps everything on your machine + Anthropic's session boundaries (Claude doesn't store project files).
- See [PRIVACY.md](./PRIVACY.md).

## License

MIT — see [LICENSE](./LICENSE).

## Contributing

PRs welcome. Run `python3 -m pytest` (no tests yet — contribute some), keep new code typed, no extra dependencies without discussion.

## Credits

Built by [Anuj Bansal](https://github.com/99anujb) initially as a personal job-hunt tool, then generalized for public use.
