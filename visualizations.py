"""Plotly charts. Colour-blind-safe palette (Okabe-Ito) AND distinct marker shapes/labels,
so nothing relies on colour alone."""
from __future__ import annotations
import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from patients import SUSCEPTIBLE, COLONIZED, INFECTED, RESISTANT, SENSITIVE
from analytics import METRIC_LABELS

COL = {SUSCEPTIBLE: "#56B4E9", COLONIZED: "#E69F00", INFECTED: "#D55E00"}
SYM = {SUSCEPTIBLE: "circle", COLONIZED: "square", INFECTED: "diamond"}
C_BASE, C_ALT = "#0072B2", "#D55E00"
SIM_TAG = "SIMULATED DATA - educational model, not clinically validated"
LAYOUT = dict(template="plotly_white", font=dict(family="Segoe UI, Arial, sans-serif", size=13),
              margin=dict(l=50, r=20, t=50, b=45), legend=dict(orientation="h", y=-0.2))


def _fig(title: str, xt: str = "", yt: str = "", height: int = 340) -> go.Figure:
    f = go.Figure()
    f.update_layout(title=dict(text=title, font=dict(size=15)), height=height, xaxis_title=xt,
                    yaxis_title=yt, **LAYOUT)
    return f


def states_chart(h: pd.DataFrame) -> go.Figure:
    f = _fig("Patient states over time (count of beds)", "Day", "Patients")
    for col, name, state, dash in [("susceptible", "Susceptible", SUSCEPTIBLE, "solid"),
                                   ("colonized", "Colonized", COLONIZED, "dash"),
                                   ("infected", "Infected", INFECTED, "dot")]:
        f.add_scatter(x=h.day, y=h[col], name=name, mode="lines", line=dict(color=COL[state], dash=dash, width=3))
    return f


def resistance_chart(h: pd.DataFrame) -> go.Figure:
    f = _fig("Resistant vs sensitive carriers (colonized + infected)", "Day", "Patients")
    f.add_scatter(x=h.day, y=h.resistant_carriers, name="Resistant organism", mode="lines",
                  line=dict(color="#CC79A7", width=3))
    f.add_scatter(x=h.day, y=h.sensitive_carriers, name="Sensitive organism", mode="lines",
                  line=dict(color="#009E73", width=3, dash="dash"))
    f.add_scatter(x=h.day, y=h.isolated, name="In isolation", mode="lines",
                  line=dict(color="#333333", width=2, dash="dot"))
    return f


def antibiotic_chart(h: pd.DataFrame) -> go.Figure:
    f = _fig("Antibiotic exposure", "Day", "Patients on antibiotics (bars)")
    f.add_bar(x=h.day, y=h.on_antibiotic, name="Patients on antibiotics today", marker_color="#56B4E9")
    f.add_scatter(x=h.day, y=h.cum_dot, name="Cumulative days of therapy", yaxis="y2", mode="lines",
                  line=dict(color="#222", width=3))
    f.update_layout(yaxis2=dict(title="Cumulative days of therapy", overlaying="y", side="right", showgrid=False))
    return f


def compliance_chart(h: pd.DataFrame, cfg) -> go.Figure:
    f = _fig("Observed compliance (cumulative proportion)", "Day", "Proportion", 340)
    f.add_scatter(x=h.day, y=h.observed_hand_hygiene, name="Hand hygiene (observed)", mode="lines", line=dict(color="#0072B2", width=3))
    f.add_scatter(x=h.day, y=h.observed_isolation, name="Isolation precautions (observed)", mode="lines", line=dict(color="#333", width=3, dash="dash"))
    f.add_scatter(x=h.day, y=h.observed_stewardship, name="Prescriptions that were indicated", mode="lines", line=dict(color="#009E73", width=3, dash="dot"))
    f.add_hline(y=cfg.hand_hygiene, line_dash="longdash", line_color="#0072B2", opacity=0.4,
                annotation_text="hand hygiene setting", annotation_position="top left")
    f.update_yaxes(range=[0, 1.02])
    return f


