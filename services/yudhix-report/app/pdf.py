"""Draws a report (from build.build) as an A4 PDF with ReportLab.

Layout: a cover page (title, audience, period, workspaces, contents), then one numbered section after
another. Every later page has a running header and a "Page n of N" footer.
"""
import io
from datetime import datetime
from typing import Dict, List

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (CondPageBreak, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)
from xml.sax.saxutils import escape

# Same tokens as the web app (light theme)
INK = colors.HexColor("#18181b")
INK_2 = colors.HexColor("#52525b")
INK_3 = colors.HexColor("#71717a")
LINE = colors.HexColor("#e4e4e7")
SOFT = colors.HexColor("#f4f4f5")
BRAND = colors.HexColor("#4f46e5")
BRAND_SOFT = colors.HexColor("#eef2ff")
NEG = colors.HexColor("#dc2626")
POS = colors.HexColor("#2563eb")
NEU = colors.HexColor("#d4d4d8")
TONE = {"good": colors.HexColor("#15803d"), "warn": colors.HexColor("#b45309"),
        "bad": colors.HexColor("#b91c1c"), "info": INK_2}
TONE_SOFT = {"good": colors.HexColor("#ecfdf3"), "warn": colors.HexColor("#fffbeb"),
             "bad": colors.HexColor("#fef2f2"), "info": SOFT}
SEVERITY_TONE = {"High": "bad", "Medium": "warn", "Low": "info"}

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

FONT, BOLD = "Helvetica", "Helvetica-Bold"

S = {
    "h1": ParagraphStyle("h1", fontName=BOLD, fontSize=26, leading=31, textColor=INK, spaceAfter=6),
    "lead": ParagraphStyle("lead", fontName=FONT, fontSize=12, leading=17, textColor=INK_2),
    "h2": ParagraphStyle("h2", fontName=BOLD, fontSize=15, leading=19, textColor=INK, spaceBefore=4, spaceAfter=2),
    "desc": ParagraphStyle("desc", fontName=FONT, fontSize=9.5, leading=13, textColor=INK_3, spaceAfter=8),
    "h3": ParagraphStyle("h3", fontName=BOLD, fontSize=10.5, leading=14, textColor=INK, spaceBefore=6, spaceAfter=4),
    "body": ParagraphStyle("body", fontName=FONT, fontSize=9.5, leading=13.5, textColor=INK),
    "small": ParagraphStyle("small", fontName=FONT, fontSize=8, leading=10.5, textColor=INK_3),
    "note": ParagraphStyle("note", fontName=FONT, fontSize=8.3, leading=11.5, textColor=INK_3, spaceBefore=4),
    "cell": ParagraphStyle("cell", fontName=FONT, fontSize=8.3, leading=10.8, textColor=INK),
    "cellr": ParagraphStyle("cellr", fontName=FONT, fontSize=8.3, leading=10.8, textColor=INK, alignment=TA_RIGHT),
    "head": ParagraphStyle("head", fontName=BOLD, fontSize=7.8, leading=10, textColor=INK_2),
    "headr": ParagraphStyle("headr", fontName=BOLD, fontSize=7.8, leading=10, textColor=INK_2, alignment=TA_RIGHT),
    "kl": ParagraphStyle("kl", fontName=FONT, fontSize=8, leading=10, textColor=INK_3),
    "kv": ParagraphStyle("kv", fontName=BOLD, fontSize=18, leading=22, textColor=INK),
    "ks": ParagraphStyle("ks", fontName=FONT, fontSize=7.8, leading=10, textColor=INK_3),
}

_REPLACE = {"★": "*", "→": ">", "←": "<", "−": "-", "✓": "", "✔": "", " ": " "}


def clean(text) -> str:
    """Helvetica covers Windows-1252 only: swap a few symbols and drop what it can't draw."""
    s = "" if text is None else str(text)
    for a, b in _REPLACE.items():
        s = s.replace(a, b)
    return s.encode("cp1252", "ignore").decode("cp1252")


def safe(text) -> str:
    """clean() plus escaping, for Paragraph markup."""
    return escape(clean(text))


def P(text, style="body") -> Paragraph:
    return Paragraph(safe(text), S[style])


