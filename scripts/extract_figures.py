# -*- coding: utf-8 -*-
"""Extract proposal figures from arXiv PDFs at high DPI.

For each (arxiv_id, kind, num, name):
  1. download+cache the PDF
  2. locate the caption block ("Figure N" / "Table N")
  3. auto-crop the figure/table region and render at 600 DPI -> شکل-XX.png
  4. also render the FULL page at 300 DPI as fallback -> شکل-XX-fullpage.png
Outputs go to Twilight-LLIE-Proposal/figures/
"""
import io
import re
import sys
from pathlib import Path

import pymupdf
import requests

BASE = Path(r"C:\Users\Alireza\Desktop\New folder (2)")
PROJ = BASE / "Twilight-LLIE-Proposal"
OUT = PROJ / "figures"
PDFS = OUT / "pdfs"
OUT.mkdir(exist_ok=True)
PDFS.mkdir(exist_ok=True)

# (arxiv_id, kind, nums-to-try, out_name)
MANIFEST = [
    ("2212.10772", "fig", [1], "01"),
    ("2212.10772", "fig", [2], "02"),
    ("2212.10772", "fig", [3], "03"),
    ("1808.04560", "fig", [1], "04"),
    ("1808.04560", "fig", [3], "05"),
    ("2001.06826", "fig", [2], "06"),
    ("2204.10137", "fig", [1], "07"),
    ("2109.05923", "fig", [2], "08"),
    ("2303.06705", "fig", [2], "09"),
    ("2303.06705", "tab", [1], "10"),
    ("2312.12826", "fig", [1], "11"),
    ("2312.12826", "fig", [2], "12"),
    ("2510.05976", "fig", [2, 3], "13"),
    ("2608.04429", "fig", [1], "14"),
    ("2505.23743", "fig", [2, 1], "15"),
    ("2503.19804", "fig", [1], "16a"),
    ("2410.09831", "fig", [1], "16b"),
    ("2603.18067", "fig", [1], "16c"),
]

CROP_DPI = 600
PAGE_DPI = 300
MARGIN = 40.0


