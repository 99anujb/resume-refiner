"""Terminal-driven resume tailoring.

Designed to be driven by a smarter LLM (Claude in Claude Code) rather than
a paid API. Workflow:

  1. User shares a JD (paste / file path) with Claude in this terminal session.
  2. Claude reads master_profile.json + JD, produces a tailored_resume.json
     and a cover_letter.txt directly (no API call required).
  3. Claude runs:
        python cli.py render <tailored.json> <cover.txt> <out_basename>
     to produce the two PDFs at data/tailored/<out_basename>_*.pdf.

Subcommands:
  show-profile             - print the master_profile.json (so Claude has it in-context)
  render <resume_json> <cover_txt> <basename> - build PDFs
  log <basename> [--company X] [--role X] - append to tracker SQLite

The Streamlit + Gemini path remains available via app.py.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import tracker
from src.pdf_render import render_cover_letter_pdf, render_resume_pdf

OUT_DIR = ROOT / "data" / "tailored"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_PATH = ROOT / "data" / "master_profile.json"


def cmd_show_profile(_args: argparse.Namespace) -> None:
    print(PROFILE_PATH.read_text())


def cmd_render(args: argparse.Namespace) -> None:
    resume = json.loads(Path(args.resume_json).read_text())
    cover_text = Path(args.cover_txt).read_text() if args.cover_txt else None
    base = args.basename.strip()

    # Clean previous tailored outputs (resume/cover from prior JDs).
    # Keeps tracker.db (it lives in data/, not data/tailored/).
    # Keeps any file already starting with this base (so re-render of same JD is safe).
    if not args.no_clean:
        removed = []
        for f in OUT_DIR.iterdir():
            if f.is_file() and not f.name.startswith(base):
                f.unlink()
                removed.append(f.name)
        if removed:
            print(f"cleaned previous outputs: {', '.join(removed)}\n")

    pdf_bytes, info = render_resume_pdf(resume)
    out_resume = OUT_DIR / f"{base}_Resume.pdf"
    out_resume.write_bytes(pdf_bytes)
    print(f"resume:  {out_resume}  ({len(pdf_bytes)} bytes)  level={info.get('level_used')}  pages={info.get('pages')}  font={info.get('settings', {}).get('font_size_pt')}pt")

    out_cover = None
    if cover_text:
        cover_bytes = render_cover_letter_pdf(cover_text, resume["contact"])
        out_cover = OUT_DIR / f"{base}_CoverLetter.pdf"
        out_cover.write_bytes(cover_bytes)
        print(f"cover:   {out_cover}  ({len(cover_bytes)} bytes)")

    out_resume_json = OUT_DIR / f"{base}_resume.json"
    out_resume_json.write_text(json.dumps(resume, indent=2))
    print(f"json:    {out_resume_json}")

    print("\nRender info:", json.dumps(info, indent=2))


def cmd_log(args: argparse.Namespace) -> None:
    tracker.init_db()
    base = args.basename.strip()
    resume_pdf = OUT_DIR / f"{base}_Resume.pdf"
    cover_pdf = OUT_DIR / f"{base}_CoverLetter.pdf"
    fields = dict(
        company=args.company or "Unknown",
        role_title=args.role or "",
        role_category=args.role_category,
        seniority=args.seniority,
        fit_score=args.fit_score,
        verdict=args.verdict,
        status="draft",
        resume_pdf_path=str(resume_pdf) if resume_pdf.exists() else None,
        cover_pdf_path=str(cover_pdf) if cover_pdf.exists() else None,
        notes=args.notes,
    )
    fields = {k: v for k, v in fields.items() if v is not None}
    tid = tracker.add_application(**fields)
    print(f"logged application id={tid}")


def cmd_list(_args: argparse.Namespace) -> None:
    rows = tracker.list_applications()
    if not rows:
        print("No applications logged.")
        return
    for r in rows:
        print(f"#{r['id']:3d}  {r['status']:12s}  score={r.get('fit_score') or '—'}  "
              f"{r['company']}  ·  {r['role_title']}  ({r['last_update']})")


def main() -> None:
    p = argparse.ArgumentParser(prog="cli.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("show-profile").set_defaults(func=cmd_show_profile)

    rp = sub.add_parser("render", help="render resume + cover PDFs from JSON/TXT")
    rp.add_argument("resume_json", help="path to tailored resume JSON")
    rp.add_argument("cover_txt", nargs="?", default=None, help="path to cover letter text (optional)")
    rp.add_argument("basename", help="output basename, e.g. AnujBansal_DataAnalyst_FanDuel_20260506")
    rp.add_argument("--no-clean", action="store_true",
                    help="keep previous tailored outputs in data/tailored/ (default: clean)")
    rp.set_defaults(func=cmd_render)

    lp = sub.add_parser("log", help="add an entry to the tracker DB")
    lp.add_argument("basename", help="basename used in render step")
    lp.add_argument("--company")
    lp.add_argument("--role")
    lp.add_argument("--role-category", choices=["business_analyst", "data_analyst", "data_scientist"])
    lp.add_argument("--seniority")
    lp.add_argument("--fit-score", type=float)
    lp.add_argument("--verdict", choices=["apply", "stretch", "skip"])
    lp.add_argument("--notes")
    lp.set_defaults(func=cmd_log)

    sub.add_parser("list").set_defaults(func=cmd_list)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
