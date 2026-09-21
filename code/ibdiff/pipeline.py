# -*- coding: utf-8 -*-
"""Core IBDiff pipeline: Cho-style zero-shot base + illumination gate + wavelet + adaptive steps.

Base scheme (Cho et al., arXiv:2412.13401):
  preprocess -> DDIM inversion (T steps, store up-block self-attention q/k/v)
  -> AdaIN -> denoise with self-attention replacement (frozen SD weights).

IBDiff additions (training-free, sampling-time only):
  (B) illumination-gate guidance on the predicted noise,
  (C) wavelet LL-band restriction of the guidance + final HF merge,
  (D) adaptive number of sampling steps from scene darkness.
"""
import math
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn.functional as F


# ---------------------------------------------------------------- Haar wavelet

def dwt_haar(x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor,
                                       torch.Tensor, torch.Tensor]:
    """2D Haar DWT. x: (B,C,H,W) -> LL, LH, HL, HH each (B,C,H/2,W/2)."""
    b, c, h, w = x.shape
    assert h % 2 == 0 and w % 2 == 0, "DWT needs even H, W"
    x = x.reshape(b, c, h // 2, 2, w // 2, 2)
    a = x[:, :, :, 0, :, 0]
    b_ = x[:, :, :, 0, :, 1]
    c_ = x[:, :, :, 1, :, 0]
    d = x[:, :, :, 1, :, 1]
    ll = (a + b_ + c_ + d) / 2.0
    lh = (a - b_ + c_ - d) / 2.0
    hl = (a + b_ - c_ - d) / 2.0
    hh = (a - b_ - c_ + d) / 2.0
    return ll, lh, hl, hh


def idwt_haar(ll: torch.Tensor, lh: torch.Tensor,
              hl: torch.Tensor, hh: torch.Tensor) -> torch.Tensor:
    """Inverse 2D Haar DWT."""
    b, c, h, w = ll.shape
    out = torch.empty(b, c, h * 2, w * 2, device=ll.device, dtype=ll.dtype)
    out[:, :, 0::2, 0::2] = (ll + lh + hl + hh) / 2.0
    out[:, :, 0::2, 1::2] = (ll - lh + hl - hh) / 2.0
    out[:, :, 1::2, 0::2] = (ll + lh - hl - hh) / 2.0
    out[:, :, 1::2, 1::2] = (ll - lh - hl + hh) / 2.0
    return out


def gaussian_kernel5(device, dtype) -> torch.Tensor:
    k = torch.tensor([1., 4., 6., 4., 1.], device=device, dtype=dtype)
    k = k / k.sum()
    return (k[:, None] * k[None, :])[None, None]


# ---------------------------------------------------------------- pipeline

class IBDiffPipeline:
    def __init__(self, model_id: str = "Manojb/stable-diffusion-2-1-base",
                 device: str = "cuda", fp16: bool = True, T: int = 25,
                 empty_prompt: str = ""):
        from diffusers import DDIMScheduler, AutoencoderKL, UNet2DConditionModel

        self.device = torch.device(device)
        self.dtype = torch.float16 if (fp16 and self.device.type == "cuda") else torch.float32
        self.T = T

        self.vae = AutoencoderKL.from_pretrained(model_id, subfolder="vae",
                                                 torch_dtype=self.dtype).to(self.device)
        self.unet = UNet2DConditionModel.from_pretrained(model_id, subfolder="unet",
                                                         torch_dtype=self.dtype).to(self.device)
        self.vae.eval()
        self.unet.eval()
        for p in list(self.vae.parameters()) + list(self.unet.parameters()):
            p.requires_grad_(False)

        self.scheduler = DDIMScheduler.from_pretrained(model_id, subfolder="scheduler")
        self.scheduler.set_timesteps(T)
        self._ts_asc: List[int] = sorted(int(t) for t in self.scheduler.timesteps.tolist())
        self._alphas = self.scheduler.alphas_cumprod.to(self.device)

        try:
            from transformers import CLIPTextModel, CLIPTokenizer  # noqa
        except Exception:
            pass
        # unconditional embedding (zeros of SD2.1 text dim 1024)
        self._uncond = torch.zeros(1, 77, 1024, device=self.device, dtype=self.dtype)
        _ = empty_prompt

        # self-attention modules in up_blocks (structural, version-robust)
        self._sa: List[Tuple[str, object]] = []
        for name, mod in self.unet.named_modules():
            if "up_blocks" not in name:
                continue
            if type(mod).__name__ != "Attention":
                continue
            if not all(hasattr(mod, a) for a in ("to_q", "to_k", "to_v")):
                continue
            try:
                if mod.to_k.in_features != mod.to_q.in_features:
                    continue  # cross-attention
            except Exception:
                continue
            self._sa.append((name, mod))
        assert self._sa, "no self-attention modules found in up_blocks"
        print(f"[IBDiff] collected {len(self._sa)} up-block self-attention modules")

        self._store: Dict[Tuple[int, int, str], torch.Tensor] = {}
        self._cur_t: int = -1
        self._mode: str = "invert"
        self._hooks = []
        self._register_hooks()

    # ------------------------------------------------------------- SA hooks
    def _register_hooks(self):
        for idx, (name, attn) in enumerate(self._sa):
            for role, proj in (("q", attn.to_q), ("k", attn.to_k), ("v", attn.to_v)):
                proj.register_forward_hook(self._make_hook(idx, role))

    def _make_hook(self, idx: int, role: str):
        def fn(module, _inp, out):
            key = (self._cur_t, idx, role)
            if self._mode == "invert":
                self._store[key] = out.detach().to("cpu")
                return None
            saved = self._store.get(key)
            if saved is None:
                return None
            return saved.to(out.device, dtype=out.dtype)
        return fn

    # ------------------------------------------------------------- helpers
    @torch.no_grad()
    def _vae_encode(self, img: torch.Tensor) -> torch.Tensor:
        sf = self.vae.config.scaling_factor
        return self.vae.encode(img.to(self.dtype)).latent_dist.mode() * sf

    @torch.no_grad()
    def _vae_decode(self, z: torch.Tensor) -> torch.Tensor:
        sf = self.vae.config.scaling_factor
        return self.vae.decode((z / sf).to(self.dtype)).sample.clamp(0, 1)

    def _eps(self, z: torch.Tensor, t: int) -> torch.Tensor:
        self._cur_t = int(t)
        return self.unet(z, t, encoder_hidden_states=self._uncond)["sample"]

    # ------------------------------------------------------------- main API
    @torch.no_grad()
    def enhance(self, img01: torch.Tensor,
                tau_low: float = 0.35, tau_high: float = 0.65, s_gate: float = 0.05,
                mu_E: float = 0.5, lam_d: float = 1.5, lam_b: float = 1.5,
                alpha: float = 0.6,
                use_gate: bool = True, use_wavelet: bool = True,
                adaptive_steps: bool = True,
                verbose: bool = False) -> torch.Tensor:
        """img01: (1,3,H,W) float in [0,1] on self.device. Returns (1,3,H,W) [0,1]."""
        dev, dt = self.device, self.dtype
        img01 = img01.to(dev, dtype=torch.float32)

        # ---- (1) preprocess: lift mean to 30/255 (Cho et al.)
        mean255 = img01.mean().item() * 255.0
        pre = img01 * (30.0 / max(mean255, 1e-3)) if mean255 < 30.0 else img01
        pre = pre.clamp(0, 1)

        # ---- illumination map + gates (input space, reused at latent grid later)
        maxc = pre.amax(dim=1, keepdim=True)                      # (1,1,H,W)
        k5 = gaussian_kernel5(dev, torch.float32)
        L_hat = F.conv2d(F.pad(maxc, (2, 2, 2, 2), mode="reflect"), k5)
        G_dark = torch.sigmoid((tau_low - L_hat) / s_gate)
        G_bright = torch.sigmoid((L_hat - tau_high) / s_gate)

        s_I = float(1.0 - L_hat.mean().item())
        T_eff = self.T if not adaptive_steps else max(
            4, int(round(self.T * (alpha + (1.0 - alpha) * s_I))))
        if verbose:
            print(f"[IBDiff] darkness={s_I:.3f} T_eff={T_eff} mean_in={mean255:.1f}")

        # ---- (2) invert (python floats for alphas: keeps latents in fp16)
        z = self._vae_encode(pre).to(dt)
        ts = self._ts_asc
        self._store.clear()
        self._mode = "invert"
        for i, t in enumerate(ts):
            a_t = float(self._alphas[t])
            a_n = float(self._alphas[ts[i + 1]]) if i + 1 < len(ts) else float(self._alphas[999])
            s1, s2 = math.sqrt(1 - a_t), math.sqrt(1 - a_n)
            eps = self._eps(z, t)
            x0 = (z - s1 * eps) / math.sqrt(a_t)
            z = math.sqrt(a_n) * x0 + s2 * eps

        # ---- (3) AdaIN to N(0, I)
        mu = z.mean(dim=(2, 3), keepdim=True)
        sd = z.std(dim=(2, 3), keepdim=True).clamp_min(1e-6)
        z = (z - mu) / sd

        # ---- gates at latent grid
        lh_lat, lw_lat = z.shape[2], z.shape[3]
        Gd = F.interpolate(G_dark, size=(lh_lat, lw_lat), mode="bilinear",
                           align_corners=False).to(dt)
        Gb = F.interpolate(G_bright, size=(lh_lat, lw_lat), mode="bilinear",
                           align_corners=False).to(dt)

        # ---- (4) sample with guidance
        desc = sorted(ts, reverse=True)
        stride = max(1, round(len(desc) / T_eff))
        sub = desc[::stride][:T_eff]
        self._mode = "sample"
        for j, t in enumerate(sub):
            prev = sub[j + 1] if j + 1 < len(sub) else -1
            a_t = float(self._alphas[t])
            a_p = float(self._alphas[prev]) if prev >= 0 else 1.0
            rt, rp = math.sqrt(a_t), math.sqrt(a_p)
            st, sp = math.sqrt(1 - a_t), math.sqrt(1 - a_p)
            eps = self._eps(z, t)
            if use_gate and (lam_d > 0 or lam_b > 0):
                x0 = (z - st * eps) / rt
                dec = self._vae_decode(x0.float()).mean(dim=1, keepdim=True)
                mu_loc = F.avg_pool2d(dec, kernel_size=8, stride=8)
                mu_loc = F.interpolate(mu_loc, size=(lh_lat, lw_lat),
                                       mode="bilinear", align_corners=False).to(dt)
                sched = float(t) / 1000.0
                corr = (lam_d * sched) * Gd * (mu_E - mu_loc) \
                    - (lam_b * sched) * Gb * torch.clamp(mu_loc - mu_E, min=0)
                eps_t = eps + corr
                if use_wavelet:
                    eps_t = self._ll_only(eps_t, eps)
                eps = eps_t
            x0 = (z - st * eps) / rt
            z = rp * x0 + sp * eps

        # ---- (5) decode + HF merge
        out = self._vae_decode(z.float())
        if use_wavelet:
            ll_o, _, _, _ = dwt_haar(out)
            _, lh_i, hl_i, hh_i = dwt_haar(
                F.interpolate(pre, size=out.shape[2:], mode="bilinear",
                              align_corners=False))
            out = idwt_haar(ll_o, lh_i, hl_i, hh_i).clamp(0, 1)
        return out.clamp(0, 1)

    @staticmethod
    def _ll_only(eps_guided: torch.Tensor, eps_plain: torch.Tensor) -> torch.Tensor:
        ll_g, _, _, _ = dwt_haar(eps_guided)
        _, lh, hl, hh = dwt_haar(eps_plain)
        return idwt_haar(ll_g, lh, hl, hh)
