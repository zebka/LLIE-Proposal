# -*- coding: utf-8 -*-
"""Reference and no-reference metrics (torch-native; LPIPS/MUSIQ/NIQE optional)."""
import math
from typing import Optional

import torch
import torch.nn.functional as F


def psnr(a: torch.Tensor, b: torch.Tensor, data_range: float = 1.0) -> float:
    mse = F.mse_loss(a.float(), b.float()).item()
    if mse <= 0:
        return float("inf")
    return 20 * math.log10(data_range) - 10 * math.log10(mse)


def _gaussian_window(ch: int, k: int = 11, sigma: float = 1.5,
                     device=None, dtype=None):
    coords = torch.arange(k, device=device, dtype=dtype) - k // 2
    g = torch.exp(-(coords ** 2) / (2 * sigma ** 2))
    g = g / g.sum()
    w = (g[:, None] * g[None, :]).expand(ch, 1, k, k).contiguous()
    return w


def ssim(a: torch.Tensor, b: torch.Tensor, data_range: float = 1.0) -> float:
    """SSIM for (C,H,W) or (N,C,H,W) in [0, data_range]."""
    x = a.float()
    y = b.float()
    if x.dim() == 3:
        x, y = x.unsqueeze(0), y.unsqueeze(0)
    c = x.shape[1]
    w = _gaussian_window(c, device=x.device, dtype=x.dtype)
    mu_x = F.conv2d(x, w, groups=c, padding=5)
    mu_y = F.conv2d(y, w, groups=c, padding=5)
    mu_xx, mu_yy, mu_xy = mu_x * mu_x, mu_y * mu_y, mu_x * mu_y
    sx = F.conv2d(x * x, w, groups=c, padding=5) - mu_xx
    sy = F.conv2d(y * y, w, groups=c, padding=5) - mu_yy
    sxy = F.conv2d(x * y, w, groups=c, padding=5) - mu_xy
    c1, c2 = (0.01 * data_range) ** 2, (0.03 * data_range) ** 2
    num = (2 * mu_xy + c1) * (2 * sxy + c2)
    den = (mu_xx + mu_yy + c1) * (sx + sy + c2)
    return (num / den.clamp_min(1e-12)).mean().item()


def exposure_stats(img: torch.Tensor):
    """img (C,H,W) [0,1] -> (under%, over%, mean brightness)."""
    m = img.float().mean(dim=0)
    under = (m < 0.05).float().mean().item() * 100.0
    over = (m > 0.95).float().mean().item() * 100.0
    return under, over, m.mean().item()


def loe(inp: torch.Tensor, enh: torch.Tensor, max_side: int = 50) -> float:
    """Lightness Order Error (Wang et al. 2013). Lower is better."""
    def light(x):
        x = x.float()
        h, w = x.shape[1], x.shape[2]
        s = max(1, math.ceil(max(h, w) / max_side))
        if s > 1:
            x = F.avg_pool2d(x.unsqueeze(0), s, s).squeeze(0)
        return x.amax(dim=0).reshape(-1)
    u, ue = light(inp), light(enh)
    n = u.numel()
    order = (u[:, None] <= u[None, :])
    order_e = (ue[:, None] <= ue[None, :])
    return (order ^ order_e).float().sum().item() / (n * n)


_lpips_fn = None


def lpips(a: torch.Tensor, b: torch.Tensor, net: str = "alex") -> Optional[float]:
    """LPIPS via `lpips` package if installed, else None."""
    global _lpips_fn
    if _lpips_fn is None:
        try:
            import lpips as _lp
            _lpips_fn = _lp.LPIPS(net=net)
        except Exception:
            _lpips_fn = False
    if _lpips_fn is False:
        return None
    import torch as _t
    with _t.no_grad():
        return float(_lpips_fn(a.float() * 2 - 1, b.float() * 2 - 1).item())


_pyiqa = None


def pyiqa_score(img: torch.Tensor, metric: str):
    """NIQE / MUSIQ via `pyiqa` if installed, else None. img (C,H,W) [0,1]."""
    global _pyiqa
    if _pyiqa is None:
        try:
            import pyiqa as _p
            _pyiqa = _p
        except Exception:
            _pyiqa = False
    if _pyiqa is False:
        return None
    try:
        m = _pyiqa.create_metric(metric)
        with torch.no_grad():
            return float(m(img.float().unsqueeze(0)).item())
    except Exception:
        return None
