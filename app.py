"""Streamlit app: JD → visa check → fit score → approve → tailored resume + cover letter + tracker."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.cover_letter import generate_cover_letter
from src.fit_scorer import score_fit
from src.jd_analyzer import analyze_jd
from src.llm import load_profile
from src.pdf_render import render_cover_letter_pdf, render_resume_pdf
from src.tailor import tailor_resume
from src import tracker
from src.visa_check import visa_location_check

st.set_page_config(page_title="Resume Refiner", layout="wide")

OUT_DIR = Path(__file__).resolve().parent / "data" / "tailored"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", (s or "").strip().lower())
    return s.strip("_")[:60] or "untitled"


def init_state():
    for k, v in {
        "jd_text": "",
        "analysis": None,
        "visa": None,
        "fit": None,
        "tailored": None,
        "tailor_notes": "",
        "cover_notes": "",
        "resume_pdf": None,
        "cover_pdf": None,
        "render_info": None,
        "cover_text": None,
        "tracker_id": None,
    }.items():
        st.session_state.setdefault(k, v)


init_state()
profile = load_profile()
tracker.init_db()

tab_apply, tab_history = st.tabs(["Apply to a JD", "Application History"])

# ============================================================
# TAB 1: APPLY
# ============================================================
with tab_apply:
    st.title("Resume Refiner")
    st.caption("Paste JD → fit check → visa check → approve → tailored 1-page resume + cover letter.")

    with st.sidebar:
        st.subheader("Master Profile")
        st.write(f"**Name:** {profile['contact']['name']}")
        c = profile.get("constraints", {})
        st.write(f"**Auth:** {'Sponsorship needed (future)' if c.get('needs_sponsorship_future') else 'No sponsorship needed'}")
        st.write(f"**Location:** {c.get('current_location', '—')}")
        st.write(f"**Experience entries:** {len(profile['experience'])}")
        st.write(f"**Project bank:** {len(profile['projects'])}")
        s = tracker.stats()
        if s:
            st.markdown("---")
            st.subheader("Tracker")
            for status, n in s.items():
                st.write(f"{status}: {n}")
        if st.button("Reset session"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    # --- 1. JD input ---
    st.markdown("### 1. Paste Job Description")
    st.session_state.jd_text = st.text_area(
        "Job description text",
        value=st.session_state.jd_text,
        height=240,
        placeholder="Paste full JD including title, responsibilities, qualifications...",
    )
    if st.button("Analyze JD", type="primary", disabled=not st.session_state.jd_text.strip()):
        with st.spinner("Running JD analysis + visa check + fit score in parallel..."):
            try:
                st.session_state.analysis = analyze_jd(st.session_state.jd_text, profile)
                st.session_state.visa = visa_location_check(
                    st.session_state.jd_text, profile.get("constraints", {})
                )
                st.session_state.fit = score_fit(st.session_state.analysis, profile)
                st.session_state.tailored = None
                st.session_state.resume_pdf = None
                st.session_state.cover_pdf = None
                st.session_state.tracker_id = None
            except Exception as e:
                st.error(f"Analysis failed: {e}")

    # --- 2. Visa/Location ---
    if st.session_state.visa:
        v = st.session_state.visa
        st.markdown("### 2. Visa & Location Check")
        verdict = v.get("verdict", "unclear")
        if verdict == "stop":
            st.error("STOP — visa/location dealbreaker detected.")
        elif verdict == "caution":
            st.warning("CAUTION — soft mismatch.")
        else:
            st.success("GO — no visa/location blockers.")
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**Sponsorship required:** {v.get('sponsorship_required_by_jd')}")
            st.write(f"**Sponsorship offered:** {v.get('sponsorship_offered_by_jd')}")
            st.write(f"**Clearance required:** {v.get('clearance_required')}")
        with c2:
            loc = v.get("location") or {}
            if not isinstance(loc, dict):
                loc = {"raw": loc}
            st.write(f"**Location type:** {loc.get('type')}")
            st.write(f"**Country / city:** {loc.get('country')} / {loc.get('city') or '—'}")
            st.write(f"**Matches candidate:** {loc.get('matches_candidate')}")
        def _fmt_issue(x):
            if isinstance(x, dict):
                r = x.get("reason") or x.get("message") or ""
                e = x.get("evidence") or ""
                return f"{r}" + (f" — \"{e}\"" if e else "")
            return str(x)
        if v.get("blockers"):
            st.error("Blockers: " + " | ".join(_fmt_issue(b) for b in v["blockers"]))
        if v.get("warnings"):
            st.warning("Warnings: " + " | ".join(_fmt_issue(w) for w in v["warnings"]))

    # --- 3. Fit score ---
    if st.session_state.fit:
        f = st.session_state.fit
        st.markdown("### 3. Fit Score")
        score = f.get("overall_score", 0)
        verdict = f.get("verdict", "—")
        m1, m2, m3 = st.columns([1, 1, 3])
        with m1:
            st.metric("Score", f"{score}/5")
        with m2:
            st.metric("Verdict", verdict.upper())
        with m3:
            st.write(f.get("recommendation", ""))

        st.markdown("**Per-dimension breakdown**")
        dims = f.get("dimensions", {})
        for dim_name, dim in dims.items():
            s = dim.get("score", 0)
            w = dim.get("weight", 0)
            note = dim.get("note", "")
            st.progress(s / 5, text=f"{dim_name} — {s}/5 (w={w}) — {note}")

        c4, c5 = st.columns(2)
        with c4:
            st.markdown("**Strengths**")
            for s in f.get("strengths", []):
                st.write(f"- {s}")
        with c5:
            st.markdown("**Weaknesses**")
            for w in f.get("weaknesses", []):
                st.write(f"- {w}")
        if f.get("red_flags"):
            st.error("Red flags: " + "; ".join(f["red_flags"]))
        if f.get("fix_suggestions"):
            st.markdown("**Fix suggestions**")
            for fx in f["fix_suggestions"]:
                if isinstance(fx, dict):
                    st.write(f"- ({fx.get('effort','?')}) **{fx.get('gap','')}** → {fx.get('action','')}")
                elif isinstance(fx, list):
                    # tolerate [gap, action, effort?] or nested
                    st.write("- " + " | ".join(str(x) for x in fx))
                else:
                    st.write(f"- {fx}")

    # --- 4. JD analysis ---
    if st.session_state.analysis:
        a = st.session_state.analysis
        st.markdown("### 4. JD Analysis")
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**Company:** {a.get('company') or '—'}")
            st.write(f"**Role:** {a.get('role_title')} ({a.get('role_category')})")
            st.write(f"**Seniority:** {a.get('seniority')}")
        with c2:
            st.write(f"**Domain:** {', '.join(a.get('domain', []) or ['—'])}")
            st.write(f"**Tone:** {', '.join(a.get('tone_signals', []) or ['—'])}")
        st.write("**Responsibilities:** " + (a.get("responsibilities_summary") or "—"))
        c3, c4 = st.columns(2)
        with c3:
            st.markdown("**Must-have keywords**")
            st.write(", ".join(a.get("must_have_keywords", [])))
        with c4:
            st.markdown("**Gaps vs profile**")
            gaps = a.get("gaps_vs_profile", [])
            if gaps:
                st.warning(", ".join(gaps))
            else:
                st.write("None.")
        with st.expander("Raw analysis JSON"):
            st.json(a)

    # --- 5. Approve & tailor ---
    if st.session_state.analysis:
        st.markdown("### 5. Approve & Tailor")
        verdict = (st.session_state.fit or {}).get("verdict")
        visa_verdict = (st.session_state.visa or {}).get("verdict")
        if visa_verdict == "stop":
            st.error("Visa/location blocker present. Tailoring blocked unless you override.")
        if verdict == "skip":
            st.warning(f"Fit score is below threshold (verdict={verdict}). You can still tailor but consider skipping.")

        st.session_state.tailor_notes = st.text_area(
            "Optional notes for tailoring (e.g., 'emphasize SQL', 'tone down ML')",
            value=st.session_state.tailor_notes,
            height=80,
        )
        force = visa_verdict == "stop"
        col_btn, col_ovr = st.columns([1, 2])
        with col_btn:
            tailor_clicked = st.button("Approve → Tailor Resume", type="primary")
        with col_ovr:
            override = st.checkbox("Override visa block", value=False) if force else True

        if tailor_clicked and (override or not force):
            with st.spinner("Tailoring resume..."):
                try:
                    st.session_state.tailored = tailor_resume(
                        st.session_state.analysis, profile, notes=st.session_state.tailor_notes or None
                    )
                    pdf_bytes, info = render_resume_pdf(st.session_state.tailored)
                    st.session_state.resume_pdf = pdf_bytes
                    st.session_state.render_info = info
                except Exception as e:
                    st.error(f"Tailoring failed: {e}")

    # --- 6. Tailored output + cover letter ---
    if st.session_state.tailored and st.session_state.resume_pdf:
        t = st.session_state.tailored
        st.markdown("### 6. Tailored Resume")
        info = st.session_state.render_info or {}
        if info.get("warning"):
            st.warning(f"Render warning: {info['warning']} (pages={info.get('pages')})")
        else:
            st.success(f"1-page fit at compression level {info.get('level_used')}, font {info.get('settings', {}).get('font_size_pt')}pt")

        cov = t.get("keyword_coverage", {})
        k1, k2 = st.columns(2)
        with k1:
            st.markdown("**Keywords placed**")
            st.write(", ".join(cov.get("must_have_hit", [])) or "—")
        with k2:
            st.markdown("**Keywords missed (honesty)**")
            missed = cov.get("must_have_missed", [])
            if missed:
                st.warning(", ".join(missed))
            else:
                st.write("None.")

        company = (st.session_state.analysis or {}).get("company") or "company"
        role = (st.session_state.analysis or {}).get("role_title") or t.get("target_title", "role")
        base = f"AnujBansal_{_slug(role)}_{_slug(company)}_{datetime.now().strftime('%Y%m%d')}"

        st.download_button(
            "Download Resume PDF",
            data=st.session_state.resume_pdf,
            file_name=f"{base}_Resume.pdf",
            mime="application/pdf",
            type="primary",
        )

        with st.expander("Tailored resume JSON (debug)"):
            st.json(t)

        st.markdown("### 7. Cover Letter")
        st.session_state.cover_notes = st.text_area(
            "Optional notes for the cover letter",
            value=st.session_state.cover_notes,
            height=80,
        )
        if st.button("Generate Cover Letter"):
            with st.spinner("Drafting cover letter..."):
                try:
                    txt = generate_cover_letter(
                        t, st.session_state.analysis, notes=st.session_state.cover_notes or None
                    )
                    st.session_state.cover_text = txt
                    st.session_state.cover_pdf = render_cover_letter_pdf(txt, t["contact"])
                except Exception as e:
                    st.error(f"Cover letter failed: {e}")

        if st.session_state.cover_text:
            st.text_area("Cover letter draft", value=st.session_state.cover_text, height=320)
        if st.session_state.cover_pdf:
            st.download_button(
                "Download Cover Letter PDF",
                data=st.session_state.cover_pdf,
                file_name=f"{base}_CoverLetter.pdf",
                mime="application/pdf",
            )

        # --- 8. Save + log to tracker ---
        st.markdown("### 8. Save & Track")
        save_col, log_col = st.columns(2)
        with save_col:
            if st.button("Save outputs to data/tailored/"):
                (OUT_DIR / f"{base}_Resume.pdf").write_bytes(st.session_state.resume_pdf)
                if st.session_state.cover_pdf:
                    (OUT_DIR / f"{base}_CoverLetter.pdf").write_bytes(st.session_state.cover_pdf)
                (OUT_DIR / f"{base}_resume.json").write_text(json.dumps(t, indent=2))
                (OUT_DIR / f"{base}_analysis.json").write_text(json.dumps(st.session_state.analysis, indent=2))
                st.success(f"Saved to data/tailored/{base}_*")
        with log_col:
            if st.button("Log to tracker", type="primary"):
                resume_path = str(OUT_DIR / f"{base}_Resume.pdf")
                cover_path = str(OUT_DIR / f"{base}_CoverLetter.pdf") if st.session_state.cover_pdf else None
                (OUT_DIR / f"{base}_Resume.pdf").write_bytes(st.session_state.resume_pdf)
                if st.session_state.cover_pdf:
                    (OUT_DIR / f"{base}_CoverLetter.pdf").write_bytes(st.session_state.cover_pdf)
                tid = tracker.add_application(
                    company=(st.session_state.analysis or {}).get("company") or "Unknown",
                    role_title=(st.session_state.analysis or {}).get("role_title") or "",
                    role_category=(st.session_state.analysis or {}).get("role_category"),
                    seniority=(st.session_state.analysis or {}).get("seniority"),
                    location=json.dumps((st.session_state.visa or {}).get("location", {})),
                    fit_score=(st.session_state.fit or {}).get("overall_score"),
                    verdict=(st.session_state.fit or {}).get("verdict"),
                    visa_verdict=(st.session_state.visa or {}).get("verdict"),
                    status="draft",
                    resume_pdf_path=resume_path,
                    cover_pdf_path=cover_path,
                    jd_text=st.session_state.jd_text,
                    analysis_json=json.dumps(st.session_state.analysis or {}),
                    fit_json=json.dumps(st.session_state.fit or {}),
                )
                st.session_state.tracker_id = tid
                st.success(f"Logged as application id={tid}")

# ============================================================
# TAB 2: HISTORY
# ============================================================
with tab_history:
    st.title("Application History")
    apps = tracker.list_applications()
    if not apps:
        st.info("No applications logged yet.")
    else:
        st.write(f"**{len(apps)} applications.**")
        for a in apps:
            with st.expander(f"#{a['id']} · {a['company']} · {a['role_title']} · {a['status']}  [score {a.get('fit_score')}]"):
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**Last update:** {a['last_update']}")
                    st.write(f"**Applied date:** {a.get('applied_date') or '—'}")
                    st.write(f"**Verdict:** {a.get('verdict')} · **Visa:** {a.get('visa_verdict')}")
                with c2:
                    st.write(f"**Resume:** {a.get('resume_pdf_path') or '—'}")
                    st.write(f"**Cover:** {a.get('cover_pdf_path') or '—'}")
                new_status = st.selectbox(
                    "Status",
                    tracker.STATUSES,
                    index=tracker.STATUSES.index(a["status"]) if a["status"] in tracker.STATUSES else 0,
                    key=f"status_{a['id']}",
                )
                applied_date = st.text_input(
                    "Applied date (YYYY-MM-DD)",
                    value=a.get("applied_date") or "",
                    key=f"adate_{a['id']}",
                )
                notes = st.text_area("Notes", value=a.get("notes") or "", key=f"notes_{a['id']}", height=80)
                bcol1, bcol2 = st.columns(2)
                with bcol1:
                    if st.button("Update", key=f"upd_{a['id']}"):
                        tracker.update_application(
                            a["id"],
                            status=new_status,
                            applied_date=applied_date or None,
                            notes=notes or None,
                        )
                        st.rerun()
                with bcol2:
                    if st.button("Delete", key=f"del_{a['id']}"):
                        tracker.delete_application(a["id"])
                        st.rerun()
