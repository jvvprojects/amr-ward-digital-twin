"""Core rule-based simulation engine for the AMR-Ward Digital Twin.

EDUCATIONAL MODEL - all parameters are ILLUSTRATIVE, not clinically validated.
See README.md ("Scientific methodology") for equations and assumptions.

Time step = 1 simulated day. Each day:
  1. Staff-mediated contacts (hand hygiene, isolation barrier, pickup, delivery)
  2. Antibiotic prescribing/stewardship, selection pressure, disease progression,
     discharge/admission (fixed bed count, so denominators stay constant)
  3. Surveillance and isolation of detected resistant carriers
  4. Indicator recording

Reproducibility: every mechanism has its own random stream (spawned from the seed) and
draws a FIXED-size block each day, so two configurations run with the same seed share
the same synthetic ward and largely the same random numbers (common random numbers).
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, fields
import math
import numpy as np
import pandas as pd

from patients import (Patient, generate_patients, make_patient, SUSCEPTIBLE, COLONIZED,
                      INFECTED, NONE, SENSITIVE, RESISTANT)

MAX_VISITS = 20
CLEARANCE_PROB = 0.02          # daily natural clearance of colonization (illustrative)
INFECTION_BASE = 0.03          # daily colonized -> infected, scaled by patient risk (illustrative)
INFECTION_ABX_BOOST = 0.5      # antibiotics disrupt flora: +50% infection risk (illustrative)
RECOVERY = {"sens_abx": 0.25, "res_abx": 0.07, "no_abx": 0.05}   # daily recovery (illustrative)
MORTALITY = {SENSITIVE: 0.005, RESISTANT: 0.02}                  # daily adverse outcome (illustrative)
SCREEN_SENSITIVITY = 0.7
CLINICAL_DETECTION = 0.4       # daily probability an infected patient is recognised clinically
COHORT_LEAK = 0.10             # fraction of visits crossing cohorts when staff are cohorted
BASE_COURSE_DAYS = 7
HAI_MIN_DAY = 3                # infection onset on hospital day >=3 counts as hospital-onset

# name: (low, high, kind) - the permitted range of every parameter
BOUNDS = {
    "n_patients": (4, 60, int),
    "days": (3, 120, int),
    "seed": (0, 2**31 - 1, int),
    "hand_hygiene": (0.0, 1.0, float),
    "isolation_compliance": (0.0, 1.0, float),
    "isolation_effectiveness": (0.0, 1.0, float),
    "contact_rate": (1, MAX_VISITS, int),
    "prescribe_rate": (0.0, 0.5, float),
    "inappropriate_fraction": (0.0, 1.0, float),
    "stewardship_compliance": (0.0, 1.0, float),
    "surveillance_intensity": (0.0, 1.0, float),
    "base_transmission": (0.0, 0.3, float),
    "hh_efficacy": (0.5, 1.0, float),
    "pickup_prob": (0.0, 1.0, float),
    "selection_pressure": (0.0, 0.2, float),
    "abx_kill": (0.0, 1.0, float),
    "abx_susceptibility_boost": (0.0, 2.0, float),
    "avg_los": (3.0, 60.0, float),
    "import_prevalence": (0.0, 0.5, float),
    "import_resistant_fraction": (0.0, 1.0, float),
}
STRUCTURES = ("shared", "cohorted")


@dataclass
class SimConfig:
    # --- user-facing intervention controls ---
    n_patients: int = 24
    days: int = 30
    seed: int = 42
    hand_hygiene: float = 0.55            # adherence per opportunity (before AND after each visit)
    isolation_enabled: bool = True
    isolation_compliance: float = 0.6     # probability staff apply barrier precautions
    isolation_effectiveness: float = 0.7  # reduction in pickup when precautions applied
    contact_rate: int = 12                # patient visits per staff member per day
    contact_structure: str = "shared"     # "shared" staff or "cohorted" staff
    prescribe_rate: float = 0.10          # daily prescribing decision probability per patient
    inappropriate_fraction: float = 0.35  # share of decisions that are not indicated (illustrative)
    stewardship_compliance: float = 0.2   # probability an unnecessary prescription is avoided; also shortens courses
    surveillance_intensity: float = 0.2   # daily screening probability per undetected patient
    # --- advanced / illustrative biological assumptions ---
    base_transmission: float = 0.15       # P(delivery) per visit with contaminated hands, risk = 1
    hh_efficacy: float = 0.9
    pickup_prob: float = 0.3
    selection_pressure: float = 0.06
    abx_kill: float = 0.5
    abx_susceptibility_boost: float = 0.5
    avg_los: float = 10.0
    import_prevalence: float = 0.15
    import_resistant_fraction: float = 0.3

    def validate(self) -> None:
        for name, (lo, hi, kind) in BOUNDS.items():
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, (int, float, np.integer, np.floating)):
                raise ValueError(f"{name} must be a number, got {v!r}")
            if isinstance(v, float) and not math.isfinite(v):
                raise ValueError(f"{name} must be finite")
            if kind is int and int(v) != v:
                raise ValueError(f"{name} must be a whole number")
            if not (lo <= v <= hi):
                raise ValueError(f"{name}={v} is outside the permitted range [{lo}, {hi}]")
        if not isinstance(self.isolation_enabled, (bool, np.bool_)):
            raise ValueError("isolation_enabled must be true/false")
        if self.contact_structure not in STRUCTURES:
            raise ValueError(f"contact_structure must be one of {STRUCTURES}")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SimConfig":
        if not isinstance(d, dict):
            raise ValueError("configuration must be a dictionary")
        known = {f.name for f in fields(cls)}
        unknown = set(d) - known
        if unknown:
            raise ValueError(f"unknown parameters: {sorted(unknown)}")
        clean = {}
        for k, v in d.items():
            if k in BOUNDS and BOUNDS[k][2] is int and isinstance(v, float) and v == int(v):
                v = int(v)
            clean[k] = v
        cfg = cls(**clean)
        cfg.validate()
        return cfg

    def replace(self, **kw) -> "SimConfig":
        d = self.to_dict(); d.update(kw)
        return SimConfig.from_dict(d)


class WardSimulation:
    """A synthetic hospital ward that evolves in discrete daily steps."""

    def __init__(self, config: SimConfig):
        config.validate()
        self.cfg = config
        self._init()

    # ------------------------------------------------------------------ setup
    def _init(self) -> None:
        c = self.cfg
        kids = np.random.SeedSequence(c.seed).spawn(6)
        (self.r_ward, self.r_contact, self.r_hyg, self.r_abx, self.r_prog,
         self.r_surv) = [np.random.default_rng(k) for k in kids]
        self.r_adm = np.random.default_rng(np.random.SeedSequence(c.seed).spawn(7)[6])
        self.day = 0
        self.patients: list[Patient] = generate_patients(
            c.n_patients, self.r_ward, c.import_prevalence, c.import_resistant_fraction)
        n = c.n_patients
        self.n_staff = max(2, n // 4)
        self.cohorts = [[i for i in range(n) if i * self.n_staff // n == s] for s in range(self.n_staff)]
        self.next_id = n + 1
        # cumulative counters
        self.k = dict(patient_days=0, dot=0, started=0, appropriate=0, inappropriate=0,
                      blocked=0, hh_opp=0, hh_done=0, iso_opp=0, iso_done=0,
                      acquisitions=0, res_acquisitions=0, infections=0, res_infections=0,
                      hai=0, res_hai=0, adverse=0, selections=0, screens=0, iso_days=0,
                      discharges=0)
        self.transmissions: list[dict] = []
        self.history: list[dict] = []
        self.initial_snapshot = self.snapshot()
        self._record(0, {})

    def reset(self) -> None:
        """Restore the exact initial state for this configuration and seed."""
        self._init()

    # ------------------------------------------------------------------ step
    def step(self) -> bool:
        c = self.cfg
        if self.day >= c.days:
            return False
        self.day += 1
        d = self.day
        n = len(self.patients)
        today = dict(acq=0, res_acq=0, inf=0, res_inf=0, hai=0)
        self._contacts(d, today)
        self._clinical(d, today)
        self._surveillance(d)
        self.k["patient_days"] += n
        self.k["iso_days"] += sum(p.isolated for p in self.patients)
        for p in self.patients:
            p.validate()
        self._record(d, today)
        return True

    def run(self) -> pd.DataFrame:
        while self.step():
            pass
        return self.history_df

    # ------------------------------------------------------------- mechanisms
    def _contacts(self, d: int, today: dict) -> None:
        c = self.cfg
        n = len(self.patients)
        ns = self.n_staff
        U = self.r_hyg.random((ns, MAX_VISITS, 7))   # pre-hyg, pre-eff, post-hyg, post-eff, iso, pickup, deliver
        V = self.r_contact.random((ns, MAX_VISITS, 2))
        for s in range(ns):
            org, src = NONE, None                     # staff hands are cleaned at start of shift
            cohort = self.cohorts[s]
            for v in range(c.contact_rate):
                u = U[s, v]
                if c.contact_structure == "cohorted" and cohort and V[s, v, 1] >= COHORT_LEAK:
                    pool = cohort
                else:
                    pool = range(n)
                p = self.patients[pool[int(V[s, v, 0] * len(pool))]]
                # Moment 1: hand hygiene before contact
                self.k["hh_opp"] += 1
                if u[0] < c.hand_hygiene:
                    self.k["hh_done"] += 1
                    if u[1] < c.hh_efficacy:
                        org, src = NONE, None
                carries = p.organism != NONE
                # delivery to a susceptible patient
                if p.state == SUSCEPTIBLE and org != NONE:
                    mult = p.risk
                    if p.on_antibiotic:
                        mult *= 1.0 + c.abx_susceptibility_boost
                        if org == SENSITIVE:
                            mult *= 1.0 - c.abx_kill
                    prob = min(1.0, c.base_transmission * mult)
                    if u[6] < prob:
                        p.state, p.organism = COLONIZED, org
                        p.log(d, f"Acquired {org.lower()} organism via staff S{s+1:02d}")
                        self.k["acquisitions"] += 1; today["acq"] += 1
                        if org == RESISTANT:
                            self.k["res_acquisitions"] += 1; today["res_acq"] += 1
                        self.transmissions.append(dict(day=d, source=src, staff=f"S{s+1:02d}",
                                                       target=p.pid, organism=org))
                # pickup from a carrier (isolation barrier precautions reduce it)
                if carries:
                    barrier = 1.0
                    if p.isolated:
                        self.k["iso_opp"] += 1
                        if u[4] < c.isolation_compliance:
                            self.k["iso_done"] += 1
                            barrier = 1.0 - c.isolation_effectiveness
                    if u[5] < c.pickup_prob * barrier:
                        org, src = p.organism, p.pid
                # Moment 4: hand hygiene after contact
                self.k["hh_opp"] += 1
                if u[2] < c.hand_hygiene:
                    self.k["hh_done"] += 1
                    if u[3] < c.hh_efficacy:
                        org, src = NONE, None

    def _clinical(self, d: int, today: dict) -> None:
        c = self.cfg
        n = len(self.patients)
        A = self.r_abx.random((n, 3))
        P = self.r_prog.random((n, 5))   # progression, recovery, adverse, selection, discharge
        M = self.r_adm.random((n, 2))
        Z = self.r_adm.standard_normal(n)
        for i in range(n):
            p = self.patients[i]
            p.los += 1
            a, u = A[i], P[i]
            # --- antibiotic course / prescribing / stewardship
            if p.on_antibiotic:
                self.k["dot"] += 1; p.antibiotic_days += 1; p.course_left -= 1
                if p.course_left <= 0:
                    p.on_antibiotic = False; p.course_left = 0
                    p.log(d, "Antibiotic course completed")
            elif a[0] < c.prescribe_rate:
                inappropriate = a[1] < c.inappropriate_fraction
                if inappropriate and a[2] < c.stewardship_compliance:
                    self.k["blocked"] += 1
                    p.log(d, "Unnecessary prescription avoided (stewardship)")
                else:
                    self._start_abx(p, d, appropriate=not inappropriate)
            # --- selection pressure on carried organism
            if p.on_antibiotic and p.organism == SENSITIVE and u[3] < c.selection_pressure:
                p.organism = RESISTANT
                self.k["selections"] += 1
                p.log(d, "Selection of resistance under antibiotic pressure")
            # --- disease progression
            leaving = False
            if p.state == COLONIZED:
                p_inf = min(1.0, INFECTION_BASE * p.risk * (1 + (INFECTION_ABX_BOOST if p.on_antibiotic else 0)))
                if u[0] < p_inf:
                    p.state = INFECTED
                    self.k["infections"] += 1; today["inf"] += 1
                    if p.organism == RESISTANT:
                        self.k["res_infections"] += 1; today["res_inf"] += 1
                    if p.los >= HAI_MIN_DAY:
                        self.k["hai"] += 1; today["hai"] += 1
                        if p.organism == RESISTANT:
                            self.k["res_hai"] += 1
                    p.log(d, f"Developed {p.organism.lower()} infection")
                    if not p.on_antibiotic:
                        self._start_abx(p, d, appropriate=True, treatment=True)
                elif u[0] < p_inf + CLEARANCE_PROB:
                    p.state, p.organism = SUSCEPTIBLE, NONE
                    p.detected = p.isolated = False
                    p.log(d, "Colonization cleared")
            elif p.state == INFECTED:
                if p.organism == SENSITIVE and p.on_antibiotic:
                    rec = RECOVERY["sens_abx"]
                elif p.organism == RESISTANT and p.on_antibiotic:
                    rec = RECOVERY["res_abx"]
                else:
                    rec = RECOVERY["no_abx"]
                if u[1] < rec:
                    p.state = COLONIZED
                    p.log(d, "Infection resolved (remains colonized)")
                elif u[2] < MORTALITY[p.organism]:
                    self.k["adverse"] += 1
                    p.log(d, "Simulated adverse outcome")
                    leaving = True
            if not leaving and u[4] < 1.0 / c.avg_los:
                leaving = True
                p.log(d, "Discharged")
            if leaving:
                self.k["discharges"] += 1
                self.patients[i] = make_patient(f"SYN-{self.next_id:03d}", p.bed,
                                                (M[i, 0], M[i, 1], Z[i]), d,
                                                c.import_prevalence, c.import_resistant_fraction)
                self.next_id += 1

    def _start_abx(self, p: Patient, d: int, appropriate: bool, treatment: bool = False) -> None:
        c = self.cfg
        dur = BASE_COURSE_DAYS if treatment else max(3, int(round(BASE_COURSE_DAYS - 3 * c.stewardship_compliance)))
        p.on_antibiotic, p.course_left = True, dur
        self.k["started"] += 1
        self.k["appropriate" if appropriate else "inappropriate"] += 1
        p.log(d, "Antibiotic started" + (" (treatment)" if treatment else
                                         " (indicated)" if appropriate else " (not indicated)"))

    def _surveillance(self, d: int) -> None:
        c = self.cfg
        n = len(self.patients)
        S = self.r_surv.random((n, 2))
        for i, p in enumerate(self.patients):
            if p.detected:
                continue
            screened = S[i, 1] < c.surveillance_intensity
            if screened:
                self.k["screens"] += 1
            found = p.organism != NONE and (
                (screened and S[i, 0] < SCREEN_SENSITIVITY) or
                (p.state == INFECTED and S[i, 0] < CLINICAL_DETECTION))
            if found:
                p.detected = True
                p.log(d, f"Detected ({p.organism.lower()} organism)")
                if c.isolation_enabled and p.organism == RESISTANT:
                    p.isolated = True
                    p.log(d, "Placed in isolation")

    # ------------------------------------------------------------- reporting
    def counts(self) -> dict:
        pts = self.patients
        return dict(
            susceptible=sum(p.state == SUSCEPTIBLE for p in pts),
            colonized=sum(p.state == COLONIZED for p in pts),
            infected=sum(p.state == INFECTED for p in pts),
            resistant_carriers=sum(p.organism == RESISTANT for p in pts),
            sensitive_carriers=sum(p.organism == SENSITIVE for p in pts),
            on_antibiotic=sum(p.on_antibiotic for p in pts),
            isolated=sum(p.isolated for p in pts),
            detected=sum(p.detected for p in pts))

    def _record(self, d: int, today: dict) -> None:
        k, n = self.k, len(self.patients)
        row = dict(day=d, patients=n, **self.counts())
        row.update(
            new_acquisitions=today.get("acq", 0), new_resistant_acquisitions=today.get("res_acq", 0),
            new_infections=today.get("inf", 0), new_resistant_infections=today.get("res_inf", 0),
            new_hai=today.get("hai", 0),
            cum_acquisitions=k["acquisitions"], cum_resistant_acquisitions=k["res_acquisitions"],
            cum_infections=k["infections"], cum_resistant_infections=k["res_infections"],
            cum_hai=k["hai"], cum_dot=k["dot"], cum_adverse=k["adverse"],
            cum_selections=k["selections"], cum_screens=k["screens"], cum_isolation_days=k["iso_days"],
            cum_inappropriate=k["inappropriate"], cum_blocked=k["blocked"],
            observed_hand_hygiene=(k["hh_done"] / k["hh_opp"]) if k["hh_opp"] else np.nan,
            observed_isolation=(k["iso_done"] / k["iso_opp"]) if k["iso_opp"] else np.nan,
            observed_stewardship=(k["appropriate"] / k["started"]) if k["started"] else np.nan,
            patient_days=k["patient_days"])
        self.history.append(row)

    @property
    def history_df(self) -> pd.DataFrame:
        return pd.DataFrame(self.history)

    def snapshot(self) -> list[dict]:
        return [dict(pid=p.pid, bed=p.bed, state=p.state, organism=p.organism,
                     on_antibiotic=p.on_antibiotic, isolated=p.isolated, detected=p.detected,
                     risk=round(p.risk, 3), los=p.los) for p in self.patients]

    def patient_table(self) -> pd.DataFrame:
        return pd.DataFrame(self.snapshot())
