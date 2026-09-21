# IBDiff — code

Zero-shot low-light enhancement with a frozen Stable Diffusion 2.1 prior plus
three training-free guidance modules (illumination gate, wavelet LL prior,
adaptive step scheduling). See `../paper/model-doc-fa.md` for the method.

## Setup (local, Windows + NVIDIA)

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt
```

First run downloads `stabilityai/stable-diffusion-2-1-base` (~3.5 GB) into the
Hugging Face cache. 8 GB VRAM is enough (fp16, attention features on CPU).

## Enhance

```powershell
python -m ibdiff.enhance --input path\to\img.png --output out --seed 0
python -m ibdiff.enhance --input data\ExDark --output out\exdark --seed 0
```

Ablations: `--no-gate`, `--no-wavelet`, `--fixed-steps`.

## Evaluate

Paired (LOL-style: two folders with matching filenames):
```powershell
python -m ibdiff.evaluate --low data\LOLv2\Test\Low --high data\LOLv2\Test\Normal --out results\lolv2 --runs 5
```

Unpaired:
```powershell
python -m ibdiff.evaluate --unpaired data\ExDark --out results\exdark --runs 5
```

Metrics: PSNR / SSIM / LOE / under-over-exposed % / mean brightness natively;
LPIPS (`pip install lpips`) and MUSIQ/NIQE (`pip install pyiqa`) when available.
First row of `metrics.csv` per image, plus mean±std summary.

## Datasets (place under `data/`, not tracked by git)

- LOL-v1: official page `daooshee.github.io/BMVC2018website` — `eval15/low|high` for test
- LOL-v2-real: `Test/Low`, `Test/Normal`
- ExDark / DICM / NPE / MEF / VV: flat image folders (unpaired mode)
- Colab: see `colab_ibdiff.ipynb` (Drive mount + upload)
