"""Educational challenges (hypothetical synthetic wards - no patient-specific advice)."""
from __future__ import annotations

CHALLENGES = [
    dict(
        id="c1",
        title="Challenge 1 - The busy ward with patchy hand hygiene",
        situation=("A synthetic 24-bed ward has high staff workload. Observed hand-hygiene adherence is only about "
                   "35%, and several patients carry a resistant organism. Antibiotic use is typical."),
        base=dict(hand_hygiene=0.35),
        predict="Which single change do you expect to reduce NEW resistant acquisitions the most?",
        options={
            "Raise hand-hygiene adherence to 85%": dict(hand_hygiene=0.85),
            "Strengthen stewardship to 80%": dict(stewardship_compliance=0.8),
            "Increase screening only (no other change)": dict(surveillance_intensity=0.6),
        },
        focus=["acquisitions_per_1000pd", "resistant_acquisitions", "dot_per_1000pd", "screens"],
        principle=("Staff hands link patients. Hand hygiene acts directly on the transmission pathway, so it changes "
                   "acquisitions quickly. Stewardship acts on selection pressure and antibiotic exposure instead, "
                   "so its effect on cross-transmission is small. Screening alone finds carriers but only helps if "
                   "detection leads to isolation precautions that are actually followed."),
        reflection="Which indicators did not move when you chose stewardship? What does that tell you about the pathway it acts on?",
    ),
    dict(
        id="c2",
        title="Challenge 2 - High antibiotic use, many unnecessary prescriptions",
        situation=("A synthetic ward prescribes antibiotics often (about half of prescribing decisions are not indicated) "
                   "and stewardship is absent. Hand hygiene is moderate."),
        base=dict(prescribe_rate=0.14, inappropriate_fraction=0.5, stewardship_compliance=0.0),
        predict="Which action do you expect to lower antibiotic consumption the most?",
        options={
            "Stewardship review avoiding 80% of unnecessary prescriptions": dict(stewardship_compliance=0.8),
            "Raise hand hygiene to 85%": dict(hand_hygiene=0.85),
            "Enhanced isolation with more screening": dict(isolation_compliance=0.9, isolation_effectiveness=0.85,
                                                           surveillance_intensity=0.5),
        },
        focus=["dot_per_1000pd", "inappropriate_prescriptions", "resistant_hai_per_1000pd", "adverse_outcomes"],
        principle=("Antibiotic exposure is the driver of selection pressure in this model. Only stewardship reduces "
                   "unnecessary exposure. Infection-prevention measures reduce spread but leave consumption unchanged, "
                   "so a ward needs both to address both pathways."),
        reflection="Did any option lower infections without lowering antibiotic days? Why might a hospital still need stewardship?",
    ),
    dict(
        id="c3",
        title="Challenge 3 - Isolation without detection",
        situation=("A synthetic ward has a good isolation policy on paper, but surveillance is minimal, so resistant "
                   "carriers are rarely identified."),
        base=dict(surveillance_intensity=0.03, isolation_compliance=0.9, isolation_effectiveness=0.85),
        predict="What will happen if you improve isolation compliance even further, without changing surveillance?",
        options={
            "Raise isolation compliance to 100%": dict(isolation_compliance=1.0),
            "Raise surveillance intensity to 60%": dict(surveillance_intensity=0.6),
            "Do both": dict(isolation_compliance=1.0, surveillance_intensity=0.6),
        },
        focus=["acquisitions_per_1000pd", "resistant_acquisitions", "screens", "isolation_days"],
        principle=("Isolation can only protect patients once a carrier is detected. When surveillance is minimal, "
                   "extra isolation compliance changes very little. Better detection costs more screens and isolation-days, "
                   "which is the resource trade-off hospitals manage."),
        reflection="What extra workload did earlier detection create? How would you decide whether it is worth it?",
    ),
]