def _date(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d %b %Y")
    except (TypeError, ValueError):
        return "-"


# ---- blocks ------------------------------------------------------------------------------------

def kpis(block: Dict) -> List:
    items = block["items"]
    per_row = 3
    cells, row = [], []
    cw = CONTENT_W / per_row
    for it in items:
        parts = [P(it["label"], "kl"), Paragraph(safe(it["value"]), ParagraphStyle(
            "kvt", parent=S["kv"], textColor=TONE.get(it.get("tone") or "info") if it.get("tone") in ("good", "bad", "warn") else INK))]
        if it.get("sub"):
            parts.append(P(it["sub"], "ks"))
        d = it.get("delta")
        if d:
            parts.append(Paragraph(safe(d["text"]), ParagraphStyle("kd", parent=S["ks"], textColor=TONE.get(d["tone"], INK_2),
                                                                   fontName=BOLD)))
        row.append(parts)
        if len(row) == per_row:
            cells.append(row)
            row = []
    if row:
        cells.append(row + [""] * (per_row - len(row)))
    t = Table(cells, colWidths=[cw] * per_row)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.6, LINE),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return [t, Spacer(1, 8)]


def findings(block: Dict) -> List:
    rows = []
    for f in block["items"]:
        tone = f.get("tone", "info")
        dot = Drawing(8, 8)
        dot.add(Rect(0, 1, 6, 6, rx=3, ry=3, fillColor=TONE.get(tone, INK_2), strokeColor=None))
        rows.append([dot, P(f["text"])])
    t = Table(rows, colWidths=[12, CONTENT_W - 12])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5), ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (0, -1), 6),
    ]))
    return [t, Spacer(1, 6)]


def table(block: Dict) -> List:
    cols = block["columns"]
    out: List = []
    if block.get("title"):
        out.append(P(block["title"], "h3"))
    if not block["rows"]:
        return out + [P(block.get("empty") or "Nothing to show.", "note")]
    head = [P(c["label"], "headr" if c["align"] == "right" else "head") for c in cols]
    sev_col = block.get("severityColumn")
    body = []
    for r in block["rows"]:
        line = []
        for i, (c, v) in enumerate(zip(cols, r)):
            if sev_col is not None and i == sev_col:
                tone = SEVERITY_TONE.get(v, "info")
                line.append(Paragraph(safe(v), ParagraphStyle("sev", parent=S["cell"], fontName=BOLD, textColor=TONE[tone])))
            else:
                line.append(P(v, "cellr" if c["align"] == "right" else "cell"))
        body.append(line)
    widths = _col_widths(cols, block["rows"])
    t = Table([head] + body, colWidths=widths, repeatRows=1)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK_3),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    for i in range(1, len(body) + 1):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#fafafa")))
    t.setStyle(TableStyle(style))
    return out + [t, Spacer(1, 8)]


def _col_widths(cols: List[Dict], rows: List[List]) -> List[float]:
    """Numbers get what they need; text columns share the rest by how long their content is."""
    need, word = [], []
    for i, c in enumerate(cols):
        cells = [clean(r[i]) for r in rows if i < len(r)]
        longest = max([stringWidth(clean(c["label"]), BOLD, 7.8)] + [stringWidth(x, FONT, 8.3) for x in cells])
        need.append(longest + 10)
        words = [w for x in cells for w in x.split()] + clean(c["label"]).split()
        word.append(max([stringWidth(w, FONT, 8.3) for w in words] + [20]) + 10)
    fixed = [min(n, 80) if c["align"] == "right" else None for c, n in zip(cols, need)]
    used = sum(f for f in fixed if f)
    free = CONTENT_W - used
    text_need = [n for f, n in zip(fixed, need) if f is None]
    total = sum(min(n, 260) for n in text_need) or 1
    widths = []
    for f, n, wmin in zip(fixed, need, word):
        widths.append(f if f is not None else max(48, wmin, free * min(n, 260) / total))
    scale = CONTENT_W / sum(widths)
    return [w * scale for w in widths]


def legend(d: Drawing, x: float, y: float):
    for label, color in (("Negative", NEG), ("Neutral", NEU), ("Positive", POS)):
        d.add(Rect(x, y, 7, 7, rx=1.5, ry=1.5, fillColor=color, strokeColor=None))
        d.add(String(x + 10, y + 0.5, label, fontName=FONT, fontSize=7.5, fillColor=INK_2))
        x += 14 + stringWidth(label, FONT, 7.5) + 10


