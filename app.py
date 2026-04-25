"""Digital Sovereignty Fund — Unified Model + Portfolio Simulator.

Streamlit single-page app with four tabs:
  1. Unified Model        — closed-form M, I, T, evergreen, VC benchmark.
  2. Company Simulator    — year-by-year operating engine (PDF 2 §4–§12).
  3. Cooperative Waterfall — Π → Net → Reinvest vs DistPool, vintage payouts.
  4. Glossary             — variable legend.

All math lives in `dsf/` so this file is UI-only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dsf import financial, glossary, impact, theology
from dsf.simulator import (
    CompanyParams,
    StageInputs,
    simulate_company,
    worked_example_section_12,
)
from dsf.waterfall import (
    Vintage,
    WaterfallParams,
    default_launch,
    fund_waterfall,
)


# -----------------------------------------------------------------------------
# Page setup
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="DSF Unified Model",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Digital Sovereignty Fund — Unified Model")
st.caption(
    "Financial · Impact · Theological model with a portfolio-company simulator "
    "and cooperative waterfall. Source: DSF unified model v258 + portfolio "
    "simulation framework v41."
)

# -----------------------------------------------------------------------------
# Sidebar: globals
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("Display")
    show_formulas = st.checkbox("Show formula captions", value=True)
    decimals = st.number_input("Rounding decimals", min_value=0, max_value=4, value=2)
    st.divider()
    st.header("Reference")
    st.markdown(
        """
