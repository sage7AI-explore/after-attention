"""Build the After Attention paper PDF from the markdown draft (ReportLab)."""
import re
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Table, TableStyle, Image, KeepTogether)

SRC = "paper/After_Attention_draft_v0.10.md"
OUT = "paper/After_Attention_draft_v0.10.pdf"
FIG = "figures/fig_outcomes_v2.png"
RUNNING = "After Attention: The Economics of Markets Where the Buyer Is an Agent"

body = ParagraphStyle("body", fontName="Times-Roman", fontSize=10.5, leading=14,
                      alignment=TA_JUSTIFY, spaceAfter=6)
h1 = ParagraphStyle("h1", fontName="Times-Bold", fontSize=13, leading=16,
                    spaceBefore=14, spaceAfter=6)
h2 = ParagraphStyle("h2", fontName="Times-Bold", fontSize=11.5, leading=14,
                    spaceBefore=10, spaceAfter=4)
h3 = ParagraphStyle("h3", fontName="Times-Italic", fontSize=11, leading=13,
                    spaceBefore=8, spaceAfter=3)
title = ParagraphStyle("title", fontName="Times-Bold", fontSize=17, leading=21,
                       alignment=TA_CENTER, spaceAfter=8)
authors = ParagraphStyle("authors", fontName="Times-Roman", fontSize=11.5, leading=15,
                         alignment=TA_CENTER, spaceAfter=3)
small = ParagraphStyle("small", fontName="Times-Italic", fontSize=9.5, leading=12,
                       alignment=TA_CENTER, spaceAfter=12, textColor=colors.HexColor("#444444"))
cell = ParagraphStyle("cell", fontName="Times-Roman", fontSize=8.5, leading=10.5)
cellb = ParagraphStyle("cellb", fontName="Times-Bold", fontSize=8.5, leading=10.5)
cap = ParagraphStyle("cap", fontName="Times-Italic", fontSize=9, leading=11.5,
                     spaceBefore=3, spaceAfter=10)

GREEK = {r"\alpha": "\u03b1", r"\gamma": "\u03b3", r"\beta": "\u03b2", r"\lambda": "\u03bb",
         r"\mu_t": "\u03bc_t", r"\theta_q": "\u03b8_q", r"\sigma_\varepsilon": "\u03c3\u03b5",
         r"\varepsilon": "\u03b5", r"\eta": "\u03b7", r"\sigma": "\u03c3", r"\Pi": "\u03a0",
         r"\pi": "\u03c0", r"\times": "\u00d7", r"\geq": "\u2265", r"\to": "\u2192",
         r"\approx": "\u2248", r"\in": "\u2208", r"\ldots": "...", r"\{": "{", r"\}": "}",
         r"\,": " ", r"\;": " ", r"\qquad": "    ", r"\text{and}": "and", r"\tag": "",
         r"\log": "log", r"\sim": "~", r"\max": "max", r"\partial": "∂",
         r"\left(": "(", r"\right)": ")", r"\cdot": "·", r"\leq": "≤",
         r"\quad": "  ", r"\ast": "*", r"\alpha^*": "α*",
         r"\Delta": "Δ", r"\equiv": "≡", r"\blacksquare": "∎",
         r"\exp": "exp", r"\sum_k": "Σ_k", r"\sum": "Σ",
         r"\Big[": "[", r"\Big]": "]", r"\big[": "[", r"\big]": "]",
         r"\mu": "μ", r"\theta": "θ", r"\lambda": "λ",
         r"\delta": "δ", r"\tau": "τ", r"\iota": "ι", r"\rho": "ρ",
         r"\underline{\alpha}": "α\u0331", r"\bar{\alpha}": "ᾱ"}

# Currency in the source is written escaped (\\$900 billion), so every unescaped dollar
# is a math delimiter. Deciding which is which from a span's contents is what put
# "$A + G$" and "$N = 12$" into the v0.7 PDF as literal text: any rule narrow enough to
# protect currency also rejected real math. The ambiguity is removed at the source.
CURRENCY = "\uE000"   # private-use placeholder, restored to a literal $ at the end


def inline(t):
    t = t.replace("\\$", CURRENCY)
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", t)
    t = re.sub(r"`(.+?)`", r"<font face='Courier' size=9>\1</font>", t)

    def render(s):
        for k, v in GREEK.items():
            s = s.replace(k, v)
        s = re.sub(r"\\t?frac\{(.+?)\}\{(.+?)\}", r"(\1)/(\2)", s)
        s = re.sub(r"\\(?:bar|underline|overline|mathrm|text)\{(.+?)\}", r"\1", s)
        s = re.sub(r"\\[a-zA-Z]+", "", s)
        s = s.replace("{", "").replace("}", "")
        return "<i>%s</i>" % s.strip()

    t = re.sub(r"\$\$(.+?)\$\$", lambda m: render(m.group(1)), t, flags=re.S)

    out, i = [], 0
    while True:
        j = t.find("$", i)
        if j < 0:
            out.append(t[i:]); break
        k = t.find("$", j + 1)
        if k < 0:
            # unbalanced delimiter: leave the rest untouched rather than eat text
            out.append(t[i:]); break
        out.append(t[i:j]); out.append(render(t[j + 1:k])); i = k + 1
    return "".join(out).replace(CURRENCY, "$")


