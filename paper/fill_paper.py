# -*- coding: utf-8 -*-
"""
fill_paper.py — پر کردن دو قالب Word کنفرانس علم داده با محتوای IBDiff
متن placeholderهای قالب با محتوای ما جایگزین می‌شود ولی استایل‌ها/فرمت قالب دست‌نخورده می‌مانند.

Usage:
    python fill_paper.py            # هر دو نسخه (فارسی + انگلیسی)
    python fill_paper.py --fa       # فقط فارسی
    python fill_paper.py --en       # فقط انگلیسی
"""

import argparse
import copy
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import qn

BASE = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE.parent / "templete"
OUT_DIR = BASE / "output"

FA_TEMPLATE = TEMPLATE_DIR / "فرم-نگارش-مقاله-فارسی-سومین_کنفرانس_علم_داده.docx"
EN_TEMPLATE = TEMPLATE_DIR / "فرم-نگارش-مقاله-انگلیسی-سومین_کنفرانس_علم_داده.docx"
FA_CONTENT = BASE / "content-fa.md"
EN_CONTENT = BASE / "content-en.md"

# ---------------------------------------------------------------- OMML equations

MNS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _R(t):
    """math run"""
    return f'<m:r><m:t xml:space="preserve">{escape(t)}</m:t></m:r>'


def _SS(base, sub):
    """subscript: base with sub"""
    return f'<m:sSub><m:e>{base}</m:e><m:sub>{_R(sub)}</m:sub></m:sSub>'


def _SSU(base, sub, sup):
    """sub-superscript: base with sub and sup"""
    return (f'<m:sSubSup><m:e>{base}</m:e>'
            f'<m:sub>{_R(sub)}</m:sub><m:sup>{_R(sup)}</m:sup></m:sSubSup>')


def _F(num, den):
    """fraction"""
    return f'<m:f><m:num>{num}</m:num><m:den>{den}</m:den></m:f>'


def _D(inner):
    """delimiters (round parens)"""
    return f'<m:d><m:e>{inner}</m:e></m:d>'


def _ACC(ch, mark="\u0302"):
    """accented symbol (hat/tilde)"""
    return (f'<m:acc><m:accPr><m:chr m:val="{mark}"/></m:accPr>'
            f'<m:e>{_R(ch)}</m:e></m:acc>')


def _Z(ts, s=None, c=None):
    """z_T^s / z_T^c / z_T^* helper"""
    sup = s if s is not None else c
    return _SSU(_R("z"), ts, sup)


def _eq1():
    z = _SSU(_R("z"), "T", "*")
    num = _R("σ") + _D(_Z("T", s="s")) + _R("·") + _D(
        _Z("T", c="c") + _R("-μ") + _D(_Z("T", c="c")))
    den = _R("σ") + _D(_Z("T", c="c"))
    return (z + _R("=") + _F(num, den) + _R("+") + _R("μ")
            + _D(_Z("T", s="s")) + _R(",  ") + _Z("T", s="s")
            + _R("~N(0,I)"))


def _eq2():
    return (_ACC("L") + _R("=") + _SS(_R("blur"), "5×5")
            + _D(_SS(_R("max"), "c") + _R(" ") + _SS(_R("I"), "c")))


def _eq3():
    left = _SS(_R("G"), "dark") + _R("=") + _R("σ") + _D(
        _F(_D(_SS(_R("τ"), "low") + _R("-") + _ACC("L")), _R("s")))
    right = _SS(_R("G"), "bright") + _R("=") + _R("σ") + _D(
        _F(_D(_ACC("L") + _R("-") + _SS(_R("τ"), "high")), _R("s")))
    return left + _R(",  ") + right