def download_pdf(arxiv_id):
    pdf_path = PDFS / f"{arxiv_id}.pdf"
    if pdf_path.exists() and pdf_path.stat().st_size > 50_000:
        return pdf_path
    url = f"https://arxiv.org/pdf/{arxiv_id}"
    print(f"  downloading {url} ...", flush=True)
    r = requests.get(url, timeout=180, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    pdf_path.write_bytes(r.content)
    return pdf_path


def page_blocks(page):
    d = page.get_text("dict")
    blocks = []
    for b in d["blocks"]:
        if b["type"] != 0:
            continue
        lines = [" ".join(s["text"] for s in l["spans"]).strip() for l in b["lines"]]
        text = " ".join(lines)
        blocks.append({"rect": pymupdf.Rect(b["bbox"]), "text": text, "words": len(text.split()), "lines": lines})
    return blocks


def find_caption(doc, kind, num):
    pat = (re.compile(rf"^(?:Figure|Fig\.)\s*{num}[\.:]")
           if kind == "fig" else re.compile(rf"^Table\s*{num}[\.:]"))
    for pno in range(len(doc)):
        for b in page_blocks(doc[pno]):
            for line in b["lines"]:
                if pat.match(line.strip()):
                    return pno, b["rect"]
    return None, None


def column_bounds(cap_rect, page_rect):
    w = page_rect.width
    if cap_rect.width > 0.5 * w:
        return pymupdf.Rect(MARGIN, 0, w - MARGIN, page_rect.height)
    mid = w / 2
    if (cap_rect.x0 + cap_rect.x1) / 2 < mid:
        return pymupdf.Rect(MARGIN, 0, mid, page_rect.height)
    return pymupdf.Rect(mid, 0, w - MARGIN, page_rect.height)


def h_overlap(r, col):
    inter = min(r.x1, col.x1) - max(r.x0, col.x0)
    return inter > 0.4 * min(r.width, col.width)


def graphic_tops(page, cap_rect, col, window=460.0):
    """topmost y of images/vector drawings forming the figure above the caption"""
    tops = []
    for info in page.get_image_info():
        r = pymupdf.Rect(info["bbox"])
        if r.y1 <= cap_rect.y0 + 2 and h_overlap(r, col) and r.y0 > cap_rect.y0 - window:
            tops.append(r.y0)
    try:
        for dr in page.get_drawings():
            r = pymupdf.Rect(dr["rect"])
            if (r.y1 <= cap_rect.y0 + 2 and h_overlap(r, col)
                    and r.y0 > cap_rect.y0 - window and r.height > 1.5):
                tops.append(r.y0)
    except Exception:
        pass
    return min(tops) if tops else None


def figure_crop(page, blocks, cap_rect, col, page_rect):
    """top = highest of (paragraph above caption, figure graphics cluster)"""
    cands = [b["rect"].y1 for b in blocks
             if b["rect"].y1 < cap_rect.y0 - 3
             and h_overlap(b["rect"], col)
             and b["rect"].width > 0.55 * col.width
             and b["words"] >= 8]
    top = max(cands) + 3 if cands else MARGIN
    g = graphic_tops(page, cap_rect, col)
    if g is not None:
        top = min(top, g)
    top = max(MARGIN, top)
    return pymupdf.Rect(col.x0, top, col.x1, cap_rect.y0 - 2)


def table_crop(blocks, cap_rect, col, page_rect):
    cands = [b["rect"].y0 for b in blocks
             if b["rect"].y0 > cap_rect.y1 + 3
             and h_overlap(b["rect"], col)
             and b["rect"].width > 0.55 * col.width
             and b["words"] >= 8]
    bottom = min(cands) - 3 if cands else page_rect.height - MARGIN
    return pymupdf.Rect(col.x0, cap_rect.y1 + 2, col.x1, bottom)


def render(page, rect, dpi, path):
    pix = page.get_pixmap(matrix=pymupdf.Matrix(dpi / 72, dpi / 72), clip=rect)
    pix.save(str(path))
    return pix.width, pix.height


def main():
    report = []
    for arxiv_id, kind, nums, name in MANIFEST:
        print(f"[{name}] paper {arxiv_id} {'Figure' if kind == 'fig' else 'Table'} {nums}", flush=True)
        try:
            pdf = download_pdf(arxiv_id)
            doc = pymupdf.open(str(pdf))
        except Exception as e:
            report.append(f"{name}\tFAIL\t{arxiv_id}\t{e}")
            continue
        found = False
        for num in nums:
            pno, cap = find_caption(doc, kind, num)
            if pno is None:
                continue
            page = doc[pno]
            blocks = page_blocks(page)
            col = column_bounds(cap, page.rect)
            if kind == "fig":
                crop = figure_crop(page, blocks, cap, col, page.rect)
            else:
                crop = table_crop(blocks, cap, col, page.rect)
            if crop.height < 60 or crop.width < 120:
                report.append(f"{name}\tTHIN-CROP\t{arxiv_id}\tfig{num} p{pno + 1} crop={crop}")
            w, h = render(page, crop, CROP_DPI, OUT / f"شکل-{name}.png")
            render(page, page.rect, PAGE_DPI, OUT / f"شکل-{name}-fullpage.png")
            report.append(f"{name}\tOK\t{arxiv_id}\t{kind}{num} @page{pno + 1} crop {crop.width:.0f}x{crop.height:.0f}pt -> {w}x{h}px")
            found = True
            break
        if not found:
            report.append(f"{name}\tNOT-FOUND\t{arxiv_id}\ttried {nums}")
        doc.close()

    (OUT / "extract-report.txt").write_text("\n".join(report), encoding="utf-8")
    ok = sum(1 for r in report if "\tOK\t" in r)
    print(f"done: {ok}/{len(MANIFEST)} extracted — see figures/extract-report.txt", flush=True)


if __name__ == "__main__":
    main()
