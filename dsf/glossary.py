"""Glossary tables — Appendix A of PDF 1 and PDF 2."""
from __future__ import annotations

import pandas as pd


FINANCIAL_GLOSSARY = pd.DataFrame(
    [
        ("M",       "Single-cycle portfolio multiple",      "Core financial outcome for one investment cycle."),
        ("M_total", "Multi-cycle / evergreen multiple",     "Extends the single-cycle result across c cycles."),
        ("F",       "Financial outcome",                    "Used in the optimisation constraint F ≥ F_min."),
        ("p",       "Survival or success probability",      "Shared variable linking finance and impact."),
        ("k",       "Capital concentration",                "How much more capital is allocated to successful firms."),
        ("r",       "Repayment cap multiple",               "Total repayment claim made by the fund."),
        ("c",       "Number of evergreen cycles",           "Counts how many times capital is recycled."),
        ("W_t",     "Fund wealth at time t",                "Tracks evergreen capital over time."),
        ("r_f",     "Conventional interest rate",           "Used as a contrast case in standard interest compounding."),
        ("F_min",   "Minimum acceptable financial threshold","Lower bound for financial viability."),
        ("N",       "Number of projects funded",            "Basic scale of the portfolio."),
        ("S",       "Successful companies",                 "Used in pre-probability formulation of the portfolio model."),
        ("I_f",     "Investment in a failure-stage company","Base deployment level."),
        ("I_s",     "Investment in a successful company",   "Equal to k·I_f."),
        ("T",       "Average repayment time (years)",       "Used in the cash-flow extension."),
        ("C_ops",   "Annual operating cost",                "Salary plus administration."),
        ("C_mgmt",  "Management fee burden",                "Fee extension in the cash-flow model."),
        ("d_LP",    "LP distribution fraction",             "Share of annual cash distributed to investors."),
    ],
    columns=["Variable", "Meaning", "Role in the model"],
)


IMPACT_GLOSSARY = pd.DataFrame(
    [
        ("I",       "Impact outcome",                "Main infrastructure-creation measure."),
        ("I_t",     "Impact in period t",            "One time-slice of infrastructure creation."),
        ("I_total", "Total impact across periods",   "Sum of impact across the evergreen horizon."),
        ("L",       "Company lifetime",              "Duration that a successful firm remains active."),
        ("L_0",     "Baseline company lifetime",     "Starting lifetime before theological pressure is applied."),
        ("o",       "Openness retention factor",     "Whether the firm remains open-source."),
        ("o_0",     "Baseline openness retention",   "Starting openness before theological pressure is applied."),
        ("d",       "Sovereignty retention factor",  "Whether governance and control remain in Europe."),
        ("d_0",     "Baseline sovereignty retention","Starting sovereignty before theological pressure is applied."),
        ("a",       "Adoption factor",               "Captures actual uptake / use / deployment of the technology."),
        ("e",       "Ecosystem spillover multiplier","Reuse, collaboration, spinouts, ecosystem effects."),
        ("G",       "Governance design",             "Input into the survival function p = f(G,C,E)."),
        ("C",       "Capital structure / discipline","Input into the survival function p = f(G,C,E)."),
        ("E",       "Ecosystem support",             "Input into the survival function p = f(G,C,E)."),
    ],
    columns=["Variable", "Meaning", "Role in the model"],
)


THEOLOGY_GLOSSARY = pd.DataFrame(
    [
        ("δ",       "Damnum emergens",                       "Real expenses or real costs legitimately borne by the fund."),
        ("π",       "Poena conventionalis",                  "Bounded penalty / late-payment component."),
        ("ρ",       "Periculum sortis",                      "Risk-of-default component."),
        ("λ",       "Lucrum cessans",                        "Opportunity-cost claim; morally the most suspect component."),
        ("U",       "Usury-pressure index",                  "Extractive moral pressure from ρ and λ."),
        ("T",       "Theological integrity",                 "Summary measure of moral acceptability."),
        ("T_min",   "Minimum theological threshold",         "Lower bound for theological viability."),
        ("η",       "Reinvestment ratio",                    "Fraction of returns recycled into new productive activity."),
        ("μ",       "Reinvestment-weight parameter",         "How strongly reinvestment raises theological integrity."),
        ("M_licit", "Licit component of the multiple",       "Portion mainly attributable to principal, real expenses, bounded penalty."),
        ("M_usury", "Usury-linked component of the multiple","Portion attributable to risk-pricing and opportunity-cost claims."),
        ("α",       "Lifetime sensitivity to U",             "Governs how quickly L(U) falls as U rises."),
        ("β",       "Openness sensitivity to U",             "Governs how quickly o(U) falls as U rises."),
        ("γ",       "Sovereignty sensitivity to U",          "Governs how quickly d(U) falls as U rises."),
        ("P",       "Moral viability region",                "Set of designs satisfying finance, impact, and moral constraints."),
    ],
    columns=["Variable", "Meaning", "Role in the model"],
)


SIMULATOR_GLOSSARY = pd.DataFrame(
    [
        ("N_t",         "Team size at time t",                                "Headcount input."),
        ("W_t",         "Average annual salary per FTE",                      "Drives payroll cost."),
        ("O_t",         "Non-payroll operating expense",                      "Other operational outflow."),
        ("R_t",         "Annual revenue",                                     "Main inflow."),
        ("C_t",         "Cash available",                                     "Tracked across years."),
        ("I_t",         "Capital injected by the fund in period t",           "DSF deployment into the company."),
        ("B_t",         "Monthly burn rate",                                  "(CashOpex - Revenue) / 12."),
        ("Q_t",         "Product maturity / implementation readiness",        "Soft state variable."),
        ("P_t",         "Procurement access / sales capacity",                "Soft state variable."),
        ("A_t",         "Adoption traction",                                  "Mission-relevant soft state."),
        ("κ",           "Company-level redemption multiple",                  "Sets cap Ω = κ·ΣI."),
        ("Ω",           "Maximum cumulative company redemption obligation",   "Hard ceiling on company-to-fund cash."),
        ("Red_{i,t}",   "Actual redemption paid by company i in period t",    "Output of the trigger × clamp."),
        ("CumRed_{i,t}","Cumulative redemption already paid",                 "Compared against Ω."),
        ("L★",          "Minimum resilience reserve",                         "Floor under which redemption cannot occur."),
        ("ResGap",      "Cash needed to refill resilience reserve",           "First call on FCF."),
        ("DistCash",    "Cash available after the resilience layer",          "Splits into Reinvest vs RedBase."),
        ("γ",           "Internal reinvestment share at company level",       "γ_early before switch year, γ_late after."),
        ("Π_t",         "Aggregate company-to-fund redemption inflow",        "Σ_i Red_{i,t}."),
        ("E_t",         "Evergreen pot at start of period t",                 "Compounding engine balance."),
        ("E★",          "Minimum evergreen target",                           "Reinvestment floor."),
        ("DistPool",    "Member-level distributable pool",                    "Avail − ReinvestFund."),
        ("K_{m,v}",     "Contributed capital for member m, vintage v",        "Sets cap K·r."),
        ("u_{m,v}",     "Participation units",                                "Pro-rata weight in distribution."),
        ("r_{m,v}",     "Cap multiple for vintage (m,v)",                     "Default 3."),
        ("CumDist_{m,v}","Cumulative distributions paid",                     "Vintage exits when CumDist = r·K."),
        ("DS_NPV",      "NPV-loan debt service",                              "Sits ahead of member distributions."),
    ],
    columns=["Variable", "Meaning", "Role in the model"],
)