def _eq4():
    zh = lambda: _SS(_ACC("z"), "0,t")
    return (_SS(_ACC("ε", "\u0303"), "t") + _R("=") + _SS(_R("ε"), "θ")
            + _D(_SS(_R("z"), "t") + _R(",t"))
            + _R("+") + _SS(_R("λ"), "d") + _R("(t)·") + _SS(_R("G"), "dark")
            + _R("⊙") + _D(_SS(_R("μ"), "E") + _R("-") + _SS(_R("μ"), "local")
                           + _D(zh()))
            + _R("-") + _SS(_R("λ"), "b") + _R("(t)·") + _SS(_R("G"), "bright")
            + _R("⊙") + _R("max") + _D(
                _SS(_R("μ"), "local") + _D(zh()) + _R("-")
                + _SS(_R("μ"), "E") + _R(",0")))


def _eq5():
    return (_SS(_R("I"), "out") + _R("=") + _R("VAE.Dec")
            + _D(_R("IDWT")
                 + _D(_SS(_ACC("z"), "0") + _R(", ") + _SS(_R("H"), "L"))))


EQS = {1: _eq1, 2: _eq2, 3: _eq3, 4: _eq4, 5: _eq5}


def _omath(inner):
    return f'<m:oMath xmlns:m="{MNS}" xmlns:w="{WNS}">{inner}</m:oMath>'


