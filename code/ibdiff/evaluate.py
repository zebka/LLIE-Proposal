# -*- coding: utf-8 -*-
"""Benchmark runner: paired (PSNR/SSIM/LOE/exposure) and unpaired (LOE/exposure).

Paired example (LOL-style: separate low/high folders with matching names):
  python -m ibdiff.evaluate --low data/LOLv2/Test/Low --high data/LOLv2/Test/Normal \
      --out results/lolv2 --csv results/lolv2/metrics.csv

Unpaired example:
  python -m ibdiff.evaluate --unpaired data/ExDark --out results/exdark \
      --csv results/exdark/metrics.csv
"""
import argparse
import csv
import random
from pathlib import Path

import numpy as np
import torch
from tqdm import tqdm

from . import metrics as M
from .data import list_images, load_rgb, match_paired
from .enhance import to_pil, to_tensor
from .pipeline import IBDiffPipeline


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--low", default=None)
    ap.add_argument("--high", default=None)
    ap.add_argument("--unpaired", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--csv", default=None)
    ap.add_argument("--model", default="stabilityai/stable-diffusion-2-1-base")
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--T", type=int, default=25)
    ap.add_argument("--lam-d", type=float, default=1.5)
    ap.add_argument("--lam-b", type=float, default=1.5)
    ap.add_argument("--no-gate", action="store_true")
    ap.add_argument("--no-wavelet", action="store_true")
    ap.add_argument("--fixed-steps", action="store_true")
    ap.add_argument("--with-lpips", action="store_true")
    ap.add_argument("--with-musiq", action="store_true")
    ap.add_argument("--cpu", action="store_true")
    ap.add_argument("--fp32", action="store_true")
    args = ap.parse_args()

    device = "cpu" if args.cpu else ("cuda" if torch.cuda.is_available() else "cpu")
    pipe = IBDiffPipeline(model_id=args.model, device=device,
                          fp16=not args.fp32, T=args.T)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if args.low and args.high:
        pairs = match_paired(Path(args.low), Path(args.high))
        mode = "paired"
    elif args.unpaired:
        pairs = [(p, None) for p in list_images(Path(args.unpaired))]
        mode = "unpaired"
    else:
        raise SystemExit("give --low + --high (paired) or --unpaired")
    print(f"[evaluate] mode={mode} n={len(pairs)}")

    rows = []
    for run in range(args.runs):
        seed = args.seed + run
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        for low_p, high_p in tqdm(pairs, desc=f"run {run}"):
            x = to_tensor(load_rgb(low_p, size=args.size)).unsqueeze(0).to(device)
            y = pipe.enhance(x, lam_d=args.lam_d, lam_b=args.lam_b,
                             use_gate=not args.no_gate,
                             use_wavelet=not args.no_wavelet,
                             adaptive_steps=not args.fixed_steps)
            to_pil(y).save(out / f"{low_p.stem}_r{run}.png")
            y3 = y[0].cpu()
            under, over, meanb = M.exposure_stats(y3)
            row = {"file": low_p.name, "run": run,
                   "under%": round(under, 2), "over%": round(over, 2),
                   "mean": round(meanb, 4),
                   "loe": round(M.loe(x[0].cpu(), y3), 4)}
            if high_p is not None:
                g = to_tensor(load_rgb(high_p, size=args.size))
                row["psnr"] = round(M.psnr(y3, g), 3)
                row["ssim"] = round(M.ssim(y3, g), 4)
            if args.with_lpips and high_p is not None:
                v = M.lpips(y3, g)
                if v is not None:
                    row["lpips"] = round(v, 4)
            if args.with_musiq:
                v = M.pyiqa_score(y3, "musiq")
                if v is not None:
                    row["musiq"] = round(v, 3)
            rows.append(row)

    csv_path = Path(args.csv) if args.csv else out / "metrics.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r in rows for k in r}))
        w.writeheader()
        w.writerows(rows)
    print(f"[evaluate] wrote {csv_path} ({len(rows)} rows)")

    # summary
    keys = [k for k in ("psnr", "ssim", "lpips", "loe", "under%", "over%", "musiq")
            if any(k in r for r in rows)]
    for k in keys:
        vals = [r[k] for r in rows if k in r]
        print(f"  {k}: mean={np.mean(vals):.4f} std={np.std(vals):.4f} (n={len(vals)})")


if __name__ == "__main__":
    main()
