"""AMR-Ward Digital Twin - Streamlit user interface.

EDUCATIONAL SIMULATION. All data are synthetic. Not clinically validated.
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

from simulation import SimConfig, WardSimulation, BOUNDS
import analytics
from analytics import METRIC_LABELS
import scenarios as sc
from scenarios import SCENARIOS, PARAM_HELP
import visualizations as viz
import reporting
from education import CHALLENGES
from about_text import METHODS_MD, LIMITATIONS_MD, EVAL_PLAN_MD, NOVELTY_MD


def writable_dir(name: str) -> Path:
    """Folder for saved scenarios / reports: next to the app if writable, else in the user's home."""
    home = Path.home() / "AMR_Ward_Digital_Twin_Data"
    bases = (home,) if getattr(sys, "frozen", False) else (APP_DIR, home)   # packaged exe: APP_DIR is temporary
    for base in bases:
        try:
            p = base / name
            p.mkdir(parents=True, exist_ok=True)
            (p / ".w").write_text("ok"); (p / ".w").unlink()
            return p
        except OSError:
            continue
    raise RuntimeError("No writable folder available")



st.set_page_config(page_title="AMR-Ward Digital Twin", page_icon="🧫", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 1.2rem;}
.sim-banner {background:#fff4e5;border-left:6px solid #E69F00;padding:.6rem .9rem;border-radius:4px;font-size:.92rem;color:#3b2a00;}
.small-note {color:#555;font-size:.85rem;}
h1, h2, h3 {font-family: 'Segoe UI', Arial, sans-serif;}
</style>""", unsafe_allow_html=True)

ss = st.session_state
WARD_KEYS = ["n_patients", "days", "seed", "contact_rate", "contact_structure", "base_transmission", "hh_efficacy",
             "pickup_prob", "selection_pressure", "abx_kill", "abx_susceptibility_boost", "avg_los",
             "import_prevalence", "import_resistant_fraction"]
PRACTICE_KEYS = ["hand_hygiene", "isolation_enabled", "isolation_compliance", "isolation_effectiveness",
                 "prescribe_rate", "inappropriate_fraction", "stewardship_compliance", "surveillance_intensity"]
ALL_KEYS = list(SimConfig().to_dict())


# ------------------------------------------------------------------ state helpers
def cfg_from_widgets() -> SimConfig:
    return SimConfig.from_dict({k: ss["w_" + k] for k in ALL_KEYS})


def push_to_widgets(cfg: SimConfig) -> None:
    for k, v in cfg.to_dict().items():
        ss["w_" + k] = v


def new_sim(cfg: SimConfig) -> None:
    ss.sim = WardSimulation(cfg)
    ss.playing = False
    ss.selected_pid = None


def init_state() -> None:
    for k, v in SimConfig().to_dict().items():
        ss.setdefault("w_" + k, v)
    ss.setdefault("preset", list(SCENARIOS)[0])
    if "sim" not in ss:
        new_sim(SimConfig())
    ss.setdefault("playing", False)
    ss.setdefault("comparison", None)
    ss.setdefault("cmp_names", ("Baseline", "Alternative"))
    ss.setdefault("sens", None)
    ss.setdefault("selected_pid", None)
    ss.setdefault("notice", None)
    if "_pending" in ss:                      # config loaded from a file / repeat button
        cfg = SimConfig.from_dict(ss.pop("_pending"))
        push_to_widgets(cfg)
        new_sim(cfg)
        if ss.pop("_pending_run", False):
            ss.sim.run()


def on_preset() -> None:
    d = SimConfig().to_dict()
    cfg_d = {k: ss["w_" + k] for k in WARD_KEYS}
    cfg_d.update({k: d[k] for k in PRACTICE_KEYS})
    cfg_d.update(SCENARIOS[ss.preset]["overrides"])
    cfg = SimConfig.from_dict({**d, **cfg_d})
    push_to_widgets(cfg)
    new_sim(cfg)


def resolve_source(label: str) -> tuple[str, SimConfig]:
    """Turn a scenario-lab choice into a full configuration (ward settings come from the sidebar)."""
    if label == "Current sidebar settings":
        return label, cfg_from_widgets()
    if label.startswith("Saved: "):
        name, cfg = sc.load_scenario(SAVE_DIR() / (label[7:] + ".json"))
        return f"Saved: {name}", cfg
    d = SimConfig().to_dict()
    d.update({k: ss["w_" + k] for k in WARD_KEYS})
    d.update(SCENARIOS[label]["overrides"])
    return label, SimConfig.from_dict(d)


_save_dir = None
def SAVE_DIR() -> Path:
    global _save_dir
    if _save_dir is None:
        _save_dir = writable_dir("data/saved_scenarios")
    return _save_dir


def REPORT_DIR() -> Path:
    return writable_dir("reports")


init_state()

# ------------------------------------------------------------------ header
st.title("🧫 AMR-Ward Digital Twin")
st.caption("Interactive simulation for teaching antimicrobial stewardship and hospital infection prevention")
st.markdown('<div class="sim-banner"><b>Everything here is simulated.</b> All patients, events, transmission outcomes and '
            'indicators come from a rule-based educational model with <i>illustrative</i> parameters on synthetic data. '
            'It is not clinically validated and must never be used for real patient care or hospital decisions.</div>',
            unsafe_allow_html=True)
if ss.notice:
    st.success(ss.notice); ss.notice = None

# ------------------------------------------------------------------ sidebar controls
sb = st.sidebar
sb.header("Intervention controls")
sb.selectbox("Scenario preset", list(SCENARIOS), key="preset", on_change=on_preset,
             help="Loads a ready-made set of practice settings. You can then adjust any slider.")
sb.caption(SCENARIOS[ss.preset]["description"])
sb.slider("Hand hygiene adherence", 0.0, 1.0, key="w_hand_hygiene", step=0.05, help=PARAM_HELP["hand_hygiene"])
sb.toggle("Isolation of detected resistant carriers", key="w_isolation_enabled", help=PARAM_HELP["isolation_enabled"])
sb.slider("Isolation compliance", 0.0, 1.0, key="w_isolation_compliance", step=0.05, help=PARAM_HELP["isolation_compliance"])
sb.slider("Isolation effectiveness", 0.0, 1.0, key="w_isolation_effectiveness", step=0.05, help=PARAM_HELP["isolation_effectiveness"])
sb.slider("Surveillance intensity", 0.0, 1.0, key="w_surveillance_intensity", step=0.05, help=PARAM_HELP["surveillance_intensity"])
sb.slider("Stewardship compliance", 0.0, 1.0, key="w_stewardship_compliance", step=0.05, help=PARAM_HELP["stewardship_compliance"])
sb.slider("Antibiotic prescribing rate (per patient-day)", 0.0, 0.5, key="w_prescribe_rate", step=0.01, help=PARAM_HELP["prescribe_rate"])
sb.slider("Share of prescribing not indicated", 0.0, 1.0, key="w_inappropriate_fraction", step=0.05, help=PARAM_HELP["inappropriate_fraction"])
sb.header("Ward set-up")
sb.slider("Number of synthetic patients (beds)", 4, 60, key="w_n_patients", help=PARAM_HELP["n_patients"])
sb.slider("Simulation duration (days)", 3, 120, key="w_days", help=PARAM_HELP["days"])
sb.slider("Staff contacts per staff member per day", 1, 20, key="w_contact_rate", help=PARAM_HELP["contact_rate"])
sb.selectbox("Staff structure", ["shared", "cohorted"], key="w_contact_structure", help=PARAM_HELP["contact_structure"])
sb.number_input("Random seed", 0, 2**31 - 1, key="w_seed", step=1,
                help="Same seed + same settings = identical results. Change it to see another random 'ward history'.")
with sb.expander("Advanced model assumptions (illustrative)"):
    st.caption("These biological assumptions are illustrative, not validated estimates.")
    st.slider("Base transmission per contaminated-hand visit", 0.0, 0.3, key="w_base_transmission", step=0.01)
    st.slider("Hand-hygiene efficacy when performed", 0.5, 1.0, key="w_hh_efficacy", step=0.05)
    st.slider("Staff pickup probability from a carrier", 0.0, 1.0, key="w_pickup_prob", step=0.05)
    st.slider("Selection pressure (sensitive -> resistant per antibiotic day)", 0.0, 0.2, key="w_selection_pressure", step=0.01)
    st.slider("Antibiotic killing of sensitive organism", 0.0, 1.0, key="w_abx_kill", step=0.05)
    st.slider("Antibiotic boost to colonization risk", 0.0, 2.0, key="w_abx_susceptibility_boost", step=0.1)
    st.slider("Average length of stay (days)", 3.0, 60.0, key="w_avg_los", step=1.0)
    st.slider("Carriage on admission", 0.0, 0.5, key="w_import_prevalence", step=0.01)
    st.slider("Resistant share of admission carriage", 0.0, 1.0, key="w_import_resistant_fraction", step=0.05)

try:
    cfg = cfg_from_widgets()
except ValueError as e:                        # should not happen with bounded widgets
    sb.error(f"Invalid settings: {e}")
    st.stop()

if sb.button("Apply settings and reset ward", type="primary", width="stretch"):
    new_sim(cfg)
    st.rerun()
if ss.sim.cfg != cfg:
    sb.warning("Settings changed - press **Apply settings and reset ward** to use them in the single-run view. "
               "(The Scenario lab always uses the settings shown here.)")
sim: WardSimulation = ss.sim

# ------------------------------------------------------------------ tabs
tab_over, tab_map, tab_lab, tab_learn, tab_export, tab_about = st.tabs(
    ["📊 Ward overview", "🗺️ Ward map", "🧪 Scenario lab", "🎓 Learning challenges", "💾 Export & experiments", "ℹ️ Methods & limits"])

# ================================================================== A. overview
with tab_over:
    finished = sim.day >= sim.cfg.days
    c1, c2, c3, c4, c5 = st.columns(5)
    if ss.playing:
        if c1.button("⏸ Pause", width="stretch"):
            ss.playing = False
            st.rerun()
    else:
        if c1.button("▶ Start (auto-play)", width="stretch", disabled=finished):
            ss.playing = True
            st.rerun()
    if c2.button("⏭ Advance 1 day", width="stretch", disabled=finished or ss.playing):
        sim.step()
        st.rerun()
    if c3.button("⏩ Run to the end", width="stretch", disabled=finished,
                 help="Runs all remaining days at once. Disabled once the run has finished, so a run cannot be duplicated by accident."):
        ss.playing = False
        sim.run()
        st.rerun()
    if c4.button("↺ Reset ward", width="stretch", help="Restores the exact starting state for this seed and settings."):
        ss.playing = False
        sim.reset()
        st.rerun()
    if c5.button("🔁 Repeat with next seed", width="stretch",
                 help="Runs the same settings again with seed + 1 (a different random history).",
                 disabled=sim.cfg.seed >= BOUNDS["seed"][1]):
        ss["_pending"] = sim.cfg.replace(seed=sim.cfg.seed + 1).to_dict()
        ss["_pending_run"] = True
        st.rerun()
    st.progress(min(1.0, sim.day / sim.cfg.days), text=f"Simulated day {sim.day} of {sim.cfg.days}"
                + ("  - finished (press Reset or Repeat to run again)" if finished else ""))

    h = sim.history_df
    last = h.iloc[-1]
    k = sim.k
    pdays = max(1, k["patient_days"])
    m = st.columns(6)
    m[0].metric("Synthetic patients", int(last.patients))
    m[1].metric("Susceptible", int(last.susceptible))
    m[2].metric("Colonized", int(last.colonized))
    m[3].metric("Infected", int(last.infected))
    m[4].metric("Resistant carriers", int(last.resistant_carriers),
                help="Patients currently colonized or infected with a resistant organism.")
    m[5].metric("On antibiotics today", int(last.on_antibiotic))
    m2 = st.columns(6)
    m2[0].metric("Antibiotic days /1000 pt-days", f"{1000*k['dot']/pdays:,.0f}" if sim.day else "-",
                 help="Cumulative antibiotic patient-days divided by cumulative patient-days x 1000 (simulated).")
    m2[1].metric("Hospital-onset infections /1000 pt-days", f"{1000*k['hai']/pdays:,.1f}" if sim.day else "-",
                 help="Infections with onset on ward day >= 3, per 1000 cumulative patient-days. A simulation rule, not a clinical incidence rate.")
    m2[2].metric("Ward-acquired colonizations", int(k["acquisitions"]),
                 help="Cumulative count of new colonizations acquired on the ward (excludes carriage on admission).")
    m2[3].metric("Hand hygiene (observed / set)",
                 f"{last.observed_hand_hygiene:.0%}" if sim.day else "-", delta=f"set {sim.cfg.hand_hygiene:.0%}", delta_color="off")
    m2[4].metric("Isolation precautions (observed / set)",
                 "-" if pd.isna(last.observed_isolation) else f"{last.observed_isolation:.0%}",
                 delta=f"set {sim.cfg.isolation_compliance:.0%}", delta_color="off")
    m2[5].metric("Prescriptions indicated (observed)",
                 "-" if pd.isna(last.observed_stewardship) else f"{last.observed_stewardship:.0%}",
                 help="Share of antibiotic courses started that were clinically indicated. Stewardship raises it by avoiding unnecessary courses.")
    st.caption("All values are SIMULATED. Counts are cumulative or current as labelled; rates use cumulative patient-days as denominator; "
               "'observed' compliance is measured from simulated opportunities, 'set' is the input.")
    a, b = st.columns(2)
    a.plotly_chart(viz.states_chart(h), width="stretch", key="ch_states")
    b.plotly_chart(viz.resistance_chart(h), width="stretch", key="ch_res")
    a, b = st.columns(2)
    a.plotly_chart(viz.antibiotic_chart(h), width="stretch", key="ch_abx")
    b.plotly_chart(viz.infections_chart(h), width="stretch", key="ch_inf")
    st.plotly_chart(viz.compliance_chart(h, sim.cfg), width="stretch", key="ch_comp")
    st.caption("This is ONE random run. Differences between runs can be due to chance - use the Scenario lab to compare distributions.")

# ================================================================== B. ward map
with tab_map:
    st.subheader("Synthetic ward map")
    pids = [p.pid for p in sim.patients]
    colA, colB = st.columns([3, 2])
    with colB:
        sel = st.selectbox("Inspect a patient", ["(none)"] + pids, key="map_sel")
        show_tx = st.toggle("Show transmission pathways", value=True,
                            help="Dashed lines join the patient whose organism was carried by staff hands to the newly colonized patient.")
        p_sel = next((p for p in sim.patients if p.pid == sel), None)
        if p_sel:
            st.markdown(f"**{p_sel.pid}** - bed {p_sel.bed + 1}")
            st.write(f"State: **{p_sel.state}**  |  Organism: **{p_sel.organism}**  |  On antibiotic: **{'yes' if p_sel.on_antibiotic else 'no'}**  |  "
                     f"Isolated: **{'yes' if p_sel.isolated else 'no'}**  |  Detected: **{'yes' if p_sel.detected else 'no'}**  |  Ward day: **{p_sel.los}**")
            ev = pd.DataFrame(p_sel.events, columns=["Day", "Simulated event"])
            st.dataframe(ev, width="stretch", hide_index=True)
        else:
            st.info("Pick a patient to see their simulated status and event history.")
    with colA:
        st.plotly_chart(viz.ward_map(sim, p_sel.pid if p_sel else None, show_tx), width="stretch", key="ch_map")
    st.caption("Legend: shape and label, not only colour - circle = Susceptible, square = Colonized, diamond = Infected; thick ring = resistant organism; "
               "hexagon outline = isolated; 'ABX' = on antibiotics; number = bed. All synthetic.")
    st.subheader("Transmission events in this run")
    if sim.transmissions:
        st.dataframe(pd.DataFrame(sim.transmissions).rename(columns={"day": "Day", "source": "Source patient", "staff": "Staff",
                                                                    "target": "New carrier", "organism": "Organism"}),
                     width="stretch", hide_index=True)
        st.caption("Each row: a staff member picked up the organism from the source patient and delivered it to the recipient later the same day.")
    else:
        st.info("No ward-acquired transmissions yet. Advance the simulation or try lower hand hygiene.")

# ================================================================== D/F/G. scenario lab
with tab_lab:
    st.subheader("Counterfactual scenario laboratory")
    st.markdown("Compare a **baseline** with an **alternative** on the **same synthetic starting wards and matched random seeds**, "
                "repeated many times, so you see distributions and uncertainty rather than one lucky or unlucky run. "
                "Ward size, duration, seed and advanced assumptions come from the sidebar; presets only change the practice settings.")
    saved = [f"Saved: {p.stem}" for p in sc.list_saved(SAVE_DIR())]
    options = list(SCENARIOS) + ["Current sidebar settings"] + saved
    c1, c2, c3 = st.columns([2, 2, 1])
    src_b = c1.selectbox("Baseline", options, index=0, key="lab_b")
    src_a = c2.selectbox("Alternative", options, index=4, key="lab_a")
    n_rep = c3.slider("Replicates", 5, 100, 30, key="lab_n", help="More replicates give narrower uncertainty intervals but take longer.")
    if st.button("▶ Run comparison", type="primary"):
        try:
            nb, cb = resolve_source(src_b)
            na, ca = resolve_source(src_a)
            with st.spinner(f"Running {2 * n_rep} simulations..."):
                ss.comparison = analytics.compare(cb, ca, n_rep=n_rep, base_seed=cfg.seed)
            ss.cmp_names = (nb, na)
            ss.sens = None
        except (ValueError, OSError) as e:
            st.error(f"Could not run comparison: {e}")
    res = ss.comparison
    if res is not None:
        nb, na = ss.cmp_names
        st.success(f"Showing: **{na}** vs **{nb}** - {res['n_rep']} matched-seed replicates, seeds {res['seed0']}-{res['seed0'] + res['n_rep'] - 1}")
        key_metrics = ["hai_per_1000pd", "acquisitions_per_1000pd", "resistant_acquisitions", "mean_resistant_prevalence",
                       "dot_per_1000pd", "adverse_outcomes", "screens", "isolation_days"]
        pt = res["paired"].set_index("metric").loc[key_metrics]
        show = pd.DataFrame({
            "Outcome (simulated)": pt.label, "Baseline mean": pt.baseline_mean, "Alternative mean": pt.alt_mean,
            "Mean difference (alt - base)": pt.mean_diff, "95% CI low": pt.ci_low, "95% CI high": pt.ci_high,
            "Alt lower in % of runs": 100 * pt.frac_alt_lower, "Clear difference?": np.where(pt.ci_excludes_zero, "yes (CI excludes 0)", "no (CI includes 0)")})
        st.dataframe(show.round(3), width="stretch", hide_index=True)
        st.caption("Paired differences use the same seed in both arms. CI = 95% percentile bootstrap of the paired mean difference. "
                   "Rates use cumulative patient-days as denominator; counts are totals over the run. Not clinical incidence rates.")
        st.plotly_chart(viz.diff_chart(res["paired"], key_metrics), width="stretch", key="ch_diff")
        a, b = st.columns(2)
        metric = a.selectbox("Distribution across replicates", list(METRIC_LABELS), format_func=lambda x: METRIC_LABELS[x], key="box_m")
        st.plotly_chart(viz.box_compare(res["baseline"], res["alternative"], metric, "Baseline", "Alternative"),
                        width="stretch", key="ch_box")
        st.plotly_chart(viz.tradeoff_chart(res["baseline"], res["alternative"]), width="stretch", key="ch_trade")
        st.caption("Trade-off view: an intervention can lower infections yet cost more screens and isolation-days, or lower antibiotic use "
                   "without changing transmission. Open rings are group means.")
        with st.expander("📖 Explanation: what changed, why, and what you cannot conclude", expanded=True):
            st.markdown(reporting.explain_comparison(res, nb, na))
        d1, d2 = st.columns(2)
        d1.download_button("⬇ Replicate-level results (CSV)",
                           pd.concat([res["baseline"].assign(arm="baseline"), res["alternative"].assign(arm="alternative")]).to_csv(index=False),
                           "replicates.csv", "text/csv", width="stretch")
        d2.download_button("⬇ Paired summary (CSV)", res["paired"].to_csv(index=False), "paired_summary.csv", "text/csv", width="stretch")
    else:
        st.info("Choose a baseline and an alternative, then press **Run comparison**.")

    with st.expander("🔬 Sensitivity analysis (one parameter at a time)"):
        st.caption("Sweeps one parameter of the current sidebar settings with matched seeds. Check the response matches the model's stated rules.")
        sweeps = {"base_transmission": (0.02, 0.3), "hand_hygiene": (0.0, 1.0), "isolation_effectiveness": (0.0, 1.0),
                  "contact_rate": (2, 20), "selection_pressure": (0.0, 0.2), "stewardship_compliance": (0.0, 1.0)}
        s1, s2, s3 = st.columns(3)
        sp = s1.selectbox("Parameter", list(sweeps), key="sens_p")
        sm = s2.selectbox("Outcome", list(METRIC_LABELS), format_func=lambda x: METRIC_LABELS[x], key="sens_m")
        sn = s3.slider("Replicates per value", 5, 40, 15, key="sens_n")
        if st.button("Run sensitivity sweep"):
            lo, hi = sweeps[sp]
            vals = np.linspace(lo, hi, 6)
            if BOUNDS[sp][2] is int:
                vals = np.unique(np.round(vals).astype(int))
            with st.spinner("Running sweep..."):
                ss.sens = (sp, sm, analytics.sensitivity(cfg, sp, [v.item() for v in vals], sn, sm))
        if ss.sens:
            sp_, sm_, sdf = ss.sens
            st.plotly_chart(viz.sensitivity_chart(sdf, sp_, sm_), width="stretch", key="ch_sens")
            st.dataframe(sdf.round(3), width="stretch", hide_index=True)

# ================================================================== H. learning
with tab_learn:
    st.subheader("Learning challenges (hypothetical synthetic wards)")
    st.caption("Educational scenarios only - they give no patient-specific treatment advice. Each runs 30 matched replicates of a 24-bed, 30-day ward.")
    for ch in CHALLENGES:
        with st.expander(ch["title"], expanded=(ch["id"] == "c1")):
            st.markdown(f"**Situation.** {ch['situation']}")
            st.markdown(f"**Predict first:** {ch['predict']}")
            choice = st.radio("Choose an intervention", list(ch["options"]), key=f"opt_{ch['id']}")
            if st.button("Run this challenge", key=f"run_{ch['id']}"):
                base_cfg = SimConfig.from_dict({**SimConfig().to_dict(), **ch["base"], "seed": cfg.seed})
                alt_cfg = base_cfg.replace(**ch["options"][choice])
                with st.spinner("Simulating 60 wards..."):
                    ss[f"res_{ch['id']}"] = (choice, analytics.compare(base_cfg, alt_cfg, n_rep=30, base_seed=cfg.seed))
            got = ss.get(f"res_{ch['id']}")
            if got:
                chosen, r = got
                st.markdown(f"**Modelled consequences of:** *{chosen}*")
                pt = r["paired"].set_index("metric").loc[ch["focus"]]
                st.dataframe(pd.DataFrame({
                    "Outcome (simulated)": pt.label, "Before (challenge ward)": pt.baseline_mean, "After intervention": pt.alt_mean,
                    "Mean difference": pt.mean_diff, "95% CI low": pt.ci_low, "95% CI high": pt.ci_high}).round(2),
                    width="stretch", hide_index=True)
                st.plotly_chart(viz.box_compare(r["baseline"], r["alternative"], ch["focus"][0], "Before", "After"),
                                width="stretch", key=f"box_{ch['id']}")
                st.info(f"**Principle.** {ch['principle']}")
                st.markdown(f"**Reflect:** {ch['reflection']}")
                st.text_area("Your notes (not saved)", key=f"note_{ch['id']}")

# ================================================================== I. export
with tab_export:
    st.subheader("Save, export and reproduce experiments")
    st.caption("Every export records the parameters and random seed, and states that the results are simulated.")
    e1, e2 = st.columns(2)
    with e1:
        st.markdown("##### Scenario configurations")
        name = st.text_input("Scenario name", "My scenario", key="save_name")
        if st.button("💾 Save current settings as scenario"):
            try:
                path = sc.save_scenario(name, cfg, SAVE_DIR())
                st.success(f"Saved to {path}")
            except (ValueError, OSError) as ex:
                st.error(str(ex))
        saved_files = sc.list_saved(SAVE_DIR())
        if saved_files:
            pick = st.selectbox("Load a saved scenario", [p.stem for p in saved_files], key="load_pick")
            if st.button("📂 Load selected scenario"):
                try:
                    nm, loaded = sc.load_scenario(SAVE_DIR() / (pick + ".json"))
                    ss["_pending"] = loaded.to_dict(); ss.notice = f"Loaded scenario '{nm}'."
                    st.rerun()
                except (ValueError, OSError) as ex:
                    st.error(f"Could not load: {ex}")
        st.download_button("⬇ Download current settings (JSON)", json.dumps(dict(name="Current settings", synthetic_only=True, config=cfg.to_dict()), indent=2),
                           "scenario.json", "application/json")
        up = st.file_uploader("Upload a scenario file (JSON)", type=["json"], key="up_scn")
        if up is not None and st.button("Apply uploaded scenario"):
            try:
                nm, loaded = sc.parse_scenario_text(up.getvalue().decode("utf-8", "ignore"))
                ss["_pending"] = loaded.to_dict(); ss.notice = f"Loaded scenario '{nm}'."
                st.rerun()
            except ValueError as ex:
                st.error(f"Scenario file rejected: {ex}")
    with e2:
        st.markdown("##### Results of the current single run")
        h = sim.history_df
        st.download_button("⬇ Daily indicators (CSV)", h.to_csv(index=False), f"daily_indicators_seed{sim.cfg.seed}.csv", "text/csv")
        st.download_button("⬇ Patient table at current day (CSV)", sim.patient_table().to_csv(index=False), "patients_synthetic.csv", "text/csv")
        ev_rows = [dict(patient=p.pid, day=d, event=t) for p in sim.patients for d, t in p.events]
        st.download_button("⬇ Event log of current patients (CSV)", pd.DataFrame(ev_rows, columns=["patient", "day", "event"]).to_csv(index=False),
                           "events_synthetic.csv", "text/csv")
        st.download_button("⬇ Transmission events (CSV)",
                           pd.DataFrame(sim.transmissions, columns=["day", "source", "staff", "target", "organism"]).to_csv(index=False),
                           "transmissions_synthetic.csv", "text/csv")
        report = reporting.build_report(sim.cfg, sim, ss.comparison, ss.cmp_names)
        st.download_button("⬇ Summary report (Markdown)", report, "amr_ward_report.md", "text/markdown", type="primary")
        if st.button("Save report into the reports folder"):
            try:
                p = REPORT_DIR() / f"report_seed{sim.cfg.seed}_{time.strftime('%Y%m%d_%H%M%S')}.md"
                p.write_text(report, encoding="utf-8"); st.success(f"Saved {p}")
            except OSError as ex:
                st.error(str(ex))
        st.caption("Charts: use the camera icon in each chart's toolbar to download a PNG.")
    st.divider()
    st.markdown("##### Reproduce a previous experiment")
    st.download_button("⬇ Download experiment record (JSON: parameters + seeds)",
                       reporting.experiment_record(sim.cfg, ss.comparison, ss.cmp_names), "experiment_record.json", "application/json")
    rec = st.file_uploader("Upload an experiment record (JSON) to reproduce it", type=["json"], key="up_rec")
    if rec is not None and st.button("Reproduce this experiment"):
        try:
            obj = json.loads(rec.getvalue().decode("utf-8", "ignore"))
            if not isinstance(obj, dict) or "config" not in obj:
                raise ValueError("record has no 'config' section")
            loaded = SimConfig.from_dict(obj["config"])
            ss["_pending"] = loaded.to_dict(); ss["_pending_run"] = True
            ss.notice = "Experiment reloaded and re-run with the recorded parameters and seed."
            st.rerun()
        except (ValueError, json.JSONDecodeError) as ex:
            st.error(f"Experiment record rejected: {ex}")

# ================================================================== about
with tab_about:
    st.subheader("Methods, assumptions and limitations")
    st.markdown(METHODS_MD)
    with st.expander("Limitations", expanded=True):
        st.markdown(LIMITATIONS_MD)
    with st.expander("Evaluation plan and research question"):
        st.markdown(EVAL_PLAN_MD)
    with st.expander("Novelty status and related work"):
        st.markdown(NOVELTY_MD)
    with st.expander("Model parameters used in the current run"):
        st.json(sim.cfg.to_dict())

# ------------------------------------------------------------------ auto-play loop
if ss.playing:
    if sim.day < sim.cfg.days:
        sim.step()
        time.sleep(0.35)
        st.rerun()
    else:
        ss.playing = False
        st.rerun()