def add_equation_para(doc, eq_num, num_label, body_style):
    """پاراگراف معادله: tab وسط + oMath + tab + (شماره) — شماره راست‌چین"""
    p = doc.add_paragraph(style=body_style)
    sec = doc.sections[0]
    usable = int(sec.page_width - sec.left_margin - sec.right_margin)
    ts = p.paragraph_format.tab_stops
    ts.add_tab_stop(usable // 2, WD_TAB_ALIGNMENT.CENTER)
    ts.add_tab_stop(usable, WD_TAB_ALIGNMENT.RIGHT)
    p.add_run("\t")
    p._p.append(parse_xml(_omath(EQS[eq_num]())))
    p.add_run("\t(" + num_label + ")")
    return p

# ---------------------------------------------------------------- content parsing

def parse_content(md_path: Path):
    """متن مارک‌داون را به فیلدهای براکت‌دار + سکشن‌های ## تجزیه می‌کند.
    فیلدهای براکت‌دار فقط پیش از اولین سرفصل ## شناسایی می‌شوند؛
    بعد از آن همه خطوط (ازجمله [1] مراجع و [شکل ۱]) بدنه سکشن می‌مانند."""
    fields = {}       # key -> list of lines
    sections = []     # [{title, lines}]
    current_field = None
    current_section = None

    for raw in md_path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            current_field = None
            current_section = {"title": line[3:].strip(), "lines": []}
            sections.append(current_section)
            continue
        m = re.match(r"^\[([^\[\]]+)\]\s*(.*)$", line.strip())
        if m and current_section is None and not m.group(1).strip()[:1].isdigit():
            current_field = m.group(1).strip().upper()
            fields[current_field] = ([m.group(2).strip()] if m.group(2).strip() else [])
            continue
        if current_field is not None and current_section is None:
            if line.strip():
                fields[current_field].append(line.strip())
        elif current_section is not None:
            if line.strip():
                current_section["lines"].append(line.strip())
    return fields, sections


# ---------------------------------------------------------------- docx helpers

def set_para_text(para, text):
    """متن پاراگراف را با حفظ فرمت اولین run جایگزین می‌کند."""
    runs = para.runs
    if runs:
        runs[0].text = text
        for r in runs[1:]:
            r._element.getparent().remove(r._element)
    else:
        para.add_run(text)


def clear_para(para):
    set_para_text(para, "")


def delete_para(para):
    para._element.getparent().remove(para._element)


def set_ltr(p):
    """پاراگراف را صریحاً LTR می‌کند (قالب انگلیسی، استایل Normal آن RTL است)."""
    pPr = p._p.get_or_add_pPr()
    old = pPr.find(qn("w:bidi"))
    if old is not None:
        pPr.remove(old)
    bidi = parse_xml(f'<w:bidi xmlns:w="{WNS}" w:val="0"/>')
    pPr.insert_element_before(
        bidi, "w:spacing", "w:ind", "w:jc", "w:rPr", "w:sectPr")


def strip_shapes(doc):
    """حذف عناصر آموزشی باقی‌مانده قالب: text box / شکل / عکس / جدول نمونه
    (باقی‌مانده‌ها که doc.paragraphs نمی‌بیند، مثل معادله نمونه قالب داخل جدول)."""
    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
    body = doc.element.body
    targets = []
    for el in body.iter():
        tag = el.tag
        if tag in (f"{{{W}}}drawing", f"{{{W}}}pict", f"{{{W}}}tbl",
                   f"{{{MC}}}AlternateContent", f"{{{W}}}object"):
            targets.append(el)
    for el in targets:
        parent = el.getparent()
        if parent is not None:
            parent.remove(el)


# ---------------------------------------------------------------- FA template

def fill_fa(fields, sections):
    doc = Document(str(FA_TEMPLATE))
    ps = doc.paragraphs

    # عنوان فارسی + انگلیسی
    set_para_text(ps[0], fields["عنوان-فارسی"][0])
    set_para_text(ps[10], fields["عنوان-انگلیسی"][0])

    # نویسندگان فارسی (ps[1] نویسندگان، ps[2..3] وابستگی‌ها، ps[4..5] خالی)
    fa_authors = fields["نویسندگان-فارسی"]
    set_para_text(ps[1], fa_authors[0])
    set_para_text(ps[2], fa_authors[1] if len(fa_authors) > 1 else "")
    set_para_text(ps[3], fa_authors[2] if len(fa_authors) > 2 else "")
    clear_para(ps[4])
    clear_para(ps[5])

    # چکیده فارسی (ps[7..8]) و کلیدواژه فارسی (ps[9])
    set_para_text(ps[7], " ".join(fields["چکیده-فارسی"]))
    clear_para(ps[8])
    set_para_text(ps[9], "کلیدواژه‌ها: " + fields["کلیدواژه-فارسی"][0])

    # نویسندگان انگلیسی (ps[11..15])
    en_authors = fields["نویسندگان-انگلیسی"]
    set_para_text(ps[11], en_authors[0])
    set_para_text(ps[12], en_authors[1] if len(en_authors) > 1 else "")
    set_para_text(ps[13], en_authors[2] if len(en_authors) > 2 else "")
    clear_para(ps[14])
    clear_para(ps[15])

    # چکیده انگلیسی (ps[17]) و کلیدواژه انگلیسی (ps[18])
    set_para_text(ps[17], " ".join(fields["ABSTRACT-EN"]))
    set_para_text(ps[18], "Keywords: " + fields["KEYWORDS-EN"][0])

    # حذف بدنه آموزشی قالب از پاراگراف 19 به بعد
    for p in list(ps[19:]):
        delete_para(p)
    strip_shapes(doc)

    # افزودن سکشن‌های مقاله با استایل قالب
    for sec in sections:
        doc.add_paragraph(sec["title"], style="Heading 1")
        for line in sec["lines"]:
            add_md_body(doc, line, "fa")

    return doc


# ---------------------------------------------------------------- EN template

def _add_en_heading(doc, text):
    p = doc.add_paragraph(text, style="List Paragraph")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_ltr(p)
    for r in p.runs:
        r.font.size = Pt(10)
        r.font.bold = True
    return p


def _add_en_body(doc, text):
    p = doc.add_paragraph(text, style="Normal")
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for r in p.runs:
        r.font.size = Pt(10)
    return p


def fill_en(fields, sections):
    doc = Document(str(EN_TEMPLATE))
    ps = doc.paragraphs

    set_para_text(ps[0], fields["PAPER-TITLE"][0])
    clear_para(ps[1])

    author_lines = fields["AUTHORS"]
    set_para_text(ps[2], author_lines[0])
    set_para_text(ps[3], author_lines[1] if len(author_lines) > 1 else "")
    clear_para(ps[4])

    # چکیده: run اول «Abstract—» پررنگ می‌ماند
    p6 = ps[6]
    runs = p6.runs
    if runs:
        runs[0].text = "Abstract—"
        if len(runs) > 1:
            runs[1].text = " ".join(fields["ABSTRACT"])
            for r in runs[2:]:
                r._element.getparent().remove(r._element)
    set_para_text(ps[7], "Keywords—" + fields["KEYWORDS"][0])

    # حذف بدنه آموزشی از پاراگراف 8 به بعد
    for p in list(ps[8:]):
        delete_para(p)
    strip_shapes(doc)

    for sec in sections:
        _add_en_heading(doc, sec["title"])
        for line in sec["lines"]:
            add_md_body(doc, line, "en")

    return doc


# ---------------------------------------------------------------- md body renderer

def _strip_bullet(line):
    if line.startswith("- "):
        return line[2:].strip()
    if line.startswith("* "):
        return line[2:].strip()
    return line


def add_md_body(doc, line, lang):
    """یک خط مارک‌داون بدنه را به پاراگراف تبدیل می‌کند:
    - '### ' → سرفصل سطح ۲ (فارسی: Heading 2 / انگلیسی: List Paragraph بولد چپ‌چین)
    - 'EQ: ...' → پاراگراف فرمول خطی (تبدیل به معادله واقعی Word در fix_equations.ps1)
    - '**بولد**' → runهای بولد
    - باقی متن → پاراگراف بدنه با استایل قالب"""
    text = _strip_bullet(line).strip()

    if text.startswith("### "):
        title = text[4:].strip()
        if lang == "fa":
            doc.add_paragraph(title, style="Heading 2")
        else:
            p = doc.add_paragraph(title, style="List Paragraph")
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for r in p.runs:
                r.font.size = Pt(10)
                r.font.bold = True
        return

    if text.startswith("EQ:"):
        # 'EQ: ... #(۱)' → معادله واقعی OMML با شماره راست‌چین
        m = re.search(r"#\(([0-9۰-۹]+)\)\s*$", text)
        if not m:
            raise ValueError(f"bad EQ line (missing #(n)): {text[:60]}")
        digits = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
        n = int(m.group(1).translate(digits))
        if n not in EQS:
            raise ValueError(f"unknown equation number {n}")
        num_label = m.group(1) if lang == "fa" else str(n)
        p = add_equation_para(doc, n, num_label, "BodyText-fa" if lang == "fa" else "Normal")
        if lang == "en":
            set_ltr(p)
        return

    if lang == "fa":
        p = doc.add_paragraph(style="BodyText-fa")
    else:
        p = doc.add_paragraph(style="Normal")
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    parts = text.split("**")
    for i, part in enumerate(parts):
        if not part:
            continue
        run = p.add_run(part)
        if i % 2 == 1:
            run.bold = True
    if lang == "en":
        for r in p.runs:
            r.font.size = Pt(10)
        set_ltr(p)
    return p


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fa", action="store_true")
    ap.add_argument("--en", action="store_true")
    args = ap.parse_args()

    langs = []
    if args.fa:
        langs.append("fa")
    if args.en:
        langs.append("en")
    if not langs:
        langs = ["fa", "en"]

    for lang in langs:
        tpl = FA_TEMPLATE if lang == "fa" else EN_TEMPLATE
        if not tpl.exists():
            print(f"[ERROR] template not found: {tpl}")
            sys.exit(1)
        content = FA_CONTENT if lang == "fa" else EN_CONTENT
        fields, sections = parse_content(content)

        if lang == "fa":
            doc = fill_fa(fields, sections)
        else:
            doc = fill_en(fields, sections)

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out = OUT_DIR / ("IBDiff-Paper-FA.docx" if lang == "fa" else "IBDiff-Paper-EN.docx")
        doc.save(str(out))
        n_sections = len(sections)
        print(f"[OK] {lang.upper()} -> {out}  ({n_sections} sections)")


if __name__ == "__main__":
    main()
