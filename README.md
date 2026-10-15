# AMR-Ward Digital Twin

An interactive teaching simulation of a hospital ward for **antimicrobial stewardship** and **infection prevention**.
Change hand hygiene, isolation, surveillance and antibiotic prescribing, then watch simulated transmission, resistance and antibiotic use respond - and compare interventions **with uncertainty**, not from a single lucky run.

> **Everything is simulated.** All patients, events and indicators come from a rule-based educational model on synthetic data with *illustrative* parameters. It is **not clinically validated**, not a forecasting tool, and must never be used for real patient care or hospital decisions. No real data are read, stored or sent anywhere; the app runs entirely on your computer.

---

## 1. Start it (Windows 10/11) - no commands needed

1. Unzip the folder anywhere (e.g. your Desktop).
2. **Double-click `START_AMR_DIGITAL_TWIN.bat`.**
3. A black window opens. **First time only** it prepares itself and downloads its components (needs internet, about 2-5 minutes). Later starts take seconds and work offline.
4. Your web browser opens the app automatically. **Keep the black window open** while you use it.
5. To quit, close the browser tab and then close the black window.

**If Python is not installed**, the launcher offers to install it for you (Windows Package Manager), or tells you exactly what to do (install Python 3.12 from python.org and tick *Add python.exe to PATH*). If something fails, the launcher says so in plain words and saves details to the `logs` folder.

> Status: the launcher script could not be run on Windows by its author (written on Linux). The Python launcher (`run_app.py`) and the whole app *were* started and tested on Linux. Please report any Windows-specific problem from `logs\startup_log.txt`.

## 2. First demonstration (3 minutes)

1. Open **Scenario lab**.
2. Baseline = *1. Baseline ward practices*; Alternative = *2. Improved hand hygiene*; Replicates = 30. Press **Run comparison**.
3. Read the table: each row shows baseline mean, alternative mean, the **paired difference** with a 95% interval, and in what % of runs the alternative was lower.
4. Look at the **trade-off** chart and the **Explanation** box (what changed, which mechanism, what you cannot conclude).
5. Now try *4. Improved antimicrobial stewardship* as the alternative. Notice which indicators move (antibiotic use) and which barely do (transmission). Not every intervention improves every metric.
6. Go to **Ward overview** and press **Start** to watch one simulated ward evolve day by day, and **Ward map** to click a patient and see the event history and transmission pathways.

## 3. What is in the app

| Tab | What it does |
|---|---|
| Ward overview | Live indicators, trends, Start / Advance 1 day / Run to the end / Reset / Repeat with next seed |
| Ward map | Synthetic beds (shape + label + colour), patient inspection, transmission pathways |
| Scenario lab | Six preset scenarios, matched-seed baseline-vs-alternative comparison with replicates, uncertainty, trade-off view, explanation, sensitivity sweeps |
| Learning challenges | Three hypothetical ward situations: predict, intervene, see modelled consequences, principle and reflection question |
| Export & experiments | Save/load scenarios (validated JSON), CSV exports, summary report, experiment record that reproduces a run |
| Methods & limits | Equations, assumptions, limitations, evaluation plan, novelty status |

Sidebar controls (all have an effect on the model): hand hygiene, isolation (on/off, compliance, effectiveness), surveillance intensity, stewardship compliance, prescribing rate and share not indicated, number of patients, duration, staff contacts, staff structure (shared/cohorted), random seed, plus advanced assumptions.

## 4. Scientific methodology (summary - full text in the app's *Methods & limits* tab)

* One simulated day per step. Fixed beds; discharges are replaced by new synthetic admissions, so denominators are stable.
* **Contact network:** staff x patients. Each staff member makes `contact_rate` visits per day (shared or cohorted).
* **Visit rule:** hand hygiene (before) -> delivery `P = min(1, beta x risk x (1 + boost if on antibiotic) x (1 - kill if sensitive & on antibiotic))` -> pickup `pickup x (1 - isolation_effectiveness if precautions applied)` -> hand hygiene (after).
* **Antibiotics:** prescribing decisions at `prescribe_rate`; a share are "not indicated"; stewardship avoids them with probability `stewardship_compliance` and shortens courses. **Selection pressure:** on antibiotics, sensitive carriage becomes resistant with daily probability `selection_pressure`.
* **Surveillance:** screening with intensity and 70% sensitivity (+ clinical recognition of infection); detected resistant carriers are isolated if isolation is enabled.
* **Indicators:** rates per 1000 cumulative patient-days; "hospital-onset infection" = onset on ward day >= 3 (a simulation rule, not a clinical definition).
* **Reproducibility:** each mechanism has its own random stream spawned from the seed with fixed-size daily draws. Same seed + settings = identical results. Two configurations with the same seed share the same starting ward and mostly the same random numbers (**common random numbers**).
* **Uncertainty:** replicates use seeds `s, s+1, ...`; the app reports mean, 2.5-97.5 percentile across replicates, and a percentile-bootstrap 95% CI for the **paired** mean difference.
* **All parameters are illustrative.** They could be calibrated to local surveillance data (colonization pressure, acquisition rate, days of therapy) and stress-tested with the sensitivity tool.

