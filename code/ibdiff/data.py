# -*- coding: utf-8 -*-
"""Dataset helpers: image listing, load/resize, paired matching."""
from pathlib import Path
from typing import List, Tuple

from PIL import Image

IMG_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


def list_images(d: Path, recursive: bool = True) -> List[Path]:
    d = Path(d)
    if d.is_file():
        return [d]
    pat = "**/*" if recursive else "*"
    return sorted(p for p in d.glob(pat)
                  if p.is_file() and p.suffix.lower() in IMG_EXTS)


def load_rgb(p: Path, size: int = 512, square: bool = True) -> Image.Image:
    im = Image.open(p).convert("RGB")
    if square:
        return im.resize((size, size), Image.BICUBIC)
    w, h = im.size
    s = size / min(w, h)
    nw, nh = int(round(w * s / 8) * 8), int(round(h * s / 8) * 8)
    return im.resize((nw, nh), Image.BICUBIC)


def match_paired(low_dir: Path, high_dir: Path) -> List[Tuple[Path, Path]]:
    lows = {p.stem: p for p in list_images(low_dir)}
    highs = {p.stem: p for p in list_images(high_dir)}
    common = sorted(set(lows) & set(highs))
    return [(lows[k], highs[k]) for k in common]