def infections_chart(h: pd.DataFrame) -> go.Figure:
    f = _fig("Cumulative simulated events", "Day", "Count since day 0")
    for col, name, color, dash in [("cum_acquisitions", "Ward-acquired colonizations", "#E69F00", "solid"),
                                   ("cum_resistant_acquisitions", "...of which resistant", "#CC79A7", "dash"),
                                   ("cum_hai", "Hospital-onset infections (day >= 3)", "#D55E00", "solid"),
                                   ("cum_resistant_infections", "Resistant infections (all onset)", "#882255", "dot")]:
        f.add_scatter(x=h.day, y=h[col], name=name, mode="lines", line=dict(color=color, dash=dash, width=3))
    return f


def ward_map(sim, selected_pid: str | None = None, show_tx: bool = True) -> go.Figure:
    pts = sim.patients
    n = len(pts)
    cols = max(3, math.ceil(math.sqrt(n * 1.6)))
    pos = {p.pid: (p.bed % cols, -(p.bed // cols)) for p in pts}
    f = _fig(f"Synthetic ward - day {sim.day} ({n} beds)", height=120 + 95 * math.ceil(n / cols))
    f.update_xaxes(visible=False, range=[-0.7, cols - 0.3]); f.update_yaxes(visible=False, scaleanchor=None)
    if show_tx:
        xs, ys = [], []
        for t in sim.transmissions:
            if t["source"] in pos and t["target"] in pos:
                (x0, y0), (x1, y1) = pos[t["source"]], pos[t["target"]]
                xs += [x0, x1, None]; ys += [y0, y1, None]
        if xs:
            f.add_scatter(x=xs, y=ys, mode="lines", line=dict(color="#555", width=2, dash="dash"),
                          name="Transmission pathway (source -> staff -> recipient)", hoverinfo="skip")
    for state in (SUSCEPTIBLE, COLONIZED, INFECTED):
        sub = [p for p in pts if p.state == state]
        f.add_scatter(
            x=[pos[p.pid][0] for p in sub], y=[pos[p.pid][1] for p in sub], mode="markers+text",
            name=state, marker=dict(symbol=SYM[state], size=34, color=COL[state], line=dict(color="#222", width=1.5)),
            text=[str(p.bed + 1) for p in sub], textposition="middle center", textfont=dict(color="#111", size=12),
            customdata=[[p.pid, p.organism, "yes" if p.on_antibiotic else "no", "yes" if p.isolated else "no", p.los] for p in sub],
            hovertemplate="<b>%{customdata[0]}</b><br>Organism: %{customdata[1]}<br>Antibiotic: %{customdata[2]}"
                          "<br>Isolated: %{customdata[3]}<br>Ward day: %{customdata[4]}<extra>" + state + "</extra>")
    res = [p for p in pts if p.organism == RESISTANT]
    f.add_scatter(x=[pos[p.pid][0] for p in res], y=[pos[p.pid][1] for p in res], mode="markers",
                  name="Resistant organism (thick ring)", hoverinfo="skip",
                  marker=dict(symbol="circle-open", size=48, color="#CC79A7", line=dict(width=4)))
    iso = [p for p in pts if p.isolated]
    f.add_scatter(x=[pos[p.pid][0] for p in iso], y=[pos[p.pid][1] for p in iso], mode="markers",
                  name="Isolated (hexagon outline)", hoverinfo="skip",
                  marker=dict(symbol="hexagon2-open", size=58, color="#222", line=dict(width=2)))
    ab = [p for p in pts if p.on_antibiotic]
    f.add_scatter(x=[pos[p.pid][0] for p in ab], y=[pos[p.pid][1] - 0.36 for p in ab], mode="text",
                  name="On antibiotic (ABX label)", text=["ABX"] * len(ab), hoverinfo="skip",
                  textfont=dict(size=11, color="#006699"))
    if selected_pid and selected_pid in pos:
        x, y = pos[selected_pid]
        f.add_scatter(x=[x], y=[y], mode="markers", name="Selected patient", hoverinfo="skip",
                      marker=dict(symbol="star-open", size=64, color="#000", line=dict(width=2)))
    f.update_layout(legend=dict(orientation="h", y=-0.02, font=dict(size=11)))
    return f


def box_compare(b: pd.DataFrame, a: pd.DataFrame, metric: str, name_b="Baseline", name_a="Alternative") -> go.Figure:
    f = _fig(METRIC_LABELS[metric], "", "", 340)
    f.add_box(y=b[metric], name=name_b, boxpoints="all", jitter=0.4, pointpos=0, marker_color=C_BASE,
              boxmean=True, line_color=C_BASE)
    f.add_box(y=a[metric], name=name_a, boxpoints="all", jitter=0.4, pointpos=0, marker_color=C_ALT,
              boxmean=True, line_color=C_ALT)
    f.update_layout(showlegend=False)
    return f


def diff_chart(paired: pd.DataFrame, metrics: list[str]) -> go.Figure:
    """Percent change with bootstrap CI, per metric (normalised so scales are comparable)."""
    p = paired.set_index("metric").loc[metrics]
    f = _fig("Alternative minus baseline: mean paired difference (95% bootstrap CI), as % of baseline mean", "", "", 360)
    base = p.baseline_mean.replace(0, np.nan)
    f.add_bar(y=[METRIC_LABELS[m] for m in p.index], x=100 * p.mean_diff / base, orientation="h",
              marker_color=[C_ALT if d > 0 else C_BASE for d in p.mean_diff],
              error_x=dict(type="data", symmetric=False, array=100 * (p.ci_high - p.mean_diff) / base,
                           arrayminus=100 * (p.mean_diff - p.ci_low) / base))
    f.add_vline(x=0, line_color="#222")
    f.update_layout(showlegend=False, margin=dict(l=300, r=20, t=60, b=45))
    f.update_xaxes(title="% change vs baseline  (left = lower in alternative)")
    return f


def tradeoff_chart(b: pd.DataFrame, a: pd.DataFrame, name_b="Baseline", name_a="Alternative") -> go.Figure:
    f = _fig("Trade-off view: infections vs antibiotic use (marker size = screening + isolation workload)",
             "Antibiotic days of therapy /1000 patient-days", "Hospital-onset infections /1000 patient-days", 380)
    for df, name, color, sym in [(b, name_b, C_BASE, "circle"), (a, name_a, C_ALT, "diamond")]:
        work = df.screens + df.isolation_days
        f.add_scatter(x=df.dot_per_1000pd, y=df.hai_per_1000pd, mode="markers", name=name,
                      marker=dict(color=color, symbol=sym, opacity=0.6, size=8 + 18 * work / max(1, work.max()),
                                  line=dict(color="#222", width=0.5)),
                      customdata=np.c_[df.screens, df.isolation_days],
                      hovertemplate="DOT %{x:.0f}<br>Infections %{y:.1f}<br>Screens %{customdata[0]}<br>Isolation-days %{customdata[1]}<extra>" + name + "</extra>")
        f.add_scatter(x=[df.dot_per_1000pd.mean()], y=[df.hai_per_1000pd.mean()], mode="markers", showlegend=False,
                      marker=dict(color=color, symbol=sym + "-open" if sym == "circle" else "diamond-open", size=22, line=dict(width=4)),
                      hovertemplate=name + " mean<extra></extra>")
    return f


def sensitivity_chart(df: pd.DataFrame, param: str, metric: str) -> go.Figure:
    f = _fig(f"Sensitivity: {METRIC_LABELS[metric]} vs {param}", param, METRIC_LABELS[metric], 340)
    f.add_scatter(x=df.value, y=df.high, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip")
    f.add_scatter(x=df.value, y=df.low, mode="lines", line=dict(width=0), fill="tonexty",
                  fillcolor="rgba(0,114,178,0.18)", name="2.5-97.5 percentile of replicates")
    f.add_scatter(x=df.value, y=df["mean"], mode="lines+markers", name="Mean", line=dict(color=C_BASE, width=3))
    return f
