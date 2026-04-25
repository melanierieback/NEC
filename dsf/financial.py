"""Closed-form financial layer of the DSF model.

PDF 1 §2: M = r·k·p / (1 + (k-1)·p)
PDF 1 §2.10: M_total = M^c
PDF 1 §7: W_{t+1} = η·W_t·M  (stewardship compounding)
"""
from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd


def repayment_cap(delta: float, pi_: float, rho: float, lam: float) -> float:
    """r = 1 + δ + π + ρ + λ  (PDF 1 §4.2)."""
    return 1.0 + delta + pi_ + rho + lam


def single_cycle_multiple(k: float, p: float, r: float) -> float:
    """M = r·k·p / (1 + (k-1)·p)  (PDF 1 eq. 7)."""
    denom = 1.0 + (k - 1.0) * p
    if denom == 0:
        return 0.0
    return (r * k * p) / denom


def licit_multiple(k: float, p: float, delta: float, pi_: float) -> float:
    """M_licit = (1+δ+π)·k·p / (1 + (k-1)·p)  (PDF 1 eq. 23)."""
    denom = 1.0 + (k - 1.0) * p
    return (1.0 + delta + pi_) * k * p / denom


def usury_multiple(k: float, p: float, rho: float, lam: float) -> float:
    """M_usury = (ρ+λ)·k·p / (1 + (k-1)·p)  (PDF 1 eq. 24)."""
    denom = 1.0 + (k - 1.0) * p
    return (rho + lam) * k * p / denom


def evergreen_multiple(M: float, c: int) -> float:
    """M_total = M^c  (PDF 1 eq. 16)."""
    return float(M) ** int(c)


def vc_benchmark(c: int, years_per_cycle: int = 10, annual: float = 0.05) -> float:
    """Conventional 5%-annual VC benchmark = (1+annual)^(years_per_cycle·c)  (PDF 1 §2.12)."""
    return (1.0 + annual) ** (years_per_cycle * c)


def benchmark_table(
    k: float,
    r: float,
    ps: Sequence[float],
    cs: Sequence[int],
    years_per_cycle: int = 10,
    annual: float = 0.05,
) -> pd.DataFrame:
    """Reproduces PDF §2.12: M_total vs VC benchmark across (p, c) grid."""
    rows = []
    for p in ps:
        m = single_cycle_multiple(k, p, r)
        for c in cs:
            mt = evergreen_multiple(m, c)
            vc = vc_benchmark(c, years_per_cycle, annual)
            rows.append(
                {
                    "p": p,
                    "c": c,
                    "M": round(m, 4),
                    "M_total": round(mt, 4),
                    "VC_benchmark": round(vc, 4),
                    "result": "PASS" if mt > vc else "FAIL",
                }
            )
    return pd.DataFrame(rows)


def stewardship_path(W0: float, eta: float, M: float, T: int) -> np.ndarray:
    """W_{t+1} = η·W_t·M  (PDF 1 §7.1 evergreen stewardship compounding)."""
    factor = eta * M
    return np.array([W0 * (factor ** t) for t in range(T + 1)], dtype=float)


def heatmap_M(
    ps: Sequence[float], ks: Sequence[float], r: float
) -> pd.DataFrame:
    """2-D grid of M values for sensitivity heatmap."""
    data = np.zeros((len(ps), len(ks)))
    for i, p in enumerate(ps):
        for j, k in enumerate(ks):
            data[i, j] = single_cycle_multiple(k, p, r)
    return pd.DataFrame(data, index=[round(p, 3) for p in ps], columns=[round(k, 3) for k in ks])
