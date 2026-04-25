"""Unit tests anchoring the math against PDF reference values."""
from __future__ import annotations

import math

import pandas as pd
import pytest

from dsf import financial, impact, theology
from dsf.simulator import simulate_company, worked_example_section_12
from dsf.waterfall import (
    Vintage,
    WaterfallParams,
    fund_waterfall,
    pro_rata_capped,
)


# -----------------------------------------------------------------------------
# Test 1 — PDF 1 §2.12 evergreen benchmark table for k=5, r=3
# -----------------------------------------------------------------------------

# PDF prints the table to 2-3 decimals with some rounding. The closed-form
# formula M = r·k·p/(1+(k-1)·p) is the source of truth; the PDF rows below
# match within ±0.1 except p=0.10 which has a printing inconsistency in the
# PDF (formula gives 1.07 not 1.15).
PDF_212_TABLE = {
    (0.20, 1): 1.67, (0.40, 1): 2.31, (0.60, 1): 2.65,
    (0.20, 2): 2.78, (0.40, 2): 5.34, (0.60, 2): 7.02,
    (0.20, 3): 4.64, (0.40, 3): 12.30, (0.60, 3): 18.55,
}


@pytest.mark.parametrize("p,c,expected", [(p, c, v) for (p, c), v in PDF_212_TABLE.items()])
def test_M_total_matches_212(p, c, expected):
    M = financial.single_cycle_multiple(k=5, p=p, r=3)
    Mt = financial.evergreen_multiple(M, c)
    assert math.isclose(Mt, expected, abs_tol=0.1), (
        f"p={p}, c={c}: got {Mt:.3f}, expected {expected}"
    )


def test_pass_fail_212():
    """PDF §2.12 PASS/FAIL: low p=0.10 fails across c=1..3, p≥0.20 passes."""
    df = financial.benchmark_table(k=5, r=3, ps=[0.10, 0.20, 0.40, 0.60], cs=[1, 2, 3])
    fail_rows = df[df["result"] == "FAIL"]
    pass_rows = df[df["result"] == "PASS"]
    assert set(fail_rows["p"].unique()) == {0.10}
    assert set(pass_rows["p"].unique()) == {0.20, 0.40, 0.60}


# -----------------------------------------------------------------------------
# Test 2 — PDF 1 §5.4 scenario table: same r=2.90, M=2.49, varying impact
# -----------------------------------------------------------------------------

# Expected (U, L(U), o(U), d(U)) per PDF lines 2032-2065.
SCENARIO_EXPECTED = {
    "A. Strongly licit":   (0.05, 7.92, 0.9925, 0.99),
    "B. Mostly licit":     (0.25, 7.60, 0.9625, 0.95),
    "C. Mixed":            (0.55, 7.12, 0.9175, 0.89),
    "D. Extractive drift": (0.85, 6.64, 0.8725, 0.83),
    "E. Highly usurious":  (1.10, 6.24, 0.8350, 0.78),
}


def test_scenario_table_5_4():
    df = impact.scenario_table()
    # PDF §5.4 says r=2.90 and M=2.49 for every scenario. The closed form
    # for k=5, p=0.60, r=2.90 gives M=2.559 (PDF prints 2.49 — minor PDF
    # internal inconsistency). We assert M is constant across rows and within
    # 0.1 of the printed value.
    Ms = df["M"].tolist()
    assert max(Ms) - min(Ms) < 1e-6, f"M not constant across scenarios: {Ms}"
    assert all(math.isclose(M, 2.49, abs_tol=0.1) for M in Ms), Ms
    for name, (U_exp, L_exp, o_exp, d_exp) in SCENARIO_EXPECTED.items():
        row = df[df["Scenario"] == name].iloc[0]
        assert math.isclose(row["r"], 2.90, abs_tol=0.005), f"{name}: r={row['r']}"
        assert math.isclose(row["U"], U_exp, abs_tol=0.005), f"{name}: U"
        assert math.isclose(row["L(U)"], L_exp, abs_tol=0.05), f"{name}: L(U)"
        assert math.isclose(row["o(U)"], o_exp, abs_tol=0.005), f"{name}: o(U)"
        assert math.isclose(row["d(U)"], d_exp, abs_tol=0.01), f"{name}: d(U)"


def test_scenario_impact_strictly_decreasing():
    """Impact strictly decreases A → E (PDF approximate ratios 451/417/351/289/244)."""
    df = impact.scenario_table().reset_index(drop=True)
    impacts = df["Impact"].tolist()
    for prev, nxt in zip(impacts, impacts[1:]):
        assert prev > nxt, f"Impact not strictly decreasing: {impacts}"


# -----------------------------------------------------------------------------
# Test 3 — PDF 2 §12 worked example: redemption schedule
# -----------------------------------------------------------------------------

def test_simulator_pdf12_redemption():
    params, stages = worked_example_section_12()
    df = simulate_company(params, stages)

    # EBITDA flips at Y3.
    assert (df["EBITDA"].iloc[:3] < 0).all()
    assert df["EBITDA"].iloc[3] > 0
    assert df["EBITDA"].iloc[4] > 0

    # Tax matches PDF Y3=85k, Y4=224k (within €1k).
    assert math.isclose(df["Tax"].iloc[3], 85_000, abs_tol=1_000)
    assert math.isclose(df["Tax"].iloc[4], 224_000, abs_tol=1_000)

    # Redemption matches PDF: 0/0/0/49/213 (€k). PDF rounds to €k.
    assert df["Red"].iloc[0] == 0
    assert df["Red"].iloc[1] == 0
    assert df["Red"].iloc[2] == 0
    assert math.isclose(df["Red"].iloc[3], 49_000, abs_tol=2_000)
    assert math.isclose(df["Red"].iloc[4], 213_000, abs_tol=3_000)

    # Cumulative DSF in by Y2 = €750k → Ω = 1.5m.
    assert df["CumInvest"].iloc[2] == 750_000
    assert df["Omega"].iloc[2] == 1_500_000


