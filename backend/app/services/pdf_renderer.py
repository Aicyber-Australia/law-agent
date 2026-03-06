"""Render lawyer briefs into deterministic PDF output."""

from __future__ import annotations

import io
import re
import textwrap
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def _markdown_to_text_lines(markdown_text: str) -> list[str]:
    lines: list[str] = []
    for raw in (markdown_text or "").splitlines():
        line = raw.strip()
        if not line:
            lines.append("")
            continue

        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^[-*]\s+", "- ", line)
        line = re.sub(r"[`*_]", "", line)
        lines.append(line)

    return lines


def render_brief_pdf(
    *,
    markdown_content: str,
    conversation_id: str,
    brief_id: str,
    brief_version: int,
    jurisdiction: str | None,
) -> bytes:
    buffer = io.BytesIO()
    page_width, page_height = A4
    margin = 42
    content_width_chars = 102

    c = canvas.Canvas(buffer, pagesize=A4)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def new_page(y_start: int | None = None) -> float:
        if y_start is None:
            c.showPage()
            y = page_height - margin
        else:
            y = float(y_start)

        c.setFont("Helvetica-Bold", 16)
        c.drawString(margin, y, "AusLaw AI - Lawyer Brief")
        y -= 18

        c.setFont("Helvetica", 9)
        meta = (
            f"Brief ID: {brief_id}  |  Version: {brief_version}  |  "
            f"Conversation: {conversation_id}"
        )
        c.drawString(margin, y, meta)
        y -= 12
        c.drawString(margin, y, f"Jurisdiction: {jurisdiction or 'Australia'}  |  Generated: {generated_at}")
        y -= 12
        c.drawString(
            margin,
            y,
            "Disclaimer: General legal information only. Not legal advice.",
        )
        y -= 10
        c.line(margin, y, page_width - margin, y)
        y -= 14
        return y

    y = new_page(page_height - margin)

    c.setFont("Helvetica", 10)
    for line in _markdown_to_text_lines(markdown_content):
        wrapped = textwrap.wrap(line, width=content_width_chars) if line else [""]

        for part in wrapped:
            if y < margin + 24:
                y = new_page()
                c.setFont("Helvetica", 10)

            c.drawString(margin, y, part)
            y -= 12

    c.save()
    buffer.seek(0)
    return buffer.read()
