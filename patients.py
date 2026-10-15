"""Synthetic patient generation and state. ALL DATA ARE SYNTHETIC - no real patients."""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np

# Patient states
SUSCEPTIBLE = "Susceptible"
COLONIZED = "Colonized"
INFECTED = "Infected"
STATES = (SUSCEPTIBLE, COLONIZED, INFECTED)

# Organism status
NONE = "None"
SENSITIVE = "Sensitive"
RESISTANT = "Resistant"


@dataclass
class Patient:
    pid: str
    bed: int
    state: str = SUSCEPTIBLE
    organism: str = NONE
    on_antibiotic: bool = False
    course_left: int = 0              # days of current antibiotic course remaining
    antibiotic_days: int = 0          # cumulative days of therapy during this stay
    isolated: bool = False
    detected: bool = False            # found by surveillance / clinical recognition
    risk: float = 1.0                 # synthetic relative susceptibility (0.5-2.0)
    los: int = 0                      # days in ward
    events: list = field(default_factory=list)

    def log(self, day: int, text: str) -> None:
        self.events.append((day, text))

    def validate(self) -> None:
        if self.state not in STATES:
            raise ValueError(f"{self.pid}: invalid state {self.state}")
        if self.state == SUSCEPTIBLE and self.organism != NONE:
            raise ValueError(f"{self.pid}: susceptible patient carries organism")
        if self.state != SUSCEPTIBLE and self.organism not in (SENSITIVE, RESISTANT):
            raise ValueError(f"{self.pid}: colonized/infected patient lacks organism")
        if self.isolated and not self.detected:
            raise ValueError(f"{self.pid}: isolation requires detection")
        if self.on_antibiotic and self.course_left < 0:
            raise ValueError(f"{self.pid}: negative antibiotic course")


def make_patient(pid: str, bed: int, rng_vals, day: int, import_prev: float,
                 import_res_frac: float) -> Patient:
    """Create one synthetic admission from pre-drawn random values (u_carry, u_res, z_risk)."""
    u_carry, u_res, z = rng_vals
    p = Patient(pid=pid, bed=bed, risk=float(np.clip(np.exp(0.25 * z), 0.5, 2.0)))
    if u_carry < import_prev:
        p.state = COLONIZED
        p.organism = RESISTANT if u_res < import_res_frac else SENSITIVE
        p.log(day, f"Admitted already colonized ({p.organism.lower()} organism)")
    else:
        p.log(day, "Admitted (no known carriage)")
    return p


def generate_patients(n: int, rng: np.random.Generator, import_prev: float = 0.08,
                      import_res_frac: float = 0.3) -> list[Patient]:
    """Create a synthetic ward. Same rng seed -> identical ward."""
    if not (1 <= n <= 200):
        raise ValueError("n_patients must be between 1 and 200")
    vals = rng.random((n, 2))
    zs = rng.standard_normal(n)
    return [make_patient(f"SYN-{i+1:03d}", i, (vals[i, 0], vals[i, 1], zs[i]), 0,
                         import_prev, import_res_frac) for i in range(n)]
