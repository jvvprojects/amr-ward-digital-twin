"""Plain-language explanations and exportable reports. Every report states that results are simulated."""
from __future__ import annotations
import datetime as dt
import json
import pandas as pd
from analytics import METRIC_LABELS, changed_parameters, outcomes
from simulation import SimConfig

APP_VERSION = "1.0-prototype"

DISCLAIMER = ("All patients, events, transmission outcomes and indicators in this report are SIMULATED from a "
              "rule-based educational model with illustrative parameters. The model has NOT been clinically "
              "validated, is not a forecasting tool, and must never inform real-patient care or hospital policy.")

MECHANISM = {
    "hand_hygiene": "Cleans staff hands before and after each contact, so staff carry organisms from one bed to the next less often (acts on pickup and delivery).",
    "isolation_enabled": "Turns isolation of detected resistant carriers on or off.",
    "isolation_compliance": "Raises the share of visits to isolated patients where barrier precautions are used (acts on staff pickup from known carriers).",
    "isolation_effectiveness": "Makes precautions, when used, block more contamination of staff.",
    "contact_rate": "More staff-patient contacts create more transmission opportunities.",
    "contact_structure": "Cohorted staff mostly stay with their own beds, so organisms cross between groups less often.",
    "prescribe_rate": "More prescribing decisions mean more antibiotic exposure.",
    "inappropriate_fraction": "A larger share of unnecessary prescribing means more avoidable antibiotic exposure.",
    "stewardship_compliance": "Avoids a share of unnecessary prescriptions and shortens courses, lowering antibiotic exposure, selection pressure and infection risk.",
    "surveillance_intensity": "More screening finds carriers sooner (needed before isolation can start) but uses more tests.",
    "n_patients": "Changes the number of beds and staff (denominators change).",
    "days": "Changes the length of the observation window.",
    "base_transmission": "Scales how easily contaminated hands colonize a patient.",
    "selection_pressure": "Scales how often antibiotics convert sensitive carriage to resistant carriage.",
}

CANNOT = ("This simulation cannot tell you the real effect of any intervention in a real hospital. It uses invented, "
          "illustrative parameters, a single organism, a simplified contact network and no real patient data. "
          "It shows how the modelled mechanisms interact, not how large real effects are.")


def _fmt(x) -> str:
    return "n/a" if pd.isna(x) else f"{x:,.2f}"


def explain_comparison(res: dict, name_b: str, name_a: str) -> str:
    b_cfg, a_cfg = SimConfig.from_dict(res["baseline_cfg"]), SimConfig.from_dict(res["alt_cfg"])
    ch = changed_parameters(b_cfg, a_cfg)
    paired = res["paired"].set_index("metric")
    L = [f"### What you changed ({name_a} vs {name_b})"]
    if ch:
        for k, (bv, av) in ch.items():
            L.append(f"- **{k}**: {bv} -> {av}")
    else:
        L.append("- Nothing: both configurations are identical, so any differences are zero by construction.")
    L.append("\n### Which model mechanisms were affected")
    for k in ch:
        L.append(f"- *{k}*: {MECHANISM.get(k, 'See README assumptions.')}")
    L.append("\n### What changed in the simulated outcomes")
    L.append(f"Each of {res['n_rep']} replicates used the same seed and the same starting ward in both arms (matched seeds); differences are paired.")
    for m in ["hai_per_1000pd", "acquisitions_per_1000pd", "resistant_acquisitions", "mean_resistant_prevalence",
              "dot_per_1000pd", "adverse_outcomes", "screens", "isolation_days"]:
        r = paired.loc[m]
        sig = "interval excludes zero" if r.ci_excludes_zero else "interval includes zero (no clear difference)"
        L.append(f"- {METRIC_LABELS[m]}: {_fmt(r.baseline_mean)} -> {_fmt(r.alt_mean)} "
                 f"(difference {_fmt(r.mean_diff)}, 95% bootstrap CI {_fmt(r.ci_low)} to {_fmt(r.ci_high)}; {sig}).")
    L.append("\n### Did results vary between repeated runs?")
    hai, acq = paired.loc["hai_per_1000pd"], paired.loc["acquisitions_per_1000pd"]
    L.append(f"The alternative had lower hospital-onset infection rates in {100*hai.frac_alt_lower:.0f}% of replicates and lower "
             f"acquisition rates in {100*acq.frac_alt_lower:.0f}%. Anything far from 0% or 100% means chance alone can reverse the "
             "result in a single run - which is why one simulation is never enough.")
    L.append("\n### Which assumptions account for this")
    L.append("Transmission is staff-mediated only; hand hygiene works multiplicatively before and after each contact; isolation "
             "needs prior detection; antibiotics raise colonization risk, convert sensitive to resistant carriage and raise infection "
             "risk. All values are illustrative (see README).")
    L.append("\n### What cannot be concluded")
    L.append(CANNOT)
    return "\n".join(L)


