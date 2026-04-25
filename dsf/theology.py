"""Theology layer: Thomistic decomposition of the repayment cap.

PDF 1 §4.4: U = 0.5·ρ + λ
PDF 1 §5.1: T = 1 - U + μ·η
"""
from __future__ import annotations

from .financial import repayment_cap as _repayment_cap

repayment_cap = _repayment_cap


def usury_pressure(rho: float, lam: float) -> float:
    """U = 0.5·ρ + λ  (PDF 1 eq. 26)."""
    return 0.5 * rho + lam


def theological_integrity(U: float, mu: float, eta: float) -> float:
    """T = 1 − U + μ·η  (PDF 1 §5.3 / Eq 31)."""
    return 1.0 - U + mu * eta


def usury_share(rho: float, lam: float, delta: float, pi_: float) -> float:
    """Compositional usury index U_comp = (ρ+λ) / (r-1) from PDF 1 eq. 25."""
    denom = delta + pi_ + rho + lam
    if denom <= 0:
        return 0.0
    return (rho + lam) / denom