def bars(block: Dict) -> List:
    rows = block["rows"]
    label_w, value_w, row_h, gap = 120, 70, 12, 9
    h = 18 + len(rows) * (row_h + gap)
    d = Drawing(CONTENT_W, h)
    legend(d, 0, h - 9)
    bar_w = CONTENT_W - label_w - value_w
    y = h - 18 - row_h - 4
    for r in rows:
        total = r["negative"] + r["neutral"] + r["positive"]
        name = clean(r["label"])
        while stringWidth(name + "...", BOLD, 8.3) > label_w - 10 and len(name) > 4:
            name = name[:-2]
        if name != clean(r["label"]):
            name = name.rstrip() + "..."
        d.add(String(0, y + 6.5, name, fontName=BOLD, fontSize=8.3, fillColor=INK))
        if r.get("sub"):
            d.add(String(0, y - 2.5, clean(r["sub"]), fontName=FONT, fontSize=7, fillColor=INK_3))
        x = label_w
        segs = [(r["negative"], NEG), (r["neutral"], NEU), (r["positive"], POS)]
        segs = [(v, c) for v, c in segs if v]
        for i, (v, c) in enumerate(segs):
            w = bar_w * v / total if total else 0
            gap_px = 1.5 if i < len(segs) - 1 else 0
            d.add(Rect(x, y, max(w - gap_px, 1), row_h, fillColor=c, strokeColor=None))
            x += w
        neg = round(100 * r["negative"] / total) if total else 0
        pos = round(100 * r["positive"] / total) if total else 0
        d.add(String(label_w + bar_w + 6, y + 3, f"{neg}% neg  {pos}% pos", fontName=FONT, fontSize=7.5, fillColor=INK_2))
        y -= row_h + gap
    out: List = []
    if block.get("title"):
        out.append(P(block["title"], "h3"))
    return out + [d, Spacer(1, 8)]


