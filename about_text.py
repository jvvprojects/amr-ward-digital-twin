"""Text shown on the About / Methods tab (kept out of app.py)."""

METHODS_MD = """
### How the model works (one simulated day = one step)

**Ward.** A fixed number of beds, each holding a *synthetic* patient (state: Susceptible / Colonized / Infected; organism: none / sensitive / resistant).
Patients are discharged with daily probability 1/average-stay (or leave after a simulated adverse outcome) and the bed is refilled by a new synthetic admission, so denominators stay stable.

**Contact network.** `n_staff = max(2, n_patients // 4)` staff each make `contact_rate` visits per day. *Shared* staff pick any bed; *cohorted* staff pick from their own block of beds, except 10% of visits that cross blocks.
This produces a staff-patient bipartite contact network; the patient-to-patient pathways it creates are drawn on the ward map.

**Visit rule (staff-mediated transmission only).** For each visit:
1. *Hand hygiene (moment 1)*: with probability `hand_hygiene`, hands are cleaned and contamination is removed with probability `hh_efficacy`.
2. *Delivery*: if hands are contaminated and the patient is susceptible, colonization occurs with probability
   `P = min(1, base_transmission x risk x (1 + boost if on antibiotic) x (1 - abx_kill if the organism is sensitive and the patient is on antibiotic))`.
3. *Pickup*: if the patient carries an organism, hands become contaminated with probability `pickup_prob x barrier`, where `barrier = 1 - isolation_effectiveness` if the patient is isolated and precautions are applied (probability `isolation_compliance`), otherwise 1.
4. *Hand hygiene (moment 4)* as in step 1.

**Antibiotics and stewardship.** Each day a patient not on antibiotics has a prescribing decision with probability `prescribe_rate`; a fraction `inappropriate_fraction` of decisions are "not indicated". Stewardship avoids an unindicated prescription with probability `stewardship_compliance`; remaining courses last `round(7 - 3 x stewardship)` days. Infected patients are treated for 7 days.
**Selection pressure.** While on antibiotics, a sensitive carrier converts to resistant with daily probability `selection_pressure`.

**Disease course.** Colonized to infected: `0.03 x risk x (1.5 if on antibiotic)` per day; natural clearance 2%/day. Infection recovers faster when a sensitive organism is treated (25%/day) than a resistant one (7%/day) or untreated (5%/day); daily adverse-outcome probability 0.5% (sensitive) or 2% (resistant).

**Surveillance.** Each undetected patient is screened with probability `surveillance_intensity` (sensitivity 70%); infected patients are also recognised clinically (40%/day). Detected *resistant* carriers are isolated if isolation is enabled.

**Indicators.** Rates per 1000 patient-days use cumulative patient-days as denominator. "Hospital-onset infection" = onset on ward day 3 or later (a simulation rule, **not** a clinical surveillance definition). Observed hand-hygiene and isolation compliance are measured from simulated opportunities.

### Reproducibility and uncertainty
Every mechanism has its own random stream spawned from the seed and draws a fixed-size block per day. Two configurations run with the same seed therefore share the same starting ward and largely the same random numbers (**common random numbers**), which reduces noise in paired comparisons without removing it.
The *Scenario lab* runs many replicates (seed, seed+1, ...), reports mean, 2.5-97.5 percentile range across replicates, and a 95% percentile-bootstrap interval for the **paired** mean difference.

### Parameter status
All numeric parameters are **illustrative** choices that make the mechanisms visible; none is a validated clinical estimate. They could be calibrated against local surveillance data (colonization pressure, acquisition rates, antibiotic days of therapy) and tested with sensitivity analysis, which the app includes.
"""

LIMITATIONS_MD = """
- One generic organism; no species, strains, plasmids or environmental reservoirs.
- Staff-mediated transmission only; no direct bed-to-bed, airborne or environmental routes.
- Synthetic patient profiles (a single risk multiplier); no comorbidity, age, devices or surgery.
- Illustrative, uncalibrated parameters; real effect sizes will differ.
- No staffing shortages, workload, costs beyond simple counts, or patient transfers.
- No clinical validation. Results do not generalise to real hospitals and must never guide patient care.
- Interventions need not improve every metric: stewardship barely changes cross-transmission, and detection raises screening and isolation workload.
"""

EVAL_PLAN_MD = """
**A. Verification (done in code):** automated tests check valid patient states, probability bounds, input rejection, seed reproducibility, reset behaviour and that comparisons use the intended configurations. Run `pytest` to repeat.

**B. Sensitivity analysis (in the app):** *Scenario lab -> Sensitivity* sweeps one parameter (e.g. base transmission, hand hygiene, isolation effectiveness, contact rate, selection pressure) with matched seeds. Check that responses follow the stated rules and note any trade-offs.

**C. Proposed educational pilot (not yet conducted - no participant data exist):**
1. Brief pre-test on AMR / stewardship / infection-prevention concepts.
2. Structured 45-minute activity: three challenges plus one self-designed counterfactual comparison.
3. Post-test (parallel items) and the System Usability Scale (SUS) questionnaire; optional free-text feedback.
4. Distinguish: *usability* (SUS), *immediate learning gain* (post minus pre), *retention* (repeat test weeks later) and *clinical competence* (not measured here).
5. Pre-register outcomes, obtain ethics approval, collect no personal identifiers, and report effect sizes with confidence intervals; a control group (standard teaching) would strengthen inference.

**Research question:** *Among undergraduate medical students, does a brief activity with an uncertainty-aware counterfactual ward simulator improve understanding of how stewardship and infection-prevention measures act on different AMR pathways, compared with standard teaching, and is it usable?*
"""

NOVELTY_MD = """
**Status: a comprehensive novelty review is still outstanding.** A quick web search (titles only, not read in full) surfaced related work that should be reviewed before any originality claim:

- Serious electronic games for healthcare-associated infection and infection prevention - scoping review (*Antimicrobial Resistance & Infection Control*, 2016): https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5062920/
- Gamification as an educational tool to address antimicrobial resistance - systematic review: https://ntnuopen.ntnu.no/ntnu-xmlui/handle/11250/3117042
- Using electronic medical records in hospital simulation for infection control intervention assessment: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11883657/
- A digital-twin-based automated surveillance system for infection cluster detection and contact tracing in a tertiary hospital (Cambridge Core): https://www.cambridge.org/core/services/aop-cambridge-core/content/view/BF6BB577A2D6198C9F9A815CE1035842/S2732494X25002402a.pdf/digital-twin-based-automated-surveillance-system-for-infection-cluster-detection-outbreak-mapping-and-contact-tracing-in-a-tertiary-ho.pdf

**What similar work already does (to be confirmed by full reading):** AMR/infection-control serious games and gamified teaching tools exist, and hospital simulation and digital-twin work exists for surveillance and intervention assessment.

**Possible differentiator (a hypothesis, not a finding):** an *educational* tool that makes *uncertainty* and *counterfactual pairing* (matched seeds, replicate distributions, paired intervals) the central learning object, linking antibiotic stewardship and infection prevention in one transparent model with a trade-off view.

**Evidence still needed:** systematic literature search, comparison against existing simulators' features, and an educational pilot showing learners benefit. This project does not claim to be the first of its kind.
"""