def build_report(cfg: SimConfig, sim=None, comparison: dict | None = None, names=("Baseline", "Alternative")) -> str:
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    L = ["# AMR-Ward Digital Twin - Summary Report", f"*Generated {now} - app version {APP_VERSION}*", "",
         f"> **{DISCLAIMER}**", "", "## Model parameters and random seed", "```json",
         json.dumps(cfg.to_dict(), indent=2), "```", "",
         "Reproduce: enter the same parameters and seed in the app (or upload the experiment record JSON)."]
    if sim is not None and sim.day > 0:
        o = outcomes(sim)
        L += ["", f"## Single run (seed {cfg.seed}, {sim.day} of {cfg.days} days simulated)",
              "| Indicator (simulated) | Value | Definition |", "|---|---|---|"]
        defs = {"hai_per_1000pd": "infections with onset on ward day >= 3 / patient-days x 1000",
                "acquisitions_per_1000pd": "new ward-acquired colonizations / patient-days x 1000",
                "dot_per_1000pd": "antibiotic patient-days / patient-days x 1000",
                "mean_resistant_prevalence": "mean over days of resistant carriers / occupied beds"}
        for k, v in o.items():
            L.append(f"| {METRIC_LABELS.get(k, k)} | {_fmt(v)} | {defs.get(k, 'cumulative count over the run')} |")
    if comparison is not None:
        L += ["", f"## Counterfactual comparison: {names[1]} vs {names[0]}",
              f"{comparison['n_rep']} matched-seed replicates, first seed {comparison['seed0']}.", "",
              "| Metric | Baseline mean | Alternative mean | Mean diff | 95% CI low | 95% CI high | Alt lower in % of runs |",
              "|---|---|---|---|---|---|---|"]
        for _, r in comparison["paired"].iterrows():
            L.append(f"| {r.label} | {_fmt(r.baseline_mean)} | {_fmt(r.alt_mean)} | {_fmt(r.mean_diff)} | "
                     f"{_fmt(r.ci_low)} | {_fmt(r.ci_high)} | {100*r.frac_alt_lower:.0f}% |")
        L += ["", explain_comparison(comparison, names[0], names[1])]
    L += ["", "## Limitations", CANNOT, "", "No educational effectiveness, clinical validity or novelty is claimed by this report."]
    return "\n".join(L)


def experiment_record(cfg: SimConfig, comparison: dict | None = None, names=("Baseline", "Alternative")) -> str:
    rec = dict(app_version=APP_VERSION, synthetic_only=True, note=DISCLAIMER,
               created=dt.datetime.now().isoformat(timespec="seconds"), config=cfg.to_dict())
    if comparison is not None:
        rec["comparison"] = dict(names=list(names), n_rep=comparison["n_rep"], seed0=comparison["seed0"],
                                 baseline_config=comparison["baseline_cfg"], alternative_config=comparison["alt_cfg"])
    return json.dumps(rec, indent=2)