def build_table(rows):
    header, data = rows[0], rows[1:]
    tbl = [[Paragraph(inline(c), cellb) for c in header]] + \
          [[Paragraph(inline(c), cell) for c in r] for r in data]
    ncol = len(header)
    avail = 6.5 * inch
    w = [avail * 0.30] + [(avail * 0.70) / (ncol - 1)] * (ncol - 1) if ncol > 3 else [avail / ncol] * ncol
    t = Table(tbl, colWidths=w, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.8, colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 0.8, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f6f6")]),
    ]))
    return t

def parse(md):
    flow = []
    lines = md.split("\n")
    i = 0
    para = []
    tbl = []

    def flush_para():
        nonlocal para
        if para:
            flow.append(Paragraph(inline(" ".join(para)), body))
            para = []

    def flush_tbl():
        nonlocal tbl
        if tbl:
            flow.append(Spacer(1, 4))
            flow.append(build_table(tbl))
            flow.append(Spacer(1, 8))
            tbl = []

    while i < len(lines):
        ln = lines[i].rstrip()
        if ln.startswith("|"):
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if not all(set(c) <= set("-: ") for c in cells):
                tbl.append(cells)
            i += 1
            continue
        flush_tbl()
        if ln.startswith("# "):
            flush_para(); flow.append(Paragraph(inline(ln[2:]), title))
        elif ln.startswith("## "):
            flush_para(); flow.append(Paragraph(inline(ln[3:]), h1))
        elif ln.startswith("### "):
            flush_para(); flow.append(Paragraph(inline(ln[4:]), h2))
        elif ln.startswith("**Sudhir Vissa**"):
            flush_para(); flow.append(Paragraph(inline(ln), authors))
        elif ln.startswith("*Draft v0."):
            flush_para(); flow.append(Paragraph(inline(ln.strip("*")), small))
        elif ln.startswith("---"):
            flush_para()
        elif re.match(r"^\d+\. ", ln) or ln.startswith("- "):
            flush_para()
            txt = re.sub(r"^(\d+)\. ", "\\1.\u00a0\u00a0", ln)
            txt = re.sub(r"^- ", "\u2022\u00a0\u00a0", txt)
            flow.append(Paragraph(inline(txt), ParagraphStyle(
                "li", parent=body, leftIndent=14, firstLineIndent=-10, spaceAfter=3)))
        elif ln == "":
            flush_para()
        else:
            para.append(ln)
        i += 1
    flush_para(); flush_tbl()
    return flow

def page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Times-Italic", 8.5)
    canvas.setFillColor(colors.HexColor("#555555"))
    if doc.page > 1:
        canvas.drawString(1 * inch, LETTER[1] - 0.62 * inch, RUNNING)
        canvas.setStrokeColor(colors.HexColor("#cccccc"))
        canvas.line(1 * inch, LETTER[1] - 0.70 * inch, LETTER[0] - 1 * inch, LETTER[1] - 0.70 * inch)
    canvas.setFont("Times-Roman", 9)
    canvas.drawCentredString(LETTER[0] / 2, 0.6 * inch, str(doc.page))
    canvas.restoreState()

md = open(SRC).read()
flow = parse(md)

# insert the figure right after the Results heading paragraph block
fig = Image(FIG, width=6.5 * inch, height=6.5 * inch * 7.5 / 16)
figblock = [Spacer(1, 6), fig,
            Paragraph("Figure 1. Simulated market outcomes against twin-buyer share \u03b1, "
                      "for robust (\u03b3 = 0) and manipulable (\u03b3 = 1.5) twins; 20 seeds, smoothed best "
                      "response, mean \u00b1 sd. Panels: gross margin, advertising spend, agent-directed "
                      "spend, total persuasion spend, consumer net value per unit, sales share of top-3 "
                      "true-value sellers, concentration (HHI), price dispersion.", cap)]
fig2 = Image("figures/fig_phase.png", width=6.5 * inch, height=6.5 * inch * 4.1 / 17)
fig2block = [Spacer(1, 6), fig2,
             Paragraph("Figure 2. Outcomes across the persuadability \u00d7 adoption plane: gross margin, "
                       "total persuasion spend, concentration and consumer net value per unit, for "
                       "\u03b3 from 0 to 3 against twin share \u03b1 (4 seeds per cell). White contours are "
                       "iso-outcome lines.", cap)]
for idx, f in enumerate(flow):
    if isinstance(f, Paragraph) and f.style.name == "h2" and "7.4 The persuadability" in f.text:
        flow[idx + 2:idx + 2] = fig2block
        break

for idx, f in enumerate(flow):
    if isinstance(f, Paragraph) and f.style.name == "h1" and "7. Results" in f.text:
        # place after the intro paragraph following the heading
        flow[idx + 2:idx + 2] = figblock
        break

doc = BaseDocTemplate(OUT, pagesize=LETTER, leftMargin=1 * inch, rightMargin=1 * inch,
                      topMargin=0.85 * inch, bottomMargin=0.85 * inch,
                      title="After Attention: The Economics of Markets Where the Buyer Is an Agent",
                      author="Sudhir Vissa; Venkata M. Sangaraju")
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=page)])
doc.build(flow)
print("wrote", OUT)
