"""Year-by-year company simulator (PDF 2 §4–§12).

Reproduces the worked example in PDF 2 §12 with κ=2 and γ_late=0.6:

  Year   Team  Revenue  Cash Opex  EBITDA   Tax   Capex   ΔWC   DSF In   Red
  Y0     3     40       286        −246     0     20      0     0        0
  Y1     5     180      480        −300     0     35      10    400      0
  Y2     8     520      772        −252     0     60      20    350      0
  Y3     12    1550     1172       378      85    90      40    0        49
  Y4     18    2700     1744       956      224   120     80    0        213

(units: € thousand)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd


@dataclass
class CompanyParams:
    """Configuration shared across all years for one company."""

    kappa: float = 2.0                  # company-level redemption multiple Ω = κ·ΣI
    gamma_early: float = 0.0            # share of DistCash retained for reinvest, years before switch
    gamma_late: float = 0.6             # share retained from gamma_switch_year onwards
    gamma_switch_year: int = 3          # PDF §5.6 says γ=60% in Y3+
    tau: float = 0.25                   # effective tax rate on positive EBIT
    L_min: float = 100_000.0            # absolute minimum reserve floor (€)
    rho_reserve_months: float = 3.0     # months of CashOpex held as resilience
    C0: float = 0.0                     # opening cash at t=0


@dataclass
class StageInputs:
    """One row of per-year operating inputs."""

    year: int                           # 0=Day 1, 1=Y1, ...
    team: float
    wage_per_fte: float
    revenue: float
    other_opex: float                   # non-payroll opex
    capex: float
    delta_wc: float
    dsf_in: float                       # gross DSF capital injection in this year
    depreciation: float = 0.0           # per-year depreciation (PDF §12 implies D=40 in Y3, 60 in Y4)
    force_res_gap: Optional[float] = None  # override the resilience gap (PDF §12 sets Y3=40k, Y4=0)


def _gamma_for_year(p: CompanyParams, t: int) -> float:
    return p.gamma_early if t < p.gamma_switch_year else p.gamma_late


def simulate_company(
    params: CompanyParams, stages: List[StageInputs]
) -> pd.DataFrame:
    """Run the deterministic year-by-year engine.

    Returns a DataFrame with one row per stage and columns including FCF,
    L_star, ResGap, DistCash, Reinvest, RedBase, Trigger, Red, CumRed,
    Cash_open, Cash_close.
    """
    rows = []
    cum_invest = 0.0
    cum_red = 0.0
    cash = params.C0

    for t, s in enumerate(stages):
        payroll = s.team * s.wage_per_fte
        cash_opex = payroll + s.other_opex
        ebitda = s.revenue - cash_opex
        ebit = ebitda - s.depreciation
        tax = params.tau * max(0.0, ebit)
        fcf = ebitda - tax - s.capex - s.delta_wc

        L_star = max(params.L_min, params.rho_reserve_months * cash_opex / 12.0)
        cash_pre = cash
        if s.force_res_gap is not None:
            res_gap = max(0.0, s.force_res_gap)
        else:
            res_gap = max(0.0, L_star - (cash_pre + fcf))
        dist_cash = max(0.0, fcf - res_gap)
        gamma = _gamma_for_year(params, s.year)
        reinvest = gamma * dist_cash
        red_base = (1.0 - gamma) * dist_cash

        cum_invest += s.dsf_in
        omega = params.kappa * cum_invest
        trigger = (ebitda > 0) and (dist_cash > 0) and (cum_red < omega)
        red = (
            min(red_base, max(0.0, omega - cum_red)) if trigger else 0.0
        )
        cum_red += red

        # Cash close: open + injection + revenue - opex - tax - capex - dWC - red
        # (reinvest is retained inside the firm and stays in cash.)
        cash_close = cash_pre + s.dsf_in + s.revenue - cash_opex - tax - s.capex - s.delta_wc - red

        rows.append(
            {
                "Year": s.year,
                "Team": s.team,
                "Wage": s.wage_per_fte,
                "Payroll": payroll,
                "OtherOpex": s.other_opex,
                "CashOpex": cash_opex,
                "Revenue": s.revenue,
                "EBITDA": ebitda,
                "EBIT": ebit,
                "Tax": tax,
                "Capex": s.capex,
                "dWC": s.delta_wc,
                "FCF": fcf,
                "L_star": L_star,
                "ResGap": res_gap,
                "DistCash": dist_cash,
                "gamma": gamma,
                "Reinvest": reinvest,
                "RedBase": red_base,
                "DSF_in": s.dsf_in,
                "CumInvest": cum_invest,
                "Omega": omega,
                "Trigger": int(bool(trigger)),
                "Red": red,
                "CumRed": cum_red,
                "Cash_open": cash_pre,
                "Cash_close": cash_close,
            }
        )
        cash = cash_close

    return pd.DataFrame(rows)


def worked_example_section_12() -> tuple[CompanyParams, List[StageInputs]]:
    """PDF 2 §12 worked example fixture.

    PDF specifies cash opex 286/480/772/1172/1744 (€k). We allocate
    payroll = team·€80k, other_opex = remainder so totals match.
    Depreciation values are reverse-engineered from the PDF tax column
    (Tax Y3=85k → EBIT=340k → D=378-340=38k≈40k; Tax Y4=224k → D=60k).
    Resilience gap forced to PDF's printed values (Y3=40k, Y4=0).
    """
    params = CompanyParams(
        kappa=2.0,
        gamma_early=0.0,
        gamma_late=0.6,
        gamma_switch_year=3,
        tau=0.25,
        L_min=100_000.0,
        rho_reserve_months=3.0,
        C0=0.0,
    )
    wage = 80_000.0
    cash_opex = [286_000, 480_000, 772_000, 1_172_000, 1_744_000]
    teams = [3, 5, 8, 12, 18]
    revenues = [40_000, 180_000, 520_000, 1_550_000, 2_700_000]
    capex = [20_000, 35_000, 60_000, 90_000, 120_000]
    dwc = [0, 10_000, 20_000, 40_000, 80_000]
    dsf_in = [0, 400_000, 350_000, 0, 0]
    depreciation = [0, 0, 0, 40_000, 60_000]
    force_res_gap = [None, None, None, 40_000.0, 0.0]

    stages: List[StageInputs] = []
    for t in range(5):
        payroll_t = teams[t] * wage
        other_opex_t = cash_opex[t] - payroll_t
        stages.append(
            StageInputs(
                year=t,
                team=teams[t],
                wage_per_fte=wage,
                revenue=revenues[t],
                other_opex=other_opex_t,
                capex=capex[t],
                delta_wc=dwc[t],
                dsf_in=dsf_in[t],
                depreciation=depreciation[t],
                force_res_gap=force_res_gap[t],
            )
        )
    return params, stages
