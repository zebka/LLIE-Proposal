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

from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

BASE = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE.parent / "templete"
OUT_DIR = BASE / "output"

FA_TEMPLATE = TEMPLATE_DIR / "فرم-نگارش-مقاله-فارسی-سومین_کنفرانس_علم_داده.docx"
EN_TEMPLATE = TEMPLATE_DIR / "فرم-نگارش-مقاله-انگلیسی-سومین_کنفرانس_علم_داده.docx"
FA_CONTENT = BASE / "content-fa.md"
EN_CONTENT = BASE / "content-en.md"


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

    # افزودن سکشن‌های مقاله با استایل قالب
    for sec in sections:
        doc.add_paragraph(sec["title"], style="Heading 1")
        for line in sec["lines"]:
            t = line.lstrip("-* ").strip() if line.startswith(("- ", "* ")) else line
            doc.add_paragraph(t, style="BodyText-fa")

    return doc


# ---------------------------------------------------------------- EN template

def _add_en_heading(doc, text):
    p = doc.add_paragraph(text, style="List Paragraph")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
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

    for sec in sections:
        _add_en_heading(doc, sec["title"])
        for line in sec["lines"]:
            t = line.lstrip("-* ").strip() if line.startswith(("- ", "* ")) else line
            _add_en_body(doc, t)

    return doc


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