## 5. Primary research innovation (and what is *not* claimed)

**An uncertainty-aware, counterfactual intervention laboratory for AMR education:** baseline and alternative interventions are run on identical synthetic wards with matched seeds, repeated, and compared as distributions with paired intervals, with an automatic plain-language explanation of mechanisms, assumptions and what cannot be concluded; plus a transmission-pathway view and a trade-off view (infections vs antibiotic use vs screening/isolation workload).

**Novelty is not established.** AMR serious games, gamified teaching tools and hospital digital-twin/simulation work already exist (see the *Novelty status* box in the app for the titles found). A systematic literature review is still outstanding; the differentiator above is a hypothesis to be tested, not a finding.

## 6. Testing

```
pip install pytest
python -m pytest -q
```
37 engine/analytics/scenario tests check: valid patient states and counts at every step, probability bounds, rejection of invalid inputs, seed reproducibility, reset behaviour, matched initial wards, that each control changes the mechanism it should (hand hygiene, stewardship, isolation, surveillance, selection pressure), that comparisons use the intended configurations, and safe scenario-file handling. `tests/test_app_smoke.py` drives the Streamlit UI headlessly.

## 7. Evaluation plan (not yet conducted - no participant data exist)

* **Verification:** automated tests (above).
* **Sensitivity analysis:** *Scenario lab -> Sensitivity*; check responses follow the stated rules and look for trade-offs.
* **Educational pilot (proposed):** pre-test -> structured activity -> post-test + System Usability Scale + optional feedback; distinguish usability, immediate learning gain, retention and clinical competence (not measured). Ethics approval, no identifiers, pre-registered outcomes, ideally a control group.
* **Research question:** *Among undergraduate medical students, does a brief activity with an uncertainty-aware counterfactual ward simulator improve understanding of how stewardship and infection-prevention measures act on different AMR pathways, compared with standard teaching, and is it usable?*

## 8. Limitations

One generic organism; staff-mediated transmission only; synthetic patients with a single risk multiplier; uncalibrated illustrative parameters; no staffing, cost or transfer effects; no clinical validation; results do not generalise to real hospitals.

## 9. Optional: standalone Windows app (no Python for the end user)

`build_windows.bat` (run **on Windows, on a developer machine**) builds a PyInstaller folder app. **It has not been run or tested** - no `.exe` is included in this package. Expect to iterate: Streamlit needs `--collect-all streamlit` and package metadata (already in the script); the first start of a packaged app is slow; unsigned executables can trigger SmartScreen/antivirus warnings; a web browser is still required because the interface is shown in the browser; saved scenarios/reports go to `Documents`-independent `%USERPROFILE%\AMR_Ward_Digital_Twin_Data`.

## 10. Files

```
AMR_Ward_Digital_Twin/
  START_AMR_DIGITAL_TWIN.bat   one-click launcher (Windows)
  build_windows.bat            optional PyInstaller build (untested)
  run_app.py                   starts the server on a free port and opens the browser
  app.py                       Streamlit interface
  simulation.py                core engine (SimConfig, WardSimulation)
  patients.py                  synthetic patients and state validation
  scenarios.py                 presets, validated save/load
  analytics.py                 outcomes, replicates, paired comparison, sensitivity
  visualizations.py            Plotly charts and ward map
  education.py                 learning challenges
  reporting.py                 explanations, reports, experiment records
  about_text.py                methods / limitations / evaluation / novelty text
  requirements.txt
  tests/                       pytest suite
  data/                        example scenario file (saved scenarios go here)
  reports/                     exported reports
```

## 11. Troubleshooting

* *Black window closes immediately* - run it again and read the message; see `logs\startup_log.txt` and `logs\app_log.txt`.
* *Browser did not open* - the black window prints the address (e.g. `http://127.0.0.1:8501`); type it in the browser.
* *Windows Firewall prompt* - the app only listens on your own computer (127.0.0.1); you can choose *Cancel*.
