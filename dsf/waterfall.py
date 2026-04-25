"""Cooperative waterfall (PDF 2 §11) and per-vintage capped pro-rata distribution.

Per year:
  Π_t        = Σ Red_{i,t}                                  (companies → fund)
  Gross_t    = Π_t + LiquidationProceeds + OtherProceeds
  Net_t      = max(0, Gross - CoopOpex - Tax - Liab - DS_NPV)
  Avail_t    = max(0, Net - ReserveAlloc)
  Reinvest_t = min(Avail, max(η·Avail, E★ - E_t))
  DistPool_t = Avail - Reinvest_t
  E_{t+1}    = E_t + Reinvest_t - NewDeploy_t

Per-vintage iterative pro-rata (§11.3): provisional = (u/Σu_live)·DistPool,
clamp to headroom H_v = r·K_v − cum_dist_v, redistribute residual.

NPV-loan rule (§15.6): no DistPool until DS_NPV is fully provided for and
E_t ≥ E★.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd


@dataclass
class Vintage:
    vintage_id: str
    year: int                  # year vintage was subscribed
    K: float                   # contributed capital
    units: float               # participation units (typically proportional to K)
    r_cap: float = 3.0         # PDF baseline cap multiple
    cum_dist: float = 0.0
    status: str = "economic"   # economic | non-economic | exited

    @property
    def headroom(self) -> float:
        return max(0.0, self.r_cap * self.K - self.cum_dist)


@dataclass
class WaterfallParams:
    eta_early: float = 0.80
    eta_late: float = 0.40
    eta_switch_year: int = 4
    E_star: float = 50_000.0
    E0: float = 50_000.0
    coop_opex_schedule: Optional[List[float]] = None
    coop_tax_rate: float = 0.0
    other_liabilities_schedule: Optional[List[float]] = None
    npv_ds_schedule: Optional[List[float]] = None        # debt service per year
    new_deploy_schedule: Optional[List[float]] = None    # capital deployed into new companies
    reserve_alloc_schedule: Optional[List[float]] = None
    formation_costs_y0: float = 30_000.0                 # Coop+Stichting+Golden share (PDF §15.5)
    horizon: int = 10


def _eta_for_year(p: WaterfallParams, t: int) -> float:
    return p.eta_early if t < p.eta_switch_year else p.eta_late


def _from_schedule(sched: Optional[List[float]], t: int, default: float = 0.0) -> float:
    if sched is None:
        return default
    if t < 0 or t >= len(sched):
        return default
    return float(sched[t])


def pro_rata_capped(
    dist_pool: float, vintages: List[Vintage]
) -> Dict[str, float]:
    """Iterative pro-rata-with-cap-clamp (PDF §11.3).

    Returns a mapping vintage_id → distribution amount this period.
    Mutates nothing; the caller is responsible for updating cum_dist.
    """
    payouts: Dict[str, float] = {v.vintage_id: 0.0 for v in vintages}
    if dist_pool <= 0:
        return payouts

    # Work on copies of headroom so we can clamp iteratively.
    headroom = {v.vintage_id: v.headroom for v in vintages if v.status == "economic"}
    units = {v.vintage_id: v.units for v in vintages if v.status == "economic"}

    remaining = dist_pool
    # Iterate at most len(vintages)+2 rounds; each round either fully distributes
    # or saturates ≥1 vintage at its cap.
    for _ in range(len(vintages) + 2):
        live = [vid for vid, h in headroom.items() if h > 0 and units[vid] > 0]
        if not live or remaining <= 1e-9:
            break
        total_units = sum(units[vid] for vid in live)
        provisional = {vid: (units[vid] / total_units) * remaining for vid in live}
        any_clamped = False
        round_paid = 0.0
        for vid in live:
            pay = min(provisional[vid], headroom[vid])
            if pay < provisional[vid] - 1e-9:
                any_clamped = True
            payouts[vid] += pay
            headroom[vid] -= pay
            round_paid += pay
        remaining -= round_paid
        if not any_clamped:
            break
    return payouts


def fund_waterfall(
    company_redemptions: pd.Series,
    vintages: List[Vintage],
    params: WaterfallParams,
) -> pd.DataFrame:
    """Run the cooperative waterfall over `params.horizon` years.

    `company_redemptions` is a pd.Series indexed by integer year 0..T-1 giving
    Π_t (aggregated company redemption inflow). Missing years default to 0.

    Returns a DataFrame with one row per year and one column per vintage
    plus the canonical waterfall columns.
    """
    T = params.horizon
    rows = []
    E = params.E0

    # Deduct one-shot formation costs from the year-0 evergreen pot (these
    # are real cash uses paid out of the cooperative's opening balance).
    if params.formation_costs_y0:
        E = max(0.0, E - params.formation_costs_y0)

    for t in range(T):
        Pi = float(company_redemptions.get(t, 0.0))
        gross = Pi  # no liquidation/other in baseline
        coop_opex = _from_schedule(params.coop_opex_schedule, t, 0.0)
        liab_other = _from_schedule(params.other_liabilities_schedule, t, 0.0)
        ds_npv = _from_schedule(params.npv_ds_schedule, t, 0.0)
        coop_tax = params.coop_tax_rate * max(0.0, gross - coop_opex - liab_other - ds_npv)
        net = max(0.0, gross - coop_opex - coop_tax - liab_other - ds_npv)
        reserve_alloc = _from_schedule(params.reserve_alloc_schedule, t, 0.0)
        avail = max(0.0, net - reserve_alloc)

        eta = _eta_for_year(params, t)
        evergreen_topup = max(0.0, params.E_star - E)
        reinvest = min(avail, max(eta * avail, evergreen_topup))

        # PDF §15.6 NPV-loan rule: no member distribution while either E < E★
        # or NPV debt service is unfunded. The DS_NPV deduction above already
        # enforces priority; the E < E★ guard kicks in here.
        dist_pool = max(0.0, avail - reinvest)
        if E + reinvest < params.E_star - 1e-6:
            # Force everything into reinvest until the floor is restored.
            reinvest = avail
            dist_pool = 0.0

        # Per-vintage capped pro-rata.
        payouts = pro_rata_capped(dist_pool, vintages)
        # Update vintage state.
        for v in vintages:
            pay = payouts.get(v.vintage_id, 0.0)
            v.cum_dist += pay
            if v.cum_dist >= v.r_cap * v.K - 1e-6 and v.status == "economic":
                v.status = "exited"

        new_deploy = _from_schedule(params.new_deploy_schedule, t, 0.0)
        E_open = E
        E = E + reinvest - new_deploy

        row: Dict[str, float] = {
            "Year": t,
            "Pi": Pi,
            "Gross": gross,
            "CoopOpex": coop_opex,
            "CoopTax": coop_tax,
            "DSNPV": ds_npv,
            "OtherLiab": liab_other,
            "Net": net,
            "ReserveAlloc": reserve_alloc,
            "Avail": avail,
            "eta": eta,
            "Reinvest": reinvest,
            "DistPool": dist_pool,
            "E_open": E_open,
            "E_close": E,
            "NewDeploy": new_deploy,
            "TotalPayout": sum(payouts.values()),
        }
        for v in vintages:
            row[f"Pay[{v.vintage_id}]"] = payouts.get(v.vintage_id, 0.0)
            row[f"Cum[{v.vintage_id}]"] = v.cum_dist
            row[f"Status[{v.vintage_id}]"] = v.status
        rows.append(row)

    return pd.DataFrame(rows)


def default_launch(
    company_redemptions: pd.Series,
) -> tuple[List[Vintage], WaterfallParams]:
    """PDF 2 §15 minimum-viable launch: 2 members @ €100k, NPV loan €300k,
    formation costs €30k, E★_0=€50k.
    """
    vintages = [
        Vintage(vintage_id="A_v0", year=0, K=100_000.0, units=1.0, r_cap=3.0),
        Vintage(vintage_id="B_v0", year=0, K=100_000.0, units=1.0, r_cap=3.0),
    ]
    params = WaterfallParams(
        eta_early=0.80,
        eta_late=0.40,
        eta_switch_year=4,
        E_star=50_000.0,
        E0=200_000.0 + 300_000.0,                # member capital + NPV loan
        coop_opex_schedule=[20_000.0] * 10,
        coop_tax_rate=0.0,
        npv_ds_schedule=[30_000.0] * 10,         # simple ten-year amortisation
        new_deploy_schedule=[0.0] * 10,
        reserve_alloc_schedule=[0.0] * 10,
        formation_costs_y0=30_000.0,
        horizon=10,
    )
    return vintages, params