- **Financial:** `M = r·k·p / (1 + (k-1)·p)`
- **Impact:** `I = N·p·L(U)·o(U)·d(U)·a·e`
- **Theology:** `T = 1 - U + μ·η`,  `U = 0.5·ρ + λ`
- **r-decomposition:** `r = 1 + δ + π + ρ + λ`
"""
    )
    if st.button("Reset defaults", use_container_width=True):
        st.session_state.clear()
        st.rerun()


# -----------------------------------------------------------------------------
# Tabs
# -----------------------------------------------------------------------------
tab_model, tab_sim, tab_waterfall, tab_glossary = st.tabs(
    ["Unified Model", "Company Simulator", "Cooperative Waterfall", "Glossary"]
)


# =============================================================================
# Tab 1 — Unified Model
# =============================================================================
with tab_model:
    st.subheader("Unified closed-form model")

    left, right = st.columns([1, 1])

    with left:
        st.markdown("**Repayment cap (Thomistic decomposition)**")
        delta = st.slider("δ — damnum emergens (real expenses)", 0.0, 3.0, 0.90, 0.05)
        pi_ = st.slider("π — poena conventionalis (bounded penalty)", 0.0, 1.0, 0.20, 0.05)
        rho = st.slider("ρ — periculum sortis (default risk)", 0.0, 1.5, 0.50, 0.05)
        lam = st.slider("λ — lucrum cessans (opportunity-cost claim)", 0.0, 1.5, 0.30, 0.05)

        st.markdown("**Portfolio**")
        k = st.slider("k — capital concentration", 1.0, 15.0, 5.0, 0.5)
        p = st.slider("p — survival probability", 0.05, 1.0, 0.60, 0.05)
        c = st.slider("c — evergreen cycles", 1, 10, 1)
        N = st.slider("N — companies funded", 1, 200, 40)

    with right:
        st.markdown("**Coupling: how usury pressure erodes durability**")
        L0 = st.slider("L₀ — baseline lifetime (yrs)", 1.0, 20.0, 8.0, 0.5)
        alpha = st.slider("α — lifetime sensitivity to U", 0.0, 1.0, 0.20, 0.01)
        o0 = st.slider("o₀ — baseline openness", 0.0, 1.5, 1.0, 0.05)
        beta = st.slider("β — openness sensitivity to U", 0.0, 1.0, 0.15, 0.01)
        d0 = st.slider("d₀ — baseline sovereignty retention", 0.0, 1.5, 1.0, 0.05)
        gamma_couple = st.slider("γ — sovereignty sensitivity to U", 0.0, 1.0, 0.20, 0.01)
        a = st.slider("a — adoption", 0.0, 5.0, 2.0, 0.1)
        e = st.slider("e — ecosystem spillover multiplier", 0.0, 5.0, 1.2, 0.1)
        mu = st.slider("μ — reinvestment weight in T", 0.0, 2.0, 0.5, 0.05)
        eta = st.slider("η — reinvestment ratio", 0.0, 1.0, 0.6, 0.05)

    # Computed metrics ---------------------------------------------------------
    r = financial.repayment_cap(delta, pi_, rho, lam)
    U = theology.usury_pressure(rho, lam)
    M = financial.single_cycle_multiple(k, p, r)
    M_lic = financial.licit_multiple(k, p, delta, pi_)
    M_us = financial.usury_multiple(k, p, rho, lam)
    M_total = financial.evergreen_multiple(M, c)
    vc = financial.vc_benchmark(c)
    T = theology.theological_integrity(U, mu, eta)
    I = impact.impact(N, p, L0, o0, d0, alpha, beta, gamma_couple, a, e, U)

    st.divider()
    st.markdown("### Outputs")
    cols = st.columns(7)
    cols[0].metric("r (cap)", f"{r:.{decimals}f}")
    cols[1].metric("U (usury)", f"{U:.{decimals}f}")
    cols[2].metric("M", f"{M:.{decimals}f}×")
    cols[3].metric("M_licit", f"{M_lic:.{decimals}f}×")
    cols[4].metric("M_usury", f"{M_us:.{decimals}f}×")
    cols[5].metric("T (theology)", f"{T:.{decimals}f}")
    cols[6].metric("I (impact)", f"{I:,.0f}")

    st.markdown("### Evergreen vs VC benchmark")
    cs = list(range(1, 11))
    Mtots = [financial.evergreen_multiple(M, ci) for ci in cs]
    vcs = [financial.vc_benchmark(ci) for ci in cs]
    fig_evergreen = go.Figure()
    fig_evergreen.add_trace(go.Scatter(x=cs, y=Mtots, mode="lines+markers", name="M_total = Mᶜ"))
    fig_evergreen.add_trace(go.Scatter(x=cs, y=vcs, mode="lines", name="(1.05)^(10c) VC benchmark", line=dict(dash="dash")))
    fig_evergreen.update_layout(
        height=320,
        xaxis_title="Cycles c",
        yaxis_title="Cumulative multiple",
        yaxis_type="log",
        legend=dict(orientation="h", y=1.15),
        margin=dict(l=20, r=20, t=40, b=20),
    )
    st.plotly_chart(fig_evergreen, use_container_width=True)
    pass_state = "PASS ✅" if M_total > vc else "FAIL ❌"
    st.caption(
        f"At c={c}: M_total = {M_total:.2f}× vs VC benchmark {vc:.2f}× → **{pass_state}**"
    )

    st.markdown("### Five-scenario comparison (PDF §5.4)")
    scen = impact.scenario_table(
        N=N, p=p, k=k, L0=L0, o0=o0, d0=d0,
        alpha=alpha, beta=beta, gamma=gamma_couple, a=a, e=e, mu=mu, eta=eta,
    )
    if show_formulas:
        st.caption(
            "Same nominal r and M for all five rows — but the moral composition "
            "(δ, π, ρ, λ) varies, and so does the impact through L(U), o(U), d(U)."
        )
    st.dataframe(scen, use_container_width=True, hide_index=True)

    fig_lic = go.Figure()
    fig_lic.add_trace(go.Bar(name="M_licit", x=scen["Scenario"], y=scen["M_licit"], marker_color="#2E7D32"))
    fig_lic.add_trace(go.Bar(name="M_usury", x=scen["Scenario"], y=scen["M_usury"], marker_color="#C62828"))
    fig_lic.update_layout(
        barmode="stack",
        height=320,
        title="Licit vs usury composition of M (same total, different morality)",
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(fig_lic, use_container_width=True)

    fig_imp = go.Figure(
        data=go.Bar(x=scen["Scenario"], y=scen["Impact"], marker_color="#1565C0")
    )
    fig_imp.update_layout(
        height=300,
        title="Impact I across the five scenarios",
        yaxis_title="I = N·p·L(U)·o(U)·d(U)·a·e",
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(fig_imp, use_container_width=True)

    st.markdown("### M(p, k) heatmap at current r")
    ps_grid = np.linspace(0.05, 1.0, 20).round(3)
    ks_grid = np.linspace(1, 15, 15).round(2)
    Hm = financial.heatmap_M(ps_grid, ks_grid, r)
    fig_heat = go.Figure(
        data=go.Heatmap(
            z=Hm.values,
            x=ks_grid,
            y=ps_grid,
            colorscale="Viridis",
            colorbar=dict(title="M"),
        )
    )
    fig_heat.update_layout(
        height=380,
        xaxis_title="k",
        yaxis_title="p",
        title=f"M(p, k) for r = {r:.2f}",
        margin=dict(l=20, r=20, t=50, b=20),
    )
    fig_heat.add_trace(
        go.Scatter(x=[k], y=[p], mode="markers", marker=dict(size=14, color="white", line=dict(color="black", width=2)), name="current")
    )
    st.plotly_chart(fig_heat, use_container_width=True)


# =============================================================================
# Tab 2 — Company Simulator
# =============================================================================
with tab_sim:
    st.subheader("Portfolio-company simulator (PDF 2 §4–§12)")
    st.caption(
        "Year-by-year operating engine. Defaults reproduce the §12 worked example: "
        "Y3 redemption ≈ €49k, Y4 ≈ €213k."
    )

    default_params, default_stages = worked_example_section_12()

    # Editable parameter block ------------------------------------------------
    cparam_cols = st.columns(4)
    kappa = cparam_cols[0].number_input(
        "κ — company redemption multiple", 0.5, 5.0, default_params.kappa, 0.1
    )
    tau = cparam_cols[1].number_input("τ — tax rate", 0.0, 0.5, default_params.tau, 0.01)
    gamma_late = cparam_cols[2].number_input(
        "γ_late — reinvest share (year ≥ switch)", 0.0, 1.0, default_params.gamma_late, 0.05
    )
    gamma_switch = cparam_cols[3].number_input(
        "γ switch year", 1, 5, default_params.gamma_switch_year
    )

    cparam_cols2 = st.columns(4)
    L_min = cparam_cols2[0].number_input(
        "L_min (€) — reserve floor", 0, 1_000_000, int(default_params.L_min), 10_000
    )
    rho_months = cparam_cols2[1].number_input(
        "ρ — reserve months of CashOpex", 0.0, 12.0, default_params.rho_reserve_months, 0.5
    )
    C0 = cparam_cols2[2].number_input("C₀ (€) — opening cash", 0, 5_000_000, int(default_params.C0), 50_000)
    gamma_early = cparam_cols2[3].number_input(
        "γ_early — reinvest share (year < switch)", 0.0, 1.0, default_params.gamma_early, 0.05
    )

    # Editable per-stage table ------------------------------------------------
    st.markdown("**Per-stage operating inputs** (€)")
    rows = []
    for s in default_stages:
        rows.append(
            {
                "Stage": ["Day 1", "Y1", "Y2", "Y3", "Y4"][s.year] if s.year < 5 else f"Y{s.year}",
                "Year": s.year,
                "Team": s.team,
                "Wage_per_FTE": s.wage_per_fte,
                "Revenue": s.revenue,
                "OtherOpex": s.other_opex,
                "Capex": s.capex,
                "dWC": s.delta_wc,
                "DSF_in": s.dsf_in,
                "Depreciation": s.depreciation,
                "force_ResGap": s.force_res_gap if s.force_res_gap is not None else float("nan"),
            }
        )
    edited = st.data_editor(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "Stage": st.column_config.TextColumn(disabled=True),
            "Year": st.column_config.NumberColumn(disabled=True),
        },
    )

    # Build params + stages from edited inputs --------------------------------
    params = CompanyParams(
        kappa=float(kappa),
        gamma_early=float(gamma_early),
        gamma_late=float(gamma_late),
        gamma_switch_year=int(gamma_switch),
        tau=float(tau),
        L_min=float(L_min),
        rho_reserve_months=float(rho_months),
        C0=float(C0),
    )
    stages: list[StageInputs] = []
    for _, row in edited.iterrows():
        frg = row["force_ResGap"]
        stages.append(
            StageInputs(
                year=int(row["Year"]),
                team=float(row["Team"]),
                wage_per_fte=float(row["Wage_per_FTE"]),
                revenue=float(row["Revenue"]),
                other_opex=float(row["OtherOpex"]),
                capex=float(row["Capex"]),
                delta_wc=float(row["dWC"]),
                dsf_in=float(row["DSF_in"]),
                depreciation=float(row["Depreciation"]),
                force_res_gap=None if pd.isna(frg) else float(frg),
            )
        )

    sim_df = simulate_company(params, stages)
    st.session_state["simulator_redemptions"] = sim_df.set_index("Year")["Red"]

    # KPI strip ---------------------------------------------------------------
    cum_red = sim_df["CumRed"].iloc[-1]
    cum_invest = sim_df["CumInvest"].iloc[-1]
    omega_final = sim_df["Omega"].iloc[-1]
    first_trigger = sim_df.loc[sim_df["Trigger"] == 1, "Year"]
    first_trigger_year = int(first_trigger.iloc[0]) if not first_trigger.empty else None

    kpi_cols = st.columns(4)
    kpi_cols[0].metric("Cumulative DSF in", f"€{cum_invest:,.0f}")
    kpi_cols[1].metric("Cumulative redemption", f"€{cum_red:,.0f}")
    kpi_cols[2].metric("Ω cap (κ·ΣI)", f"€{omega_final:,.0f}")
    kpi_cols[3].metric("First trigger year", str(first_trigger_year) if first_trigger_year is not None else "—")

    # Validation banner ------------------------------------------------------
    y3_red = sim_df.loc[sim_df["Year"] == 3, "Red"]
    y4_red = sim_df.loc[sim_df["Year"] == 4, "Red"]
    y3_ok = (not y3_red.empty) and abs(y3_red.iloc[0] - 49_000) < 2_000
    y4_ok = (not y4_red.empty) and abs(y4_red.iloc[0] - 213_000) < 3_000
    if y3_ok and y4_ok:
        st.success("✓ Reproduces PDF §12 worked example: Y3 ≈ €49k, Y4 ≈ €213k.")
    else:
        y3v = float(y3_red.iloc[0]) if not y3_red.empty else 0
        y4v = float(y4_red.iloc[0]) if not y4_red.empty else 0
        st.info(
            f"Custom inputs: Y3 redemption €{y3v:,.0f}, Y4 €{y4v:,.0f}. "
            f"PDF §12 reference: Y3 ≈ €49 000, Y4 ≈ €213 000."
        )

    # Year-by-year display ----------------------------------------------------
    st.markdown("### Year-by-year results (€k)")
    show = sim_df[
        ["Year", "Team", "Revenue", "CashOpex", "EBITDA", "EBIT", "Tax",
         "Capex", "dWC", "FCF", "L_star", "ResGap", "DistCash", "Reinvest",
         "RedBase", "DSF_in", "Omega", "Red", "CumRed", "Cash_close"]
    ].copy()
    money_cols = [c for c in show.columns if c not in ("Year", "Team")]
    for col in money_cols:
        show[col] = (show[col] / 1000).round(1)
    st.dataframe(show, use_container_width=True, hide_index=True)

    # Charts ------------------------------------------------------------------
    fig_cash = go.Figure()
    fig_cash.add_trace(go.Bar(name="Revenue", x=sim_df["Year"], y=sim_df["Revenue"], marker_color="#2E7D32"))
    fig_cash.add_trace(go.Bar(name="CashOpex", x=sim_df["Year"], y=sim_df["CashOpex"], marker_color="#C62828"))
    fig_cash.add_trace(go.Scatter(name="EBITDA", x=sim_df["Year"], y=sim_df["EBITDA"], mode="lines+markers", line=dict(color="#1565C0", width=3)))
    fig_cash.add_trace(go.Scatter(name="FCF", x=sim_df["Year"], y=sim_df["FCF"], mode="lines+markers", line=dict(color="#6A1B9A", dash="dot", width=3)))
    fig_cash.update_layout(
        height=360,
        barmode="group",
        title="Operating profile",
        xaxis_title="Year",
        yaxis_title="€",
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(fig_cash, use_container_width=True)

    fig_red = go.Figure()
    fig_red.add_trace(
        go.Scatter(
            x=sim_df["Year"], y=sim_df["CumRed"], mode="lines+markers",
            line=dict(color="#FF6F00", width=3, shape="hv"),
            name="Cumulative redemption",
        )
    )
    fig_red.add_trace(
        go.Scatter(
            x=sim_df["Year"], y=sim_df["Omega"], mode="lines",
            line=dict(color="#9E9E9E", dash="dash"),
            name="Ω cap",
        )
    )
    fig_red.update_layout(
        height=320,
        title="Cumulative redemption vs Ω cap",
        xaxis_title="Year",
        yaxis_title="€",
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(fig_red, use_container_width=True)


# =============================================================================
# Tab 3 — Cooperative Waterfall
# =============================================================================
with tab_waterfall:
    st.subheader("Cooperative waterfall + member vintages (PDF 2 §11, §15)")

    # Fall back to PDF §12 simulator output if user hasn't visited Tab 2 yet.
    sim_red: pd.Series | None = st.session_state.get("simulator_redemptions")
    if sim_red is None:
        params0, stages0 = worked_example_section_12()
        sim_red = simulate_company(params0, stages0).set_index("Year")["Red"]

    use_sim = st.toggle(
        "Feed simulator redemptions as Π_t (uncheck to use a manual schedule)",
        value=True,
    )

    horizon = st.slider("Horizon (years)", 5, 20, 10)

    # Member vintages ---------------------------------------------------------
    st.markdown("**Member vintages**")
    default_vintages, default_params_w = default_launch(sim_red)
    vintage_rows = [
        {"Vintage": v.vintage_id, "Year": v.year, "K (€)": v.K, "Units": v.units, "r_cap": v.r_cap, "CumDist (€)": v.cum_dist}
        for v in default_vintages
    ]
    edited_vintages = st.data_editor(
        pd.DataFrame(vintage_rows),
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
    )

    # Cooperative parameters --------------------------------------------------
    wcol1, wcol2, wcol3 = st.columns(3)
    eta_early = wcol1.number_input("η_early (years 1–3)", 0.0, 1.0, 0.80, 0.05)
    eta_late = wcol2.number_input("η_late (year ≥ switch)", 0.0, 1.0, 0.40, 0.05)
    eta_switch = wcol3.number_input("η switch year", 1, 10, 4)

    wcol4, wcol5, wcol6 = st.columns(3)
    E_star = wcol4.number_input("E★ — evergreen target (€)", 0, 5_000_000, 50_000, 10_000)
    E0 = wcol5.number_input("E₀ — opening pot (€)", 0, 10_000_000, 500_000, 50_000)
    formation = wcol6.number_input("Formation costs y0 (€)", 0, 1_000_000, 30_000, 5_000)

    wcol7, wcol8, wcol9 = st.columns(3)
    coop_opex_yr = wcol7.number_input("Coop opex / year (€)", 0, 1_000_000, 20_000, 5_000)
    coop_tax = wcol8.number_input("Coop tax rate", 0.0, 0.5, 0.0, 0.01)
    npv_ds_yr = wcol9.number_input("NPV-loan debt service / year (€)", 0, 1_000_000, 30_000, 5_000)

    # Per-year manual schedule (if not using simulator) ----------------------
    if use_sim:
        red_input = sim_red.copy()
        # extend to horizon length
        for t in range(horizon):
            red_input.setdefault(t, 0.0) if hasattr(red_input, "setdefault") else None
        red_input = pd.Series({t: float(sim_red.get(t, 0.0)) for t in range(horizon)})
    else:
        st.markdown("**Manual Π_t schedule (€)**")
        manual = st.data_editor(
            pd.DataFrame({"Year": list(range(horizon)), "Pi": [0.0] * horizon}),
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
        )
        red_input = pd.Series(manual.set_index("Year")["Pi"].values, index=manual["Year"])

    # Build vintages from edited table
    vintages = []
    for _, row in edited_vintages.iterrows():
        vintages.append(
            Vintage(
                vintage_id=str(row["Vintage"]),
                year=int(row["Year"]),
                K=float(row["K (€)"]),
                units=float(row["Units"]),
                r_cap=float(row["r_cap"]),
                cum_dist=float(row["CumDist (€)"]),
            )
        )

    wparams = WaterfallParams(
        eta_early=float(eta_early),
        eta_late=float(eta_late),
        eta_switch_year=int(eta_switch),
        E_star=float(E_star),
        E0=float(E0),
        coop_opex_schedule=[float(coop_opex_yr)] * horizon,
        coop_tax_rate=float(coop_tax),
        other_liabilities_schedule=[0.0] * horizon,
        npv_ds_schedule=[float(npv_ds_yr)] * horizon,
        new_deploy_schedule=[0.0] * horizon,
        reserve_alloc_schedule=[0.0] * horizon,
        formation_costs_y0=float(formation),
        horizon=int(horizon),
    )

    wf_df = fund_waterfall(red_input, vintages, wparams)

    # KPI strip
    total_pi = wf_df["Pi"].sum()
    total_payouts = wf_df["TotalPayout"].sum()
    final_E = wf_df["E_close"].iloc[-1]
    npv_paid = wf_df["DSNPV"].sum()
    kpi_cols = st.columns(4)
    kpi_cols[0].metric("Σ Π (companies → fund)", f"€{total_pi:,.0f}")
    kpi_cols[1].metric("Σ member payouts", f"€{total_payouts:,.0f}")
    kpi_cols[2].metric("Σ NPV debt service", f"€{npv_paid:,.0f}")
    kpi_cols[3].metric("Evergreen pot (final)", f"€{final_E:,.0f}")

    st.markdown("### Year-by-year waterfall (€k)")
    pretty_cols = [
        "Year", "Pi", "CoopOpex", "DSNPV", "Net", "Avail",
        "eta", "Reinvest", "DistPool", "E_open", "E_close", "TotalPayout",
    ]
    show_wf = wf_df[pretty_cols].copy()
    for c in show_wf.columns:
        if c not in ("Year", "eta"):
            show_wf[c] = (show_wf[c] / 1000).round(1)
    st.dataframe(show_wf, use_container_width=True, hide_index=True)

    # Per-vintage state
    pay_cols = [c for c in wf_df.columns if c.startswith("Pay[")]
    cum_cols = [c for c in wf_df.columns if c.startswith("Cum[")]
    fig_v = go.Figure()
    for c in pay_cols:
        vid = c[4:-1]
        fig_v.add_trace(go.Bar(name=f"Pay {vid}", x=wf_df["Year"], y=wf_df[c]))
    fig_v.update_layout(
        barmode="stack",
        title="Member distributions per vintage per year",
        height=320,
        xaxis_title="Year",
        yaxis_title="€",
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(fig_v, use_container_width=True)

    fig_E = go.Figure()
    fig_E.add_trace(
        go.Scatter(x=wf_df["Year"], y=wf_df["E_close"], mode="lines+markers", name="E_t (close)", line=dict(color="#2E7D32", width=3))
    )
    fig_E.add_hline(y=E_star, line=dict(color="#FF6F00", dash="dash"), annotation_text="E★ floor")
    fig_E.update_layout(
        height=300,
        title="Evergreen pot E_t over time",
        xaxis_title="Year",
        yaxis_title="€",
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(fig_E, use_container_width=True)

    # Cap-headroom table
    headroom_rows = []
    for v in vintages:
        headroom_rows.append(
            {
                "Vintage": v.vintage_id,
                "K (€)": v.K,
                "Cap K·r": v.K * v.r_cap,
                "CumDist (€)": v.cum_dist,
                "Headroom H (€)": v.headroom,
                "Status": v.status,
            }
        )
    st.markdown("### Vintage cap-headroom (end of horizon)")
    st.dataframe(pd.DataFrame(headroom_rows), use_container_width=True, hide_index=True)


# =============================================================================
# Tab 4 — Glossary
# =============================================================================
with tab_glossary:
    st.subheader("Glossary — Appendix A of both PDFs")
    search = st.text_input("Filter (substring match across all columns)", "")

    def _filter(df: pd.DataFrame) -> pd.DataFrame:
        if not search:
            return df
        mask = df.apply(
            lambda r: search.lower() in " ".join(str(v) for v in r.values).lower(), axis=1
        )
        return df[mask]

    g_tabs = st.tabs(["Financial", "Impact", "Theology", "Simulator"])
    with g_tabs[0]:
        st.dataframe(_filter(glossary.FINANCIAL_GLOSSARY), use_container_width=True, hide_index=True)
    with g_tabs[1]:
        st.dataframe(_filter(glossary.IMPACT_GLOSSARY), use_container_width=True, hide_index=True)
    with g_tabs[2]:
        st.dataframe(_filter(glossary.THEOLOGY_GLOSSARY), use_container_width=True, hide_index=True)
    with g_tabs[3]:
        st.dataframe(_filter(glossary.SIMULATOR_GLOSSARY), use_container_width=True, hide_index=True)
