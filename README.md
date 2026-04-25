# Digital Sovereignty Fund — Unified Model + Portfolio Simulator

A Streamlit app implementing the DSF unified financial / impact / theological
model and a portfolio-company operating simulator. Rebuilt from:

- `dsf_unified_model_consolidated_v258` — closed-form `M`, `I`, `T`, evergreen
  compounding, VC benchmark.
- `dsf_portfolio_simulation_framework_v41` — year-by-year company simulator,
  three-layer waterfall, cooperative waterfall and capped per-vintage payouts.

## Tabs

1. **Unified Model** — sliders for `r = 1+δ+π+ρ+λ`, `p`, `k`, `c`, `N`, the
   coupling parameters and the impact / theology factors. Live readouts of
   `M`, `M_licit`, `M_usury`, `T`, `I`. Five-scenario comparison from §5.4.
   Evergreen vs VC benchmark, M(p,k) heatmap.
2. **Company Simulator** — editable per-stage operating profile. Reproduces
   the §12 worked example (Y3 redemption ≈ €49k, Y4 ≈ €213k).
3. **Cooperative Waterfall** — `Π → Net → Reinvest vs DistPool`, per-vintage
   capped pro-rata distribution with NPV-loan priority. Pulls simulator
   output via `st.session_state`.
4. **Glossary** — searchable variable legend.

## Running locally

```
pip install -r requirements.txt
streamlit run app.py
```

## Tests

```
pytest tests/ -v
```

21 unit tests anchor the math against PDF reference values (§2.12 benchmark
table, §5.4 scenario table, §12 worked redemption schedule, §11 vintage cap
clamping, §15.6 NPV-loan priority).

## Repo layout

```
app.py              Streamlit UI (only file that imports streamlit)
dsf/                Pure NumPy/pandas math layer
  financial.py      M, M_total, VC benchmark, stewardship path
  impact.py         I, coupling, scenario table
  theology.py       r-decomposition, U, T
  simulator.py      Year-by-year company engine
  waterfall.py      Cooperative waterfall + per-vintage capped pro-rata
  glossary.py       Variable legend tables
tests/test_dsf.py   pytest unit tests
PLAN.md             Implementation plan
.replit, replit.nix Replit run config
```