def trend(block: Dict) -> List:
    pts = block["points"]
    h, left, bottom, top = 170, 34, 26, 18
    d = Drawing(CONTENT_W, h)
    legend(d, left, h - 9)
    plot_w, plot_h = CONTENT_W - left - 4, h - bottom - top - 6
    peak = max([p["negative"] + p["neutral"] + p["positive"] for p in pts] + [1])
    step = _nice_step(peak)
    ymax = step * -(-peak // step)
    for i in range(0, int(ymax // step) + 1):
        v = i * step
        y = bottom + plot_h * v / ymax
        d.add(Line(left, y, left + plot_w, y, strokeColor=LINE if v else INK_3, strokeWidth=0.5))
        d.add(String(left - 4, y - 2.5, _short(v), fontName=FONT, fontSize=7, fillColor=INK_3, textAnchor="end"))
    n = len(pts)
    slot = plot_w / max(n, 1)
    bw = max(min(slot * 0.68, 22), 1.5)
    every = max(1, -(-n // 12))
    for i, p in enumerate(pts):
        x = left + i * slot + (slot - bw) / 2
        y = bottom
        for v, c in ((p["negative"], NEG), (p["neutral"], NEU), (p["positive"], POS)):
            if v:
                hh = plot_h * v / ymax
                d.add(Rect(x, y, bw, max(hh - (1 if hh > 2 else 0), 0.6), fillColor=c, strokeColor=None))
                y += hh
        if i % every == 0:
            d.add(String(x + bw / 2, bottom - 11, clean(p["label"]), fontName=FONT, fontSize=6.8, fillColor=INK_3,
                         textAnchor="middle"))
    out: List = []
    if block.get("title"):
        out.append(P(block["title"], "h3"))
    return out + [d, Spacer(1, 6)]


def _nice_step(peak: float) -> int:
    raw = peak / 4
    mag = 10 ** (len(str(int(raw))) - 1) if raw >= 1 else 1
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return max(1, int(m * mag))
    return int(10 * mag)


def _short(v: float) -> str:
    return f"{v / 1000:g}K" if v >= 1000 else f"{v:g}"


def note(block: Dict) -> List:
    return [P(block["text"], "note"), Spacer(1, 4)]


RENDER = {"kpis": kpis, "findings": findings, "table": table, "bars": bars, "trend": trend, "note": note}


# ---- pages --------------------------------------------------------------------------------------

def cover(report: Dict) -> List:
    out: List = [Spacer(1, 28 * mm)]
    out.append(Paragraph(f'<font color="#4f46e5"><b>YUDHIX</b></font>  <font color="#71717a">'
                         f'{safe(report["audience"]["label"].upper())} REPORT</font>',
                         ParagraphStyle("brand", fontName=FONT, fontSize=10, leading=14, textColor=INK_3)))
    out.append(Spacer(1, 6))
    out.append(P(report["title"], "h1"))
    out.append(P(report["audience"]["description"], "lead"))
    out.append(Spacer(1, 12))
    period = report["period"]
    span = (f'{_date(period["from"])} - {_date(period["to"])}' if period.get("from") else f'Up to {_date(period["to"])}')
    names = ", ".join(w["name"] + (" (demo)" if w.get("isDemo") and "demo" not in w["name"].lower() else "")
                      for w in report["workspaces"])
    facts = [
        ["Prepared for", report["audience"]["for"]],
        ["Period", f'{period["label"]} ({span})'],
        [f'Workspace{"s" if len(report["workspaces"]) != 1 else ""}', names],
        ["Prepared by", f'{report["preparedBy"]["name"]} ({report["preparedBy"]["email"]})'],
        ["Generated", _date(report["generatedAt"])],
    ]
    t = Table([[P(a, "kl"), P(b)] for a, b in facts], colWidths=[34 * mm, CONTENT_W - 34 * mm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    out += [t, Spacer(1, 16), P("Contents", "h3")]
    toc = [[P(f'{i}.', "body"), P(s["title"], "body"), P(s["description"], "small")]
           for i, s in enumerate(report["sections"], 1)]
    tt = Table(toc, colWidths=[8 * mm, 52 * mm, CONTENT_W - 60 * mm])
    tt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    out += [tt, Spacer(1, 14),
            P("Every number in this report comes straight from the workspace data. Findings and risks are written "
              "by fixed rules from those numbers, not by AI.", "note")]
    return out


class _NumberedCanvas(rl_canvas.Canvas):
    """Holds pages until the end so the footer can say "Page n of N"."""

    def __init__(self, *args, report: Dict = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._pages = []
        self._report = report

    def showPage(self):
        self._pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._pages)
        for state in self._pages:
            self.__dict__.update(state)
            self._decorate(total)
            super().showPage()
        super().save()

    def _decorate(self, total: int):
        page = self._pageNumber
        r = self._report
        self.setFillColor(BRAND)
        self.rect(0, PAGE_H - 4, PAGE_W, 4, stroke=0, fill=1)
        if page > 1:
            self.setFont(BOLD, 8)
            self.setFillColor(INK)
            self.drawString(MARGIN, PAGE_H - 12 * mm, "YUDHIX")
            self.setFont(FONT, 8)
            self.setFillColor(INK_3)
            self.drawString(MARGIN + 36, PAGE_H - 12 * mm, clean(r["title"]))
            self.drawRightString(PAGE_W - MARGIN, PAGE_H - 12 * mm, clean(r["period"]["label"]))
            self.setStrokeColor(LINE)
            self.setLineWidth(0.5)
            self.line(MARGIN, PAGE_H - 14 * mm, PAGE_W - MARGIN, PAGE_H - 14 * mm)
        self.setFont(FONT, 7.5)
        self.setFillColor(INK_3)
        self.drawString(MARGIN, 10 * mm, clean(f'Confidential. Prepared for {r["audience"]["for"]}.'))
        self.drawRightString(PAGE_W - MARGIN, 10 * mm, f"Page {page} of {total}")


def render(report: Dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=20 * mm,
                            bottomMargin=17 * mm, title=report["title"], author="Yudhix",
                            subject=f'{report["period"]["label"]}: ' + ", ".join(w["name"] for w in report["workspaces"]),
                            creator="yudhix-report")
    story: List = cover(report)
    for i, s in enumerate(report["sections"], 1):
        story.append(PageBreak() if i == 1 else CondPageBreak(70 * mm))
        head = [P(f'{i}. {s["title"]}', "h2"), P(s["description"], "desc")]
        blocks = s["blocks"]
        first = RENDER[blocks[0]["type"]](blocks[0]) if blocks else []
        story.append(KeepTogether(head + first[:2]))
        story += first[2:]
        for b in blocks[1:]:
            story += RENDER[b["type"]](b)
        story.append(Spacer(1, 10))
    doc.build(story, canvasmaker=lambda *a, **k: _NumberedCanvas(*a, report=report, **k))
    return buf.getvalue()
