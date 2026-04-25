# DSF Unified Model + Portfolio Simulator — Implementation Plan

## Context

Rebuild the webapp at `https://unified-model-sim--mrieback.replit.app/` from
the two source PDFs:

1. `dsf_unified_model_consolidated_v258` — financial / impact / theological
   model (closed-form equations).
2. `dsf_portfolio_simulation_framework_v41` — company-level operating
   simulation, cash-flow waterfall, cooperative waterfall, and minimum-viable
   launch structure.

The live Replit app is unreachable from this sandbox (HTTP 403 on every URL),
so the rebuild is from the PDFs alone. Stack: **Python + Streamlit**.

## File layout

```
/home/user/NEC/
├── app.py                  Streamlit entrypoint (UI only)
├── requirements.txt
├── .replit
├── replit.nix
├── README.md               Minimal run instructions
├── dsf/
│   ├── __init__.py
│   ├── financial.py        M, M_total, VC benchmark, stewardship path
│   ├── impact.py           Coupling L/o/d, impact I, scenario table
│   ├── theology.py         r decomposition, U, T
│   ├── simulator.py        Year-by-year company simulator
│   ├── waterfall.py        Cooperative waterfall + per-vintage capped pro-rata
│   └── glossary.py         Static glossary tables
└── tests/
    └── test_dsf.py         pytest unit tests
```

Hard rule: no Streamlit imports under `dsf/` — pure NumPy/pandas so tests run
headlessly.

## Equations

### Unified model (PDF 1)
- `r = 1 + δ + π + ρ + λ`
- `U = 0.5·ρ + λ`
- `M = r·k·p / (1 + (k-1)·p)`
- `M_licit = (1+δ+π)·k·p / (1+(k-1)·p)`,  `M_usury = (ρ+λ)·k·p / (1+(k-1)·p)`
- `L(U)=L0(1-αU)`,  `o(U)=o0(1-βU)`,  `d(U)=d0(1-γU)`
- `I = N·p·L(U)·o(U)·d(U)·a·e`
- `T = 1 - U + μ·η`
- `M_total = M^c`,  `W_{t+1}=η·W_t·M`
- VC benchmark: `(1.05)^(10c)`
- Tri-objective: `max I  s.t. F ≥ F_min, T ≥ T_min`

### Portfolio simulator (PDF 2)
For each year:
1. Payroll = N·W; CashOpex = Payroll + O
2. EBITDA = R − CashOpex; EBIT = EBITDA − D; Tax = τ·max(0, EBIT)
3. FCF = EBITDA − Tax − Capex − ΔNWC
4. L★ = max(L_min, ρ·CashOpex/12)
5. ResGap = max(0, L★ − (C_pre + FCF))
6. DistCash = max(0, FCF − ResGap)
7. γ = γ_early if t < gamma_switch_year else γ_late
8. Reinvest = γ·DistCash; RedBase = (1−γ)·DistCash
9. Ω = κ · ΣI_τ
10. Trigger = (EBITDA>0) AND (DistCash>0) AND (CumRed<Ω)
11. Red = Trigger · min(RedBase, Ω − CumRed)

### Cooperative waterfall (PDF 2 §11)
- `Π_t = Σ_i Red_{i,t}`
- `NetProceeds = max(0, Gross − CoopOpex − Tax − Liab − DS_NPV)`
- `Avail = max(0, Net − ReserveAlloc)`
- `Reinvest = min(Avail, max(η·Avail, E★ − E_t))`
- `DistPool = Avail − Reinvest`
- Per-vintage iterative pro-rata: provisional `(u/Σu_live)·DistPool`, clamp to
  cap headroom `H = r·K − CumDist`, redistribute residual.

## Streamlit UI — single-file `app.py` with 4 tabs

| Tab | Purpose |
|-----|---------|
| Unified Model | Sliders for r-decomposition, p, k, c, N, L0/α, o0/β, d0/γ, a, e, μ, η. Metrics for r, U, M, M_licit, M_usury, T, I. Stacked bar of A–E scenarios. M_total vs cycles with VC PASS/FAIL. M(p,k) heatmap. Stewardship path. |
| Company Simulator | `st.data_editor` for per-stage inputs (Day1, Y1–Y4). Computes year-by-year table including Red. Validation banner asserts Y3=€49k, Y4=€213k. |
| Cooperative Waterfall | Vintages, NPV loan service, reserve, evergreen pot. Sankey for one focal year. Pulls simulator output via `st.session_state['simulator_redemptions']`. |
| Glossary | Searchable variable legend (Financial / Impact / Theology / Simulator). |

## Defaults

- Tab 1 reproduces PDF §5.4 row C "Mixed": δ=0.90, π=0.20, ρ=0.50, λ=0.30 →
  r=2.90, U=0.55, M=2.49 (k=5, p=0.40), Impact ≈ 351.
- Tab 2 reproduces PDF §12 worked example: teams 3/5/8/12/18, revenue
  40/180/520/1550/2700 (€k), DSF in 0/400/350/0/0, κ=2, τ=25%, γ_late=0.6 from
  year 3+ → Red 0/0/0/49/213.
- Tab 3 reproduces PDF §15.5 launch budget: 2 members at €100k, NPV loan
  €300k, Coop setup €15k, Stichting €10k, Golden share €5k, E★_0=€50k.

## State management

Single `st.session_state` dict; cross-tab handoff via
`simulator_redemptions` key. `@st.cache_data` decorates pure functions in
`dsf.*`.

## Dependencies (`requirements.txt`)

```
streamlit==1.39.0
pandas==2.2.3
numpy==2.1.2
plotly==5.24.1
pytest==8.3.3
```

## Replit config

`.replit`:
```
run = "streamlit run app.py --server.port 8080 --server.address 0.0.0.0 --server.headless true"
entrypoint = "app.py"

[nix]
channel = "stable-23_11"
```

`replit.nix`:
```
{ pkgs }: { deps = [ pkgs.python311 pkgs.python311Packages.pip ]; }
```

## Tests (`tests/test_dsf.py`)

1. `test_M_table_2_12` — k=5, r=3, asserts §2.12 PDF table for p∈{.10,.20,.40,.60} × c∈{1,2,3} (12 cells, ±0.02).
2. `test_scenario_table_5_4` — five rows A–E with r=2.90, M=2.49 (±0.005), U/L(U)/o(U)/d(U) per PDF, impact ratios within 2%.
3. `test_simulator_§12_redemption` — runs worked example, asserts Y3 Red≈€49k, Y4 Red≈€213k, EBITDA flips at Y3, tax matches.
4. `test_waterfall_pro_rata_cap` — synthetic two-vintage cap clamping with residual redistribution.
5. `test_waterfall_npv_priority` — DistPool=0 while E_t<E★ or NPV_DS_t unfunded.
6. `test_evergreen_benchmark` — for r=3, k=5, p=0.40, c=10: M_total=2.31^10>VC benchmark (1.05)^100 → PASS.

Run: `pytest tests/ -v`.

## Verification

1. `pip install -r requirements.txt` succeeds.
2. `pytest tests/ -v` — all 6 tests pass.
3. `streamlit run app.py` — opens at localhost:8501 with no console errors.
4. Tab 1 default metrics: r=2.90, U=0.55, M=2.49, I≈351.
5. Tab 2 default Red column: 0/0/0/49/213 (€k). Validation banner green.
6. Tab 3 default: NPV-DS prioritised before any member distribution; E_t
   tracks toward E★ first.
7. Tab 4 glossary searchable; "η" filters to ≥2 rows.
