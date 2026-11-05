# Data format

All files are CSV with a header row. Extra columns are ignored. Column names can be remapped for measurements with `COLUMN_MAP` in `run_pipeline.py`.

## locations.csv
`location_id, name, level, type, x, y` (required) · `x1, y1, x2, y2` (optional line segment drawn for an airway) · `airway, district` (optional).
x/y are schematic plan coordinates in metres.

## instruments.csv
`instrument_id, instrument_type, location_id, parameters, status, expected_interval_min` or `stale_after_min` (one required per instrument) · optional `model, serial_no, manufacturer, last_calibration_date, calibration_interval_days, calibration_ref, responsible_party`.
- `parameters`: semicolon list from `air_velocity, airflow, o2, co, co2, no2, h2s, ch4, temperature, humidity`.
- `status`: `in_service`, `out_of_service`, `removed`.
- Portable/handheld instruments: leave `location_id` blank; every reading must then carry a `location_id`.
- Stale rule: no reading for `stale_after_min`, or 3 × `expected_interval_min`.

## review_criteria.csv  (supplied by qualified personnel)
`criterion_id, parameter, comparator (> >= < <=), threshold, unit, name, source_reference, approved_by, approval_date` (all required) · optional `location_id` (blank = all locations), `location_type, procedure_reference, effective_from, effective_to`.
Rows missing a source, approver or date are **rejected**. Approvers beginning "SYNTHETIC" mark the file as demo and trigger the red banner. An empty file is allowed: nothing is then flagged and every channel is `NO_CRITERIA_CONFIGURED`.

## measurements*.csv and manual_entries/*.csv
`timestamp, instrument_id, parameter, value, unit` · optional `quality, source (sensor|manual), entered_by, comment, location_id`.
Timestamps are interpreted in `site_timezone` (config) unless they carry an offset.

## Channel states (most to least attention)
`CRITERION_MET` · `STALE` · `NO_DATA` · `OUT_OF_SERVICE` · `QUALITY_CONCERN` · `NO_CRITERIA_CONFIGURED` · `NO_CRITERION_MET` ("latest readings meet no configured criterion"; not a statement that conditions are safe).

## Reading flags
`IMPLAUSIBLE_VALUE, SUPPLIED_BAD, SUPPLIED_SUSPECT, DUPLICATE_CONFLICT, POSSIBLE_FLATLINE, CALIBRATION_OVERDUE, UNIT_MISSING, UNIT_UNRECOGNISED_OR_MISMATCH`.

## Manual entry workflow
1. `python make_manual_entry_form.py` (also written by `run_pipeline.py`) → `outputs/manual_entry_form.html`.
2. Open it on a laptop/tablet; it works with no network and keeps entries in the browser until exported.
3. Export CSV, copy it to `<INPUT_DIR>/manual_entries/`, run `run_pipeline.py`. The form validates entries only; it never evaluates criteria.
