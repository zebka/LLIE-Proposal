# -*- coding: utf-8 -*-
"""CLI: enhance one image or a folder with IBDiff.

Example:
  python -m ibdiff.enhance --input data/ExDark --output out/ibdiff \
      --model Manojb/stable-diffusion-2-1-base --seed 0
"""
import argparse
import random
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from tqdm import tqdm

from .data import list_images, load_rgb
from .pipeline import IBDiffPipeline


def to_tensor(im: Image.Image) -> torch.Tensor:
    return torch.from_numpy(np.asarray(im).copy()).permute(2, 0, 1).float().div(255.0)


def to_pil(t: torch.Tensor) -> Image.Image:
    t = t.detach().clamp(0, 1).cpu()
    if t.dim() == 4:
        t = t[0]
    return Image.fromarray((t.permute(1, 2, 0).numpy() * 255.0).round().astype("uint8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="image file or folder")
    ap.add_argument("--output", required=True, help="output folder")
    ap.add_argument("--model", default="Manojb/stable-diffusion-2-1-base")
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--T", type=int, default=25)
    ap.add_argument("--lam-d", type=float, default=1.5)
    ap.add_argument("--lam-b", type=float, default=1.5)
    ap.add_argument("--tau-low", type=float, default=0.35)
    ap.add_argument("--tau-high", type=float, default=0.65)
    ap.add_argument("--mu-E", type=float, default=0.5)
    ap.add_argument("--alpha", type=float, default=0.6)
    ap.add_argument("--no-gate", action="store_true", help="ablation: drop illumination gate")
    ap.add_argument("--no-wavelet", action="store_true", help="ablation: drop wavelet prior")
    ap.add_argument("--fixed-steps", action="store_true", help="ablation: no adaptive scheduling")
    ap.add_argument("--cpu", action="store_true")
    ap.add_argument("--fp32", action="store_true")
    args = ap.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    device = "cpu" if args.cpu else ("cuda" if torch.cuda.is_available() else "cpu")
    pipe = IBDiffPipeline(model_id=args.model, device=device,
                          fp16=not args.fp32, T=args.T)

    files = list_images(Path(args.input))
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    print(f"[enhance] {len(files)} image(s) -> {out}")

    for f in tqdm(files):
        im = load_rgb(f, size=args.size, square=True)
        x = to_tensor(im).unsqueeze(0).to(device)
        y = pipe.enhance(x, tau_low=args.tau_low, tau_high=args.tau_high,
                         mu_E=getattr(args, "mu_E"), lam_d=args.lam_d,
                         lam_b=args.lam_b, alpha=args.alpha,
                         use_gate=not args.no_gate,
                         use_wavelet=not args.no_wavelet,
                         adaptive_steps=not args.fixed_steps)
        to_pil(y).save(out / (f.stem + ".png"))


if __name__ == "__main__":
    main()
