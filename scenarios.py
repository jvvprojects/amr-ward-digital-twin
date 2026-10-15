"""Predefined scenarios and safe save/load of scenario files."""
from __future__ import annotations
import json
import re
from pathlib import Path
from simulation import SimConfig

MAX_FILE_BYTES = 20_000

SCENARIOS = {
    "1. Baseline ward practices": dict(
        overrides={},
        description="Moderate hand hygiene, partial isolation, light stewardship, low surveillance.",
        mechanisms="Reference point. All other scenarios are compared against this."),
    "2. Improved hand hygiene": dict(
        overrides=dict(hand_hygiene=0.85),
        description="Hand-hygiene adherence raised from 55% to 85%.",
        mechanisms="More staff-hand decontamination before and after contact lowers the chance staff carry organisms from one bed to the next (acts on pickup and delivery)."),
    "3. Enhanced isolation": dict(
        overrides=dict(isolation_compliance=0.9, isolation_effectiveness=0.85, surveillance_intensity=0.5),
        description="Better barrier precautions plus more screening so carriers are found sooner.",
        mechanisms="Isolation only works once a resistant carrier is detected, so surveillance and isolation act together: earlier detection and a stronger barrier reduce pickup from known carriers. Costs more screens and isolation-days."),
    "4. Improved antimicrobial stewardship": dict(
        overrides=dict(stewardship_compliance=0.8),
        description="80% of unnecessary prescriptions avoided; courses shortened.",
        mechanisms="Fewer and shorter antibiotic exposures reduce selection pressure (sensitive to resistant), colonization-resistance disruption and infection risk. It does not directly change contact transmission."),
    "5. Combined stewardship + infection prevention": dict(
        overrides=dict(hand_hygiene=0.85, isolation_compliance=0.9, isolation_effectiveness=0.85,
                       surveillance_intensity=0.5, stewardship_compliance=0.8),
        description="All improvements together.",
        mechanisms="Acts on transmission (hand hygiene, isolation, detection) and on selection (stewardship) at once."),
    "6. Suboptimal practices (educational contrast)": dict(
        overrides=dict(hand_hygiene=0.30, isolation_compliance=0.3, isolation_effectiveness=0.5,
                       surveillance_intensity=0.05, stewardship_compliance=0.0, inappropriate_fraction=0.5),
        description="Poor hand hygiene, weak isolation, little surveillance, no stewardship, more unnecessary prescribing.",
        mechanisms="Shows how weak practices on every pathway compound."),
}

PARAM_HELP = {
    "n_patients": "Number of occupied beds (synthetic patients).",
    "days": "Length of the simulated period in days.",
    "hand_hygiene": "Chance staff clean hands at each opportunity (before and after each contact).",
    "isolation_enabled": "Whether detected resistant carriers are isolated at all.",
    "isolation_compliance": "Chance staff actually apply barrier precautions when visiting an isolated patient.",
    "isolation_effectiveness": "How much precautions reduce staff contamination when applied.",
    "contact_rate": "Patient visits per staff member per day (more contacts = more transmission opportunities).",
    "contact_structure": "Shared staff move between any beds; cohorted staff mostly stay with their own group of beds.",
    "prescribe_rate": "Daily chance a patient not on antibiotics has a prescribing decision.",
    "inappropriate_fraction": "Share of prescribing decisions that are not clinically indicated (illustrative).",
    "stewardship_compliance": "Chance an unnecessary prescription is avoided; also shortens courses.",
    "surveillance_intensity": "Daily chance each undetected patient is screened (detection enables isolation).",
}


def make_config(name: str, **extra) -> SimConfig:
    if name not in SCENARIOS:
        raise ValueError(f"unknown scenario {name!r}")
    d = SimConfig().to_dict()
    d.update(SCENARIOS[name]["overrides"])
    d.update(extra)
    return SimConfig.from_dict(d)


def _safe_name(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_\- ]", "", name).strip().replace(" ", "_")[:60]
    if not s:
        raise ValueError("scenario name must contain letters or numbers")
    return s


def save_scenario(name: str, cfg: SimConfig, directory) -> Path:
    cfg.validate()
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{_safe_name(name)}.json"
    path.write_text(json.dumps(dict(name=name, synthetic_only=True, config=cfg.to_dict()), indent=2))
    return path


def parse_scenario_text(text: str) -> tuple[str, SimConfig]:
    """Validate scenario JSON from a file or upload. Data only - nothing is executed."""
    if len(text.encode("utf-8", "ignore")) > MAX_FILE_BYTES:
        raise ValueError("scenario file is too large")
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"not valid JSON: {e}") from None
    if not isinstance(obj, dict) or "config" not in obj:
        raise ValueError("scenario file must contain a 'config' section")
    return str(obj.get("name", "Loaded scenario"))[:80], SimConfig.from_dict(obj["config"])


def load_scenario(path) -> tuple[str, SimConfig]:
    path = Path(path)
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("scenario file is too large")
    return parse_scenario_text(path.read_text(encoding="utf-8"))


def list_saved(directory) -> list[Path]:
    d = Path(directory)
    return sorted(d.glob("*.json")) if d.exists() else []
