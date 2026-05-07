"""Render tailored resume + cover letter to single-page PDFs via WeasyPrint.

Resume uses iterative compression: try font/spacing levels until output fits 1 page.
"""
from __future__ import annotations

import ctypes
import ctypes.util
import io
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def _ensure_dylib_path() -> None:
    """macOS strips DYLD_FALLBACK_LIBRARY_PATH on Python re-exec under SIP.
    Inject Homebrew lib paths into the env before weasyprint/cffi loads dylibs.
    Also preload key dylibs via ctypes RTLD_GLOBAL as a belt-and-braces fix."""
    if sys.platform != "darwin":
        return
    extra = []
    for prefix in ("/opt/homebrew/lib", "/usr/local/lib"):
        if os.path.isdir(prefix):
            extra.append(prefix)
    if extra:
        existing = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = ":".join(extra + ([existing] if existing else []))

    libs = [
        "libgobject-2.0.0.dylib",
        "libpango-1.0.0.dylib",
        "libpangoft2-1.0.0.dylib",
        "libharfbuzz.0.dylib",
        "libfontconfig.1.dylib",
        "libgdk_pixbuf-2.0.0.dylib",
        "libglib-2.0.0.dylib",
        "libcairo.2.dylib",
    ]
    for prefix in extra:
        for lib in libs:
            p = os.path.join(prefix, lib)
            if os.path.exists(p):
                try:
                    ctypes.CDLL(p, mode=ctypes.RTLD_GLOBAL)
                except OSError:
                    pass


_ensure_dylib_path()

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


# Compression ladder: most generous → tightest. Each step shrinks vertical footprint.
# Dense ladder (largest → smallest). For each font size, tries multiple line heights
# before stepping down. First level that fits 1 page wins (max font without overflow).
COMPRESSION_LEVELS = [
    {"font_size_pt": 11.5, "line_height": 1.32, "name_size_pt": 16.0, "contact_size_pt": 10.0, "section_size_pt": 11.5},
    {"font_size_pt": 11.5, "line_height": 1.22, "name_size_pt": 16.0, "contact_size_pt": 10.0, "section_size_pt": 11.5},
    {"font_size_pt": 11.5, "line_height": 1.14, "name_size_pt": 15.5, "contact_size_pt": 9.5,  "section_size_pt": 11.5},
    {"font_size_pt": 11.0, "line_height": 1.28, "name_size_pt": 15.0, "contact_size_pt": 9.5,  "section_size_pt": 11.0},
    {"font_size_pt": 11.0, "line_height": 1.18, "name_size_pt": 15.0, "contact_size_pt": 9.5,  "section_size_pt": 11.0},
    {"font_size_pt": 11.0, "line_height": 1.12, "name_size_pt": 14.5, "contact_size_pt": 9.5,  "section_size_pt": 11.0},
    {"font_size_pt": 10.5, "line_height": 1.25, "name_size_pt": 14.0, "contact_size_pt": 9.5,  "section_size_pt": 10.5},
    {"font_size_pt": 10.5, "line_height": 1.16, "name_size_pt": 14.0, "contact_size_pt": 9.0,  "section_size_pt": 10.5},
    {"font_size_pt": 10.5, "line_height": 1.10, "name_size_pt": 13.5, "contact_size_pt": 9.0,  "section_size_pt": 10.5},
    {"font_size_pt": 10.0, "line_height": 1.22, "name_size_pt": 13.5, "contact_size_pt": 9.0,  "section_size_pt": 10.0},
    {"font_size_pt": 10.0, "line_height": 1.13, "name_size_pt": 13.5, "contact_size_pt": 9.0,  "section_size_pt": 10.0},
    {"font_size_pt": 10.0, "line_height": 1.08, "name_size_pt": 13.0, "contact_size_pt": 8.75, "section_size_pt": 10.0},
    {"font_size_pt": 9.5,  "line_height": 1.20, "name_size_pt": 13.0, "contact_size_pt": 8.75, "section_size_pt": 9.75},
    {"font_size_pt": 9.5,  "line_height": 1.13, "name_size_pt": 13.0, "contact_size_pt": 8.5,  "section_size_pt": 9.75},
    {"font_size_pt": 9.0,  "line_height": 1.18, "name_size_pt": 13.0, "contact_size_pt": 8.5,  "section_size_pt": 9.5},
    {"font_size_pt": 9.0,  "line_height": 1.10, "name_size_pt": 12.5, "contact_size_pt": 8.25, "section_size_pt": 9.5},
    {"font_size_pt": 8.75, "line_height": 1.10, "name_size_pt": 12.0, "contact_size_pt": 8.0,  "section_size_pt": 9.0},
    {"font_size_pt": 8.5,  "line_height": 1.08, "name_size_pt": 12.0, "contact_size_pt": 8.0,  "section_size_pt": 8.75},
    {"font_size_pt": 8.25, "line_height": 1.06, "name_size_pt": 11.5, "contact_size_pt": 7.75, "section_size_pt": 8.5},
]


def _render_html(tailored: dict[str, Any], level: dict[str, float]) -> str:
    css_tmpl = _env.get_template("resume.css")
    css = css_tmpl.render(**level)
    html_tmpl = _env.get_template("resume.html")
    return html_tmpl.render(css=css, **tailored)


def _page_count(pdf_bytes: bytes) -> int:
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader  # type: ignore
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return len(reader.pages)


def render_resume_pdf(tailored: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    """Render with iterative compression. Returns (pdf_bytes, debug_info)."""
    last_pdf = None
    for idx, level in enumerate(COMPRESSION_LEVELS):
        html = _render_html(tailored, level)
        pdf_bytes = HTML(string=html).write_pdf()
        pages = _page_count(pdf_bytes)
        last_pdf = pdf_bytes
        if pages <= 1:
            return pdf_bytes, {"level_used": idx, "pages": pages, "settings": level}
    # last resort: return tightest even if >1
    return last_pdf, {"level_used": len(COMPRESSION_LEVELS) - 1, "pages": _page_count(last_pdf), "warning": "exceeded 1 page even at tightest level"}


def render_cover_letter_pdf(body_text: str, contact: dict[str, Any],
                            today: str | None = None) -> bytes:
    today = today or datetime.now().strftime("%B %d, %Y")
    body = body_text.replace("{{DATE}}", today).replace("{{SOURCE}}", "your career site")
    html = _env.get_template("cover_letter.html").render(
        name=contact.get("name", ""),
        phone=contact.get("phone", ""),
        phone_tel=contact.get("phone_tel"),
        email=contact.get("email", ""),
        linkedin_label=contact.get("linkedin_label"),
        linkedin_url=contact.get("linkedin_url"),
        github_label=contact.get("github_label"),
        github_url=contact.get("github_url"),
        portfolio_label=contact.get("portfolio_label"),
        portfolio_url=contact.get("portfolio_url"),
        body=body,
    )
    return HTML(string=html).write_pdf()
