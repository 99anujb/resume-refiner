# Privacy

## Local-First

By default, this tool is local-first.

- Your master profile (`data/master_profile.json`) is stored on your machine only. It is **gitignored**, so even if you fork this repo, your profile won't accidentally be committed.
- The application tracker (`data/tracker.db`) is local SQLite. Also gitignored.
- Tailored resumes and cover letters (`data/tailored/`) are local PDFs. Also gitignored.

## What Goes to Anthropic (Claude)

When you run this tool inside Claude Code:

- The contents of files you open (master profile, JDs you paste) are sent to Anthropic's Claude API as part of your conversation.
- Anthropic's Claude API does not retain conversation contents for training by default; see [Anthropic's privacy policy](https://www.anthropic.com/legal/privacy).

## What Goes to Google (Gemini)

If you opt to use the Streamlit + Gemini path (`app.py`):

- The JD and your master profile are sent to Google's Gemini API.
- See [Google's Gemini API privacy policy](https://ai.google.dev/gemini-api/terms).
- Google may retain usage data per their policy.

## What Goes to GitHub

If you opt to use the GitHub fetcher to populate your project bank:

- Your GitHub username is sent to `api.github.com` (public unauthenticated requests).
- Only public repository data is fetched.

## What This Tool Never Does

- Never uploads your profile to any server controlled by the maintainers of this project.
- Never sends telemetry.
- Never logs to remote services.

## Recommendations

- Don't commit your `.env` or `data/master_profile.json` to a public fork.
- Don't share your generated PDFs publicly with PII visible.
- If you're applying to roles in regulated industries (healthcare, finance, government), confirm your local org's policies before using AI tooling on hiring docs.
