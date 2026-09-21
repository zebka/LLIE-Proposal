# -*- coding: utf-8 -*-
"""Build a self-contained RTL web page (HTML) from the same md sources.

Fixes the mixed Persian/Latin direction problem at its root:
  <html dir="rtl">  +  <bdi> isolation for every Latin run  +  dir="ltr" cells.
Everything (fonts, figures) is embedded — one portable .html file.

Run:  python scripts/build_html.py   ->  output/proposal.html
"""
import base64
import html
import io
import re
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from fill_form import (parse_bib, ieee_ref, clean_md, build_cite_map,
                       apply_cites, map_cites, TABLES as _TABLES,
                       TIMELINE_ROWS, COMPARISON_ROWS, MILESTONE, PROJ, SRC)

ASSETS = PROJ / "assets" / "fonts"
FIGS = PROJ / "figures"
OUTPUT = PROJ / "output"
OUT = OUTPUT / "proposal.html"

FA_TITLE = ("ارائه یک روش بهبود تصویر کم‌نور مبتنی بر پیشین (Prior) مدل‌های انتشار (Diffusion) "
            "برای شرایط نوری نامتوازن گرگ‌ومیش با کاربرد در بینایی ماشین")
EN_TITLE = ("A Diffusion-Prior Zero-Shot Method for Low-Light Image Enhancement under "
            "Imbalanced Twilight Conditions with Application to Machine Vision")
FA_KEYS = "بهبود تصویر کم‌نور، مدل‌های انتشار، یادگیری بدون نظارت، گرگ‌ومیش، بینایی ماشین"
EN_KEYS = "Low-Light Image Enhancement, Diffusion Models, Zero-Shot Learning, Twilight, Machine Vision"

TABLES = dict(_TABLES)
TABLES["5"] = TIMELINE_ROWS
TABLES["COMP"] = COMPARISON_ROWS

SEC_TITLES = [
    ("۱", "شرح مسئله (اهداف، سابقه و ضرورت تحقیق)"),
    ("۲", "سوالات تحقیق/فرضیه‌ها"),
    ("۳", "کاربردهای تحقیق و استفاده‌کنندگان از نتایج رساله"),
    ("۴", "روش شناسی (روش و ابزار جمع‌آوری، انجام و تحلیل اطلاعات تحقیق)"),
    ("۵", "جنبه نوآوری تحقیق"),
    ("۶", "جدول زمان‌بندی انجام پروژه"),
]

FIG_FILES = {n: f"شکل-{n:02d}.png" for n in range(1, 15)}
FIG_FILES[15] = ["شکل-16a.png", "شکل-16b.png", "شکل-16c.png"]
FIG_FILES[16] = None  # phase-3 photos

PD = "۰۱۲۳۴۵۶۷۸۹"
fa2en = lambda s: int(s.translate(str.maketrans(PD, "0123456789")))  # noqa: E731

FIG_RE = re.compile(r"^شکل ([۰-۹]+):")
TABLE_CAP_RE = re.compile(r"^جدول ([۰-۹]+):")
PERSIAN_RE = re.compile(r"[آ-یءئۀأإؤ]")
LATIN_RUN = re.compile(r"(?<![&\w])([A-Za-z][A-Za-z0-9\-\./#@+%()]*)")
# citation numbers produced by fill_form.map_cites are Latin digits joined by ", "
CITE_RE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")

_fig_cache = {}


def esc(s):
    return html.escape(s, quote=False)


def bdi(s):
    """escape + isolate every Latin run so RTL punctuation never scrambles."""
    return LATIN_RUN.sub(lambda m: "<bdi>" + m.group(1) + "</bdi>", esc(s))


def link_cites(s):
    def repl(m):
        nums = [x.strip() for x in m.group(1).split(",")]
        inner = "، ".join(f'<a href="#ref-{n}">{n}</a>' for n in nums)
        return f'<span class="cite">[{inner}]</span>'
    return CITE_RE.sub(repl, s)


def para(s, cls=""):
    c = f' class="{cls}"' if cls else ""
    return f"<p{c}>{link_cites(bdi(s))}</p>"


def cell(s):
    e = esc(s)
    if not PERSIAN_RE.search(s):
        return f'<span dir="ltr">{e}</span>'
    return LATIN_RUN.sub(lambda m: "<bdi>" + m.group(1) + "</bdi>", e)


def data_uri(fname, maxw=1400):
    if fname in _fig_cache:
        return _fig_cache[fname]
    im = Image.open(FIGS / fname)
    if im.mode != "RGB":
        im = im.convert("RGB")
    if im.width > maxw:
        im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82, optimize=True)
    uri = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    _fig_cache[fname] = uri
    return uri


