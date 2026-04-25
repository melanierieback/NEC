"""Impact layer: I = N·p·L·o·d·a·e with theology coupling.

PDF 1 §3.7: I = N · p · L · o · d · a · e
PDF 1 §5.1: L(U)=L0(1-αU), o(U)=o0(1-βU), d(U)=d0(1-γU)
"""
from __future__ import annotations

from typing import List

import pandas as pd

from . import financial, theology


def couple_L(L0: float, alpha: float, U: float) -> float:
    return max(0.0, L0 * (1.0 - alpha * U))


def couple_o(o0: float, beta: float, U: float) -> float:
    return max(0.0, o0 * (1.0 - beta * U))


def couple_d(d0: float, gamma: float, U: float) -> float:
    return max(0.0, d0 * (1.0 - gamma * U))


def impact(
    N: float,
    p: float,
    L0: float,
    o0: float,
    d0: float,
    alpha: float,
    beta: float,
    gamma: float,
    a: float,
    e: float,
    U: float,
) -> float:
    """I = N · p · L(U) · o(U) · d(U) · a · e."""
    L = couple_L(L0, alpha, U)
    o = couple_o(o0, beta, U)
    d = couple_d(d0, gamma, U)
    return N * p * L * o * d * a * e


# Five preset rows from PDF 1 §5.4 — same r=2.90, M=2.49, but different
# moral composition produces different impact (≈451, 417, 351, 289, 244).
_SCENARIOS: List[dict] = [
    {"id": "A", "name": "Strongly licit",   "delta": 1.60, "pi": 0.20, "rho": 0.10, "lam": 0.00},
    {"id": "B", "name": "Mostly licit",     "delta": 1.30, "pi": 0.20, "rho": 0.30, "lam": 0.10},
    {"id": "C", "name": "Mixed",            "delta": 0.90, "pi": 0.20, "rho": 0.50, "lam": 0.30},
    {"id": "D", "name": "Extractive drift", "delta": 0.60, "pi": 0.10, "rho": 0.70, "lam": 0.50},
    {"id": "E", "name": "Highly usurious",  "delta": 0.30, "pi": 0.10, "rho": 0.80, "lam": 0.70},
]


# Default coupling parameters used by PDF §5.4 worked example.
DEFAULT_COUPLING = {
    "L0": 8.0,
    "o0": 1.0,
    "d0": 1.0,
    "alpha": 0.20,
    "beta": 0.15,
    "gamma": 0.20,
    "N": 40.0,
    "p": 0.60,
    "k": 5.0,
    "a": 2.0,
    "e": 1.2,
    "mu": 0.5,
    "eta": 0.6,
}


def scenario_table(
    N: float = DEFAULT_COUPLING["N"],
    p: float = DEFAULT_COUPLING["p"],
    k: float = DEFAULT_COUPLING["k"],
    L0: float = DEFAULT_COUPLING["L0"],
    o0: float = DEFAULT_COUPLING["o0"],
    d0: float = DEFAULT_COUPLING["d0"],
    alpha: float = DEFAULT_COUPLING["alpha"],
    beta: float = DEFAULT_COUPLING["beta"],
    gamma: float = DEFAULT_COUPLING["gamma"],
    a: float = DEFAULT_COUPLING["a"],
    e: float = DEFAULT_COUPLING["e"],
    mu: float = DEFAULT_COUPLING["mu"],
    eta: float = DEFAULT_COUPLING["eta"],
) -> pd.DataFrame:
    """Reproduce the §5.4 / §5.5 tables: same M=2.49, varying impact."""
    rows = []
    for s in _SCENARIOS:
        r = financial.repayment_cap(s["delta"], s["pi"], s["rho"], s["lam"])
        U = theology.usury_pressure(s["rho"], s["lam"])
        M = financial.single_cycle_multiple(k, p, r)
        M_lic = financial.licit_multiple(k, p, s["delta"], s["pi"])
        M_us = financial.usury_multiple(k, p, s["rho"], s["lam"])
        L = couple_L(L0, alpha, U)
        o = couple_o(o0, beta, U)
        d = couple_d(d0, gamma, U)
        I = impact(N, p, L0, o0, d0, alpha, beta, gamma, a, e, U)
        T = theology.theological_integrity(U, mu, eta)
        rows.append(
            {
                "Scenario": f"{s['id']}. {s['name']}",
                "delta": s["delta"],
                "pi": s["pi"],
                "rho": s["rho"],
                "lam": s["lam"],
                "r": round(r, 3),
                "U": round(U, 3),
                "M": round(M, 3),
                "M_licit": round(M_lic, 3),
                "M_usury": round(M_us, 3),
                "L(U)": round(L, 3),
                "o(U)": round(o, 4),
                "d(U)": round(d, 3),
                "Impact": round(I, 1),
                "T": round(T, 3),
            }
        )
    return pd.DataFrame(rows)
