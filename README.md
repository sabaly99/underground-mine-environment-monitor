# underground-mine-environment-monitor

An offline-capable **reporting and visualisation** tool for underground mine ventilation and environmental measurements: air velocity, airflow, oxygen, gases, temperature and humidity, each with a timestamp, monitoring location and instrument identifier.

> ## ⚠ Safety statement (read first)
> This is **not** a gas monitoring system, alarm, ventilation control or emergency-response system and must never replace one.
> - Do **not** connect it to live mine control equipment. It only reads files you give it.
> - It **does not set or invent safety limits.** "Review criteria" are loaded only from `review_criteria.csv`, and every criterion must name its `source_reference`, `approved_by` and `approval_date` or the file is rejected. Use limits supplied and approved by qualified personnel.
> - **Missing, stale, out-of-service and unevaluable data are never shown as safe.** A channel with no recent reading is `STALE` / `NO_DATA`; a location with no instrument is `NO_DATA`; a parameter with no criterion is `NO_CRITERIA_CONFIGURED`. The best status the tool will ever show is *"latest readings meet no configured criterion"*. It never says "safe".
> - The bundled demo criteria are **synthetic placeholders** ("NOT A LIMIT"). Every report and dashboard shows a red banner while they are in use.

## What it does
| Requirement | Where |
|---|---|
| Measurements on a mine-level map/schematic | Map & status tab (shapes + colour; missing data look different from OK) |
| Measurement histories | Histories tab: gaps shaded, flagged readings marked, approved criteria drawn |
| Missing or stale observations | Stale/no-data states, gap table, availability heatmap |
| Readings meeting configured review criteria | Review events table (consecutive runs, active/closed, peak, quality flags) |
| Instrument identifiers and calibration metadata | Instruments & calibration tab; time-aware `CALIBRATION_OVERDUE` flag |
| Reports for the ventilation/environmental team | `outputs/environment_report.html` (print to PDF from a browser) |
| Offline-first manual entry (optional) | `outputs/manual_entry_form.html` → export CSV → `manual_entries/` folder |

**Interface:** grouped sidebar, KPI tiles, channel cards (status pill, freshness bar, latest value, calibration), search (press `/`), and **six themes** selectable in the app: Midnight, Daylight, Ocean, Forest, Sand and High contrast (all text pairs meet WCAG AA contrast). Themes only change appearance; status colours and shapes are identical in every theme, and status is never colour-only.

Three dashboards: a **single-file offline HTML** (double-click, no server), an **offline Dash/Plotly app** (`dashboard_dash.py`, serves its own JavaScript, no internet), and a **Streamlit app**.

## Quick start (demo data)
```bash
pip install -r requirements.txt
python make_demo_data.py        # synthetic data in data/demo
python run_pipeline.py          # analyse, store history, write outputs/
python dashboard_dash.py        # http://127.0.0.1:8050 (offline)
```
Each script has an editable `CONFIG` block at the top; there are no command-line arguments. To use your own data, put your CSVs in a folder, point `INPUT_DIR` at it and follow [docs/DATA_FORMAT.md](docs/DATA_FORMAT.md).

## Data quality handling
Unit normalisation with exact conversions only (ppm↔%vol, m³/min→m³/s, °F→°C; unknown or missing units are flagged, never guessed) · physical plausibility flags (sanity bounds, **not** limits) · supplied bad/suspect quality · duplicate and conflicting timestamps · possible flat-lined sensors · calibration overdue at the time of the reading. Quality flags never hide a reading that meets a criterion.

## Documentation
- [docs/DATA_FORMAT.md](docs/DATA_FORMAT.md): input files and states
- [docs/INSTALL_DEPLOY.md](docs/INSTALL_DEPLOY.md): install, configure, run, Windows launcher, tests
- [docs/HOSTING.md](docs/HOSTING.md): GitHub, local, Docker, sharing (keep real data private)

## Tests
`python -m pytest -q` (48 tests: comparator boundaries, event grouping, gap lengths, missing≠safe, calibration timing, units, loader rejection of unapproved criteria, database idempotence, Dash callbacks, offline self-containment, theme contrast, status-never-colour-only, Streamlit and Dash smoke tests). GitHub Actions runs them on Ubuntu and Windows, Python 3.10–3.13.

## Limitations
Schematic maps are plan-view sketches from the x/y you supply, not survey-accurate. Airflow networks are not modelled (no ventilation simulation). Trend/stale logic depends on the expected intervals you configure per instrument. Real use needs review by qualified ventilation personnel.