def font_face():
    out = []
    for fname, weight in [("Vazirmatn-Regular.ttf", 400),
                          ("Vazirmatn-Medium.ttf", 500),
                          ("Vazirmatn-Bold.ttf", 700)]:
        b64 = base64.b64encode((ASSETS / fname).read_bytes()).decode()
        out.append(f"@font-face{{font-family:'Vazirmatn';font-style:normal;"
                   f"font-weight:{weight};font-display:swap;"
                   f"src:url(data:font/ttf;base64,{b64}) format('truetype');}}")
    return "\n".join(out)


CSS = """
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{font-family:'Vazirmatn','Segoe UI',Tahoma,sans-serif;font-size:17px;line-height:1.95;
     color:#1a1a1a;background:#fff;max-width:920px;margin:0 auto;padding:2.2rem 1.4rem 4rem;
     text-align:start}
h1{font-size:1.75rem;line-height:1.6;margin:.2rem 0 .6rem}
h2{font-size:1.3rem;line-height:1.6;margin:2.6rem 0 .9rem;padding-bottom:.35rem;
   border-bottom:1px solid #dcdcdc}
h3{font-size:1.06rem;line-height:1.7;margin:1.8rem 0 .5rem}
p{margin:.55rem 0;text-align:justify}
.cover{text-align:center;border-bottom:1px solid #dcdcdc;padding-bottom:1.4rem;margin-bottom:1.4rem}
.cover .doctype{color:#666;font-size:.9rem;letter-spacing:0}
.cover .en{font-size:.86rem;color:#555;direction:ltr;text-align:center}
.keywords{font-size:.9rem;color:#444;text-align:center}
.keywords.en{direction:ltr}
nav.toc{background:#f7f7f7;border:1px solid #e6e6e6;border-radius:10px;padding:.8rem 1.1rem;
        font-size:.95rem}
nav.toc ol{margin:.3rem 0;padding-inline-start:1.5rem}
nav.toc a{color:#1a1a1a;text-decoration:none}
nav.toc a:hover{text-decoration:underline}
table{width:100%;border-collapse:collapse;font-size:.85rem;margin:1rem 0}
th,td{border:1px solid #cfcfcf;padding:.4rem .5rem;text-align:center;vertical-align:middle}
th{background:#f2f2f2;font-weight:700}
.figure{margin:1.6rem 0;text-align:center}
.figure img{max-width:100%;height:auto;border:1px solid #e2e2e2;border-radius:6px}
.figure figcaption{font-size:.84rem;color:#555;margin-top:.5rem;line-height:1.8}
.placeholder{border:1px dashed #bbb;border-radius:8px;padding:1.6rem 1rem;color:#777;font-size:.9rem}
.table-caption{font-size:.9rem;font-weight:700;margin-top:1.3rem;text-align:start}
.milestone{background:#f7f7f7;border:1px solid #e6e6e6;border-radius:8px;padding:.6rem .8rem;
           font-size:.92rem}
.refs{list-style:none;margin:0;padding:0}
.refs li{direction:ltr;text-align:left;font-size:.83rem;line-height:1.75;margin-bottom:.5rem;
         padding-inline-start:2.6rem;text-indent:-2.6rem}
.refs li a{color:#1a1a1a;text-decoration:none}
.cite{white-space:nowrap}
footer{margin-top:3rem;padding-top:1rem;border-top:1px solid #dcdcdc;color:#777;font-size:.8rem;
       text-align:center}
@media (max-width:640px){body{font-size:16px;padding:1.1rem .8rem 2.5rem}
  table{font-size:.76rem}h1{font-size:1.4rem}}
"""


def render_figure(num, caption):
    inner = ""
    if num == 16:
        inner = ('<div class="placeholder">جای تصاویر گرگ‌ومیش ضبط‌شده در فاز ۳ '
                 '(<bdi>TwilightDrive</bdi>)</div>')
    else:
        files = FIG_FILES.get(num)
        if files:
            files = files if isinstance(files, list) else [files]
            for f in files:
                inner += f'<img src="{data_uri(f)}" alt="{esc(caption)}" loading="lazy">'
    return (f'<figure class="figure" id="fig-{num}">{inner}'
            f'<figcaption>{link_cites(bdi(caption))}</figcaption></figure>')