def test_simulator_omega_cap_binds():
    """If we crank κ down, the Ω cap should clamp redemption."""
    params, stages = worked_example_section_12()
    params.kappa = 0.05  # Ω = €37.5k by Y2
    df = simulate_company(params, stages)
    cum = df["CumRed"].iloc[-1]
    assert cum <= params.kappa * 750_000 + 1.0, (
        f"Cumulative redemption {cum} exceeded Ω cap"
    )


# -----------------------------------------------------------------------------
# Test 4 — Cooperative waterfall: per-vintage capped pro-rata
# -----------------------------------------------------------------------------

def test_pro_rata_uniform_split():
    vs = [
        Vintage(vintage_id="A", year=0, K=100_000, units=1.0, r_cap=3.0),
        Vintage(vintage_id="B", year=0, K=100_000, units=1.0, r_cap=3.0),
    ]
    payouts = pro_rata_capped(500_000, vs)
    assert math.isclose(payouts["A"], 250_000, abs_tol=1)
    assert math.isclose(payouts["B"], 250_000, abs_tol=1)


def test_pro_rata_clamps_and_redistributes():
    """One vintage near its cap clamps; residual flows to the other."""
    vs = [
        Vintage(vintage_id="A", year=0, K=100_000, units=1.0, r_cap=3.0, cum_dist=280_000),
        Vintage(vintage_id="B", year=0, K=100_000, units=1.0, r_cap=3.0, cum_dist=0),
    ]
    # A has €20k headroom, B has €300k. Pool €500k → A gets 20, B gets 300, residual 180 unallocated.
    payouts = pro_rata_capped(500_000, vs)
    assert math.isclose(payouts["A"], 20_000, abs_tol=1)
    assert math.isclose(payouts["B"], 300_000, abs_tol=1)


def test_pro_rata_zero_pool():
    vs = [Vintage(vintage_id="A", year=0, K=100_000, units=1.0)]
    assert pro_rata_capped(0, vs)["A"] == 0


# -----------------------------------------------------------------------------
# Test 5 — Cooperative waterfall: NPV / E★ priority over member distribution
# -----------------------------------------------------------------------------

def test_waterfall_holds_back_until_estar_restored():
    """If E_t is below E★ entering year t, no DistPool is paid out."""
    vs = [Vintage(vintage_id="A", year=0, K=100_000, units=1.0, r_cap=3.0)]
    params = WaterfallParams(
        eta_early=0.50,
        eta_late=0.50,
        eta_switch_year=4,
        E_star=200_000.0,
        E0=0.0,
        coop_opex_schedule=[0.0] * 5,
        npv_ds_schedule=[0.0] * 5,
        new_deploy_schedule=[0.0] * 5,
        reserve_alloc_schedule=[0.0] * 5,
        formation_costs_y0=0.0,
        horizon=5,
    )
    redemptions = pd.Series({0: 100_000, 1: 100_000, 2: 100_000, 3: 100_000, 4: 100_000})
    df = fund_waterfall(redemptions, vs, params)
    # First two years should have zero DistPool because E < E★.
    assert df["DistPool"].iloc[0] == 0
    assert df["DistPool"].iloc[1] == 0


def test_waterfall_npv_priority():
    """NPV debt service is deducted in NetProceeds before DistPool."""
    vs = [Vintage(vintage_id="A", year=0, K=100_000, units=1.0, r_cap=3.0)]
    params = WaterfallParams(
        eta_early=0.0,
        eta_late=0.0,
        eta_switch_year=4,
        E_star=0.0,
        E0=0.0,
        coop_opex_schedule=[0.0] * 5,
        npv_ds_schedule=[40_000] * 5,
        new_deploy_schedule=[0.0] * 5,
        reserve_alloc_schedule=[0.0] * 5,
        formation_costs_y0=0.0,
        horizon=5,
    )
    redemptions = pd.Series({0: 50_000, 1: 50_000, 2: 50_000, 3: 50_000, 4: 50_000})
    df = fund_waterfall(redemptions, vs, params)
    # Each year: gross 50, DS_NPV 40, net 10, all flows to dist (η=0).
    assert (df["DSNPV"] == 40_000).all()
    assert (df["Net"] == 10_000).all()
    assert (df["DistPool"] == 10_000).all()


# -----------------------------------------------------------------------------
# Test 6 — Evergreen vs VC benchmark over many cycles
# -----------------------------------------------------------------------------

def test_evergreen_beats_vc_for_strong_p():
    """For r=3, k=5, p=0.4, c=10: M_total ≈ 2.31^10 should beat (1.05)^100."""
    M = financial.single_cycle_multiple(k=5, p=0.4, r=3)
    Mt = financial.evergreen_multiple(M, 10)
    vc = financial.vc_benchmark(10)
    assert Mt > vc, f"M_total={Mt:.1f}, vc={vc:.1f}"


def test_repayment_cap_decomposition():
    r = financial.repayment_cap(0.90, 0.20, 0.50, 0.30)
    assert math.isclose(r, 2.90, abs_tol=1e-9)
    U = theology.usury_pressure(0.50, 0.30)
    assert math.isclose(U, 0.55, abs_tol=1e-9)
    T = theology.theological_integrity(U, mu=0.5, eta=0.6)
    assert math.isclose(T, 1 - 0.55 + 0.5 * 0.6, abs_tol=1e-9)
