"""Outcome metrics, replicate runs, paired counterfactual comparison, sensitivity analysis.

Definitions (all SIMULATED):
  * per-1000-patient-day rates use cumulative patient-days over the whole run as denominator.
  * "hospital-onset infection" = infection onset on ward day >= 3 (a simulation rule, not a
    clinical surveillance definition).
  * counts are cumulative over the run; prevalence values are daily proportions of beds.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from simulation import SimConfig, WardSimulation

METRIC_LABELS = {
    "hai_per_1000pd": "Hospital-onset infections /1000 patient-days",
    "resistant_hai_per_1000pd": "Resistant hospital-onset infections /1000 patient-days",
    "acquisitions_per_1000pd": "Ward-acquired colonizations /1000 patient-days",
    "resistant_acquisitions": "Resistant acquisitions (count)",
    "mean_resistant_prevalence": "Mean resistant-carrier prevalence (proportion of beds)",
    "dot_per_1000pd": "Antibiotic days of therapy /1000 patient-days",
    "inappropriate_prescriptions": "Not-indicated prescriptions started (count)",
    "adverse_outcomes": "Simulated adverse outcomes (count)",
    "screens": "Screening tests performed (resource)",
    "isolation_days": "Isolation patient-days (resource)",
}
# metrics where lower is better (used only for the "alt lower" proportion wording)
LOWER_BETTER = ["hai_per_1000pd", "resistant_hai_per_1000pd", "acquisitions_per_1000pd",
                "resistant_acquisitions", "mean_resistant_prevalence", "dot_per_1000pd",
                "inappropriate_prescriptions", "adverse_outcomes"]


def outcomes(sim: WardSimulation) -> dict:
    h, k = sim.history_df, sim.k
    pd_ = max(1, k["patient_days"])
    per = 1000.0 / pd_
    daily = h[h.day > 0]
    return dict(
        hai_per_1000pd=k["hai"] * per,
        resistant_hai_per_1000pd=k["res_hai"] * per,
        acquisitions_per_1000pd=k["acquisitions"] * per,
        resistant_acquisitions=k["res_acquisitions"],
        mean_resistant_prevalence=float((daily.resistant_carriers / daily.patients).mean()) if len(daily) else 0.0,
        dot_per_1000pd=k["dot"] * per,
        inappropriate_prescriptions=k["inappropriate"],
        adverse_outcomes=k["adverse"],
        screens=k["screens"],
        isolation_days=k["iso_days"],
        observed_hand_hygiene=(k["hh_done"] / k["hh_opp"]) if k["hh_opp"] else np.nan,
        observed_stewardship=(k["appropriate"] / k["started"]) if k["started"] else np.nan,
    )


def run_replicates(cfg: SimConfig, n_rep: int, base_seed: int | None = None) -> pd.DataFrame:
    """Run n_rep stochastic replicates; replicate i uses seed base_seed+i."""
    if not (1 <= n_rep <= 500):
        raise ValueError("n_rep must be between 1 and 500")
    base = cfg.seed if base_seed is None else base_seed
    rows = []
    for i in range(n_rep):
        sim = WardSimulation(cfg.replace(seed=base + i))
        sim.run()
        r = outcomes(sim); r["replicate"] = i; r["seed"] = base + i
        rows.append(r)
    return pd.DataFrame(rows)


def distribution_summary(df: pd.DataFrame, metrics=None) -> pd.DataFrame:
    metrics = metrics or list(METRIC_LABELS)
    out = []
    for m in metrics:
        x = df[m].to_numpy(float)
        n = len(x)
        sd = x.std(ddof=1) if n > 1 else 0.0
        half = 1.96 * sd / np.sqrt(n) if n > 1 else 0.0
        out.append(dict(metric=m, label=METRIC_LABELS.get(m, m), mean=x.mean(), sd=sd,
                        mean_ci_low=x.mean() - half, mean_ci_high=x.mean() + half,
                        p2_5=np.percentile(x, 2.5), median=np.median(x), p97_5=np.percentile(x, 97.5)))
    return pd.DataFrame(out)


def compare(base_cfg: SimConfig, alt_cfg: SimConfig, n_rep: int = 30, base_seed: int | None = None,
            n_boot: int = 2000) -> dict:
    """Counterfactual comparison on matched seeds.

    Replicate i of both configurations uses the SAME seed -> same synthetic ward and shared
    random streams. Differences are paired (alt - baseline); the CI is a percentile bootstrap
    over paired differences (fixed bootstrap seed for reproducibility).
    """
    seed0 = base_cfg.seed if base_seed is None else base_seed
    b = run_replicates(base_cfg, n_rep, seed0)
    a = run_replicates(alt_cfg, n_rep, seed0)
    rng = np.random.default_rng(20240601)
    rows = []
    for m in METRIC_LABELS:
        diff = a[m].to_numpy(float) - b[m].to_numpy(float)
        if n_rep > 1:
            idx = rng.integers(0, n_rep, size=(n_boot, n_rep))
            boots = diff[idx].mean(axis=1)
            lo, hi = np.percentile(boots, [2.5, 97.5])
        else:
            lo = hi = diff.mean()
        rows.append(dict(metric=m, label=METRIC_LABELS[m], baseline_mean=b[m].mean(), alt_mean=a[m].mean(),
                         mean_diff=diff.mean(), ci_low=lo, ci_high=hi,
                         pct_change=(100 * diff.mean() / b[m].mean()) if b[m].mean() else np.nan,
                         frac_alt_lower=float((diff < 0).mean()), frac_alt_higher=float((diff > 0).mean()),
                         ci_excludes_zero=bool(lo > 0 or hi < 0)))
    return dict(baseline=b, alternative=a, paired=pd.DataFrame(rows), seed0=seed0, n_rep=n_rep,
                baseline_cfg=base_cfg.to_dict(), alt_cfg=alt_cfg.to_dict())


def changed_parameters(base_cfg: SimConfig, alt_cfg: SimConfig) -> dict:
    b, a = base_cfg.to_dict(), alt_cfg.to_dict()
    return {k: (b[k], a[k]) for k in b if b[k] != a[k]}


def sensitivity(cfg: SimConfig, param: str, values, n_rep: int = 20, metric: str = "hai_per_1000pd") -> pd.DataFrame:
    """One-at-a-time sweep of a single parameter (same seeds at every value)."""
    rows = []
    for v in values:
        df = run_replicates(cfg.replace(**{param: v}), n_rep, cfg.seed)
        x = df[metric].to_numpy(float)
        rows.append(dict(parameter=param, value=v, mean=x.mean(),
                         low=np.percentile(x, 2.5), high=np.percentile(x, 97.5)))
    return pd.DataFrame(rows)