def render_table(rows):
    head = "".join(f"<th>{cell(c)}</th>" for c in rows[0])
    body = "".join("<tr>" + "".join(f"<td>{cell(c)}</td>" for c in row) + "</tr>"
                   for row in rows[1:])
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def main():
    entries = parse_bib(PROJ / "references.bib")
    sec1 = clean_md((SRC / "section1-draft.md").read_text(encoding="utf-8").split("## ۱-۱.", 1)[1].join(["## ۱-۱.", ""]))
    all_md = (SRC / "sections-2-3-4-draft.md").read_text(encoding="utf-8")
    p2 = all_md.split("# (۲)", 1)[1]
    sec2 = clean_md(p2.split("# (۳)", 1)[0])
    sec3 = clean_md(p2.split("# (۳)", 1)[1].split("# (۴)", 1)[0])
    sec4 = clean_md(p2.split("# (۴)", 1)[1])
    md56 = (SRC / "sections-5-6-draft.md").read_text(encoding="utf-8")
    sec5 = clean_md(md56.split("# (۵)", 1)[1].split("# (۶)", 1)[0])
    sec6 = [("h", "برنامه زمان‌بندی"),
            ("p", "زمان‌بندی اجرایی پروژه در قالب پنج فاز طی ۲۴ ماه مطابق جدول زیر است."),
            ("p", "جدول ۵: برنامه زمان‌بندی پنج‌فازی اجرای پروژه (تألیف پژوهش حاضر)"),
            ("table", "5"),
            ("p", MILESTONE)]

    sections = [sec1, sec2, sec3, sec4, sec5, sec6]
    order = build_cite_map(sections, entries)
    sections = [apply_cites(s, order) for s in sections]
    for rows in TABLES.values():
        for i, row in enumerate(rows):
            rows[i] = [map_cites(v, order) for v in row]

    P = []
    P.append("<!DOCTYPE html>")
    P.append('<html dir="rtl" lang="fa">')
    P.append("<head>")
    P.append('<meta charset="utf-8">')
    P.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    P.append(f"<title>{esc(FA_TITLE)}</title>")
    P.append(f"<style>\n{font_face()}\n{CSS}</style>")
    P.append("</head><body>")

    P.append('<header class="cover">')
    P.append('<p class="doctype">طرح پیشنهادی رسالهٔ دکتری</p>')
    P.append(f"<h1>{bdi(FA_TITLE)}</h1>")
    P.append(f'<p class="en">{esc(EN_TITLE)}</p>')
    P.append(f'<p class="keywords"><strong>کلیدواژه‌ها:</strong> {bdi(FA_KEYS)}</p>')
    P.append(f'<p class="keywords en"><strong>Keywords:</strong> {esc(EN_KEYS)}</p>')
    P.append("</header>")

    P.append('<nav class="toc"><strong>فهرست</strong><ol>')
    for num, title in SEC_TITLES:
        P.append(f'<li><a href="#sec-{num}">{bdi(title)}</a></li>')
    P.append('<li><a href="#sec-7">مراجع</a></li>')
    P.append("</ol></nav>")

    P.append("<main>")
    for (num, title), items in zip(SEC_TITLES, sections):
        P.append(f'<section id="sec-{num}"><h2>{num}) {bdi(title)}</h2>')
        for kind, txt in items:
            if kind == "sp":
                continue
            if kind == "table":
                P.append(render_table(TABLES[txt]))
                continue
            m = FIG_RE.match(txt)
            if m and kind == "p":
                P.append(render_figure(fa2en(m.group(1)), txt))
                continue
            if kind == "h":
                P.append(f"<h3>{bdi(txt)}</h3>")
                continue
            cls = "milestone" if txt.startswith("نقاط کنترل") else (
                "table-caption" if TABLE_CAP_RE.match(txt) else "")
            P.append(para(txt, cls))
        P.append("</section>")

    P.append('<section id="sec-7"><h2>۷) مراجع</h2><ol class="refs">')
    for key, num in sorted(order.items(), key=lambda kv: kv[1]):
        P.append(f'<li id="ref-{num}"><a href="#ref-{num}">[{num}]</a> '
                 f"{esc(ieee_ref(key, entries))}</li>")
    P.append("</ol></section></main>")

    P.append(f'<footer>تولید‌شده به‌صورت خودکار از فایل‌های <bdi>src/*.md</bdi> — '
             f'{len(order)} مرجع</footer>')
    P.append("</body></html>")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(P), encoding="utf-8")
    return order


if __name__ == "__main__":
    order = main()
    mb = OUT.stat().st_size / 1024 / 1024
    print(f"OK — Web: {OUT}")
    print(f"     {mb:.1f} MB, {len(order)} refs, figures embedded")
