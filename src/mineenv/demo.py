"""SYNTHETIC demonstration data. Every instrument, value and criterion is invented. The review criteria are
placeholders so the dashboard has something to evaluate: they are NOT limits and must never be reused."""
from pathlib import Path

import numpy as np
import pandas as pd

AS_OF = pd.Timestamp("2026-11-04 06:00")

LOCATIONS = [  # id, name, level, type, x, y, x1, y1, x2, y2
    ("A101", "1200L Main Intake", "1200L", "intake_airway", 60, 0, 0, 0, 120, 0),
    ("A102", "1200L Footwall Drift", "1200L", "heading", 120, 40, 120, 0, 120, 80),
    ("A103", "1200L Crosscut 1", "1200L", "heading", 80, 80, 120, 80, 40, 80),
    ("A104", "1200L Return Airway", "1200L", "return_airway", 40, 40, 40, 80, 40, 0),
    ("R101", "1200L Return Raise Collar", "1200L", "raise", 40, 0, 40, 0, 40, 0),
    ("REF1", "1200L Refuge Station", "1200L", "refuge", 95, 40, 95, 40, 95, 40),
    ("B101", "1250L Ramp Entry", "1250L", "intake_airway", 50, 0, 0, 0, 100, 0),
    ("B102", "1250L Stope Drive", "1250L", "heading", 100, 30, 100, 0, 100, 60),
    ("B103", "1250L Return Drive", "1250L", "return_airway", 60, 60, 100, 60, 20, 60),
]
INSTRUMENTS = [  # id, type, model, serial, location, parameters, status, interval, stale_after, last_cal, cal_days, cal_ref
    ("AN-01", "ultrasonic flow station", "DEMO-UFS", "S1001", "A101", "air_velocity;airflow", "in_service", 10, "", "2026-08-20", 180, "CAL-1001"),
    ("GM-01", "fixed multi-gas", "DEMO-MG4", "S2001", "A102", "o2;co;no2", "in_service", 10, "", "2026-10-10", 90, "CAL-2001"),
    ("GM-02", "fixed multi-gas", "DEMO-MG4", "S2002", "A103", "o2;co;ch4", "in_service", 10, "", "2026-09-25", 60, "CAL-2002"),
    ("AN-02", "vane anemometer", "DEMO-VA2", "S1002", "A104", "air_velocity", "in_service", 10, "", "2026-06-01", 365, "CAL-1002"),
    ("GM-03", "fixed multi-gas", "DEMO-MG4", "S2003", "A104", "o2;co", "in_service", 10, "", "2026-09-10", 60, "CAL-2003"),
    ("TH-01", "temperature / humidity", "DEMO-TH1", "S3001", "R101", "temperature;humidity", "in_service", 10, "", "2026-03-01", 365, "CAL-3001"),
    ("GM-04", "fixed multi-gas", "DEMO-MG4", "S2004", "B101", "o2;co", "in_service", 10, "", "2026-09-05", 90, "CAL-2004"),
    ("AN-03", "vane anemometer", "DEMO-VA2", "S1003", "B103", "air_velocity", "in_service", 10, "", "2026-04-20", 180, "CAL-1003"),
    ("GM-05", "fixed multi-gas", "DEMO-MG4", "S2005", "B102", "o2;co;no2", "in_service", 10, "", "2026-10-01", 90, "CAL-2005"),
    ("GM-06", "fixed multi-gas", "DEMO-MG4", "S2006", "B103", "o2;co", "out_of_service", 10, "", "2026-08-01", 90, "CAL-2006"),
    ("HH-01", "handheld multi-gas + anemometer", "DEMO-HH", "S9001", "", "air_velocity;o2;co", "in_service", "", 4320, "", "", ""),
]
CRITERIA = [  # id, parameter, comparator, threshold, unit, name
    ("DEMO-CO-A", "co", ">", 25, "ppm", "DEMO placeholder: CO review level (NOT A LIMIT)"),
    ("DEMO-O2-LOW", "o2", "<", 20.0, "%vol", "DEMO placeholder: low O2 review level (NOT A LIMIT)"),
    ("DEMO-VEL-LOW", "air_velocity", "<", 0.5, "m/s", "DEMO placeholder: low air velocity review level (NOT A LIMIT)"),
    ("DEMO-TEMP-HIGH", "temperature", ">", 28, "degC", "DEMO placeholder: high temperature review level (NOT A LIMIT)"),
    ("DEMO-CH4", "ch4", ">", 0.5, "%vol", "DEMO placeholder: methane review level (NOT A LIMIT)"),
    ("DEMO-NO2", "no2", ">", 2, "ppm", "DEMO placeholder: NO2 review level (NOT A LIMIT)"),
]


def _write_locations(d):
    pd.DataFrame(LOCATIONS, columns=["location_id", "name", "level", "type", "x", "y", "x1", "y1", "x2", "y2"]).to_csv(d / "locations.csv", index=False)


def generate(days=10, seed=7, as_of=AS_OF):
    rng = np.random.default_rng(seed)
    t = pd.date_range(as_of.floor("D") - pd.Timedelta(days=days), as_of - pd.Timedelta(minutes=10), freq="10min")
    n = len(t)
    hrs = (t - t[0]).total_seconds().to_numpy() / 3600
    diurnal = np.asarray(np.sin(2 * np.pi * (t.hour + t.minute / 60 - 6) / 24))
    rows = []

    def add(inst, loc, param, vals, unit, times=t, source="sensor", entered_by="", keep=None):
        v = pd.DataFrame({"timestamp": times.strftime("%Y-%m-%d %H:%M:%S"), "instrument_id": inst, "parameter": param, "value": vals,
                          "unit": unit, "quality": "", "source": source, "entered_by": entered_by, "comment": "", "location_id": ""})
        rows.append(v if keep is None else v[keep])

    def blasts(scale):
        out = np.zeros(n)
        for tb in pd.date_range(t[0].floor("D") + pd.Timedelta(hours=2), t[-1], freq="12h"):
            dt = (t - tb).total_seconds().to_numpy() / 60
            out += np.where(dt >= 0, scale * np.exp(-dt / 40), 0)
        return out

    o2 = lambda: np.round(20.9 + rng.normal(0, 0.04, n), 1)
    co = lambda s: np.round(np.clip(1.5 + rng.normal(0, 0.6, n) + blasts(s), 0, None))
    ago = lambda **k: as_of - pd.Timedelta(**k)

    add("AN-01", "A101", "air_velocity", np.round(3.1 + 0.2 * diurnal + rng.normal(0, 0.05, n), 2), "m/s")
    add("AN-01", "A101", "airflow", np.round((3.1 + 0.2 * diurnal + rng.normal(0, 0.05, n)) * 14.0, 1), "m3/s")
    add("GM-01", "A102", "o2", o2(), "%vol"); add("GM-01", "A102", "co", co(9), "ppm"); add("GM-01", "A102", "no2", np.round(np.clip(0.1 + rng.normal(0, 0.03, n), 0, None), 2), "ppm")
    # GM-02: CO event on a past blast (closed)
    c2 = co(12).astype(float)
    tb = ago(days=5, hours=-8)
    dt = (t - tb).total_seconds().to_numpy() / 60
    c2 += np.where((dt >= 0) & (dt < 90), 28 + 8 * np.sin(np.pi * dt / 90), np.where(dt >= 90, 28 * np.exp(-(dt - 90) / 45), 0))
    add("GM-02", "A103", "o2", o2(), "%vol"); add("GM-02", "A103", "co", np.round(c2), "ppm"); add("GM-02", "A103", "ch4", np.round(np.clip(0.03 + rng.normal(0, 0.01, n), 0, None), 2), "%vol")
    # AN-02: low velocity for 5 h (door left open)
    v2 = 1.6 + 0.1 * diurnal + rng.normal(0, 0.04, n)
    low = (t >= ago(days=3, hours=3)) & (t < ago(days=3, hours=-2))
    v2 = np.where(low, 0.2 + rng.normal(0, 0.03, n), v2)
    add("AN-02", "A104", "air_velocity", np.round(np.clip(v2, 0, None), 2), "m/s")
    # GM-03: 9 h outage
    out = (t >= ago(days=4, hours=6)) & (t < ago(days=4, hours=-3))
    add("GM-03", "A104", "o2", o2(), "%vol", keep=~out); add("GM-03", "A104", "co", co(6), "ppm", keep=~out)
    # TH-01: flatline temperature for 14 h; two impossible humidity values
    temp = np.round(24 + 1.2 * diurnal + rng.normal(0, 0.1, n), 1)
    temp = np.where((t >= ago(days=2, hours=12)) & (t < ago(days=1, hours=22)), 24.3, temp)
    hum = np.array(np.round(np.clip(80 - 6 * diurnal + rng.normal(0, 1, n), 0, 100)), dtype=float)
    hum[[400, 401]] = 140
    add("TH-01", "R101", "temperature", temp, "degC"); add("TH-01", "R101", "humidity", hum, "%RH")
    # GM-04: stopped transmitting 50 h before as-of
    stop = t < ago(hours=50)
    add("GM-04", "B101", "o2", o2(), "%vol", keep=stop); add("GM-04", "B101", "co", co(5), "ppm", keep=stop)
    # AN-03: calibration overdue throughout
    add("AN-03", "B103", "air_velocity", np.round(2.2 + 0.1 * diurnal + rng.normal(0, 0.05, n), 2), "m/s")
    # GM-05: CO rising above the placeholder criterion near the as-of time (active event); some readings in an unrecognised unit
    c5 = co(8).astype(float)
    c5 += np.where(t >= ago(minutes=100), np.linspace(0, 1, n)[-1] * 0 + np.clip((t - ago(minutes=100)).total_seconds() / 60, 0, None) * 0.33 + 1, 0)
    unit5 = np.where((t >= ago(days=6)) & (t < ago(days=6, hours=-2)), "ppb", "ppm")
    c5v = np.where(unit5 == "ppb", np.round(c5) * 1000, np.round(c5))
    add("GM-05", "B102", "o2", o2(), "%vol"); add("GM-05", "B102", "co", c5v, unit5); add("GM-05", "B102", "no2", np.round(np.clip(0.12 + rng.normal(0, 0.03, n), 0, None), 2), "ppm")
    # GM-06: out of service, last readings a week ago
    old = t < ago(days=7)
    add("GM-06", "B103", "o2", o2(), "%vol", keep=old); add("GM-06", "B103", "co", co(5), "ppm", keep=old)
    sensors = pd.concat(rows, ignore_index=True)
    # duplicates: 30 exact, 3 conflicting
    d1 = sensors.sample(30, random_state=1)
    d2 = sensors[sensors.parameter == "co"].sample(3, random_state=2).copy()
    d2["value"] = (pd.to_numeric(d2["value"]) + 4).astype(str)
    sensors = pd.concat([sensors, d1, d2], ignore_index=True)

    # handheld rounds (manual): 08:00 daily; B101 is not visited for the last days
    man = []
    for d in pd.date_range(as_of.floor("D") - pd.Timedelta(days=8), as_of.floor("D") - pd.Timedelta(days=1)):
        for k, loc in enumerate(["A101", "A102", "A103", "B101"]):
            if loc == "B101" and d > pd.Timestamp("2026-10-31"):
                continue
            ts = (d + pd.Timedelta(hours=8, minutes=10 * k)).strftime("%Y-%m-%d %H:%M:%S")
            who = ["R. Owusu", "K. Asante"][d.day % 2]
            for p, val, u in (("air_velocity", round(float(rng.normal(2.0, 0.2)), 1), "m/s"), ("o2", round(float(20.9 + rng.normal(0, 0.05)), 1), "%vol"),
                              ("co", int(abs(rng.normal(2, 1))), "ppm")):
                man.append(dict(timestamp=ts, instrument_id="HH-01", parameter=p, value=val, unit=u, quality="", source="manual", entered_by=who,
                                comment="", location_id=loc))
    return dict(sensors=sensors.sort_values("timestamp"), manual=pd.DataFrame(man))


def write_demo(out_dir, days=10, seed=7):
    d = Path(out_dir)
    (d / "manual_entries").mkdir(parents=True, exist_ok=True)
    _write_locations(d)
    pd.DataFrame(INSTRUMENTS, columns=["instrument_id", "instrument_type", "model", "serial_no", "location_id", "parameters", "status",
                                       "expected_interval_min", "stale_after_min", "last_calibration_date", "calibration_interval_days",
                                       "calibration_ref"]).assign(manufacturer="DEMO", responsible_party="Ventilation team (demo)").to_csv(d / "instruments.csv", index=False)
    pd.DataFrame([dict(criterion_id=i, parameter=p, comparator=c, threshold=th, unit=u, name=nm, location_id="", location_type="",
                       procedure_reference="DEMO-PROC (placeholder)", source_reference="SYNTHETIC: placeholder, not from any approved document",
                       approved_by="SYNTHETIC DEMO - not approved", approval_date="2026-01-01", effective_from="", effective_to="")
                  for i, p, c, th, u, nm in CRITERIA]).to_csv(d / "review_criteria.csv", index=False)
    g = generate(days, seed)
    g["sensors"].to_csv(d / "measurements_sensors.csv", index=False)
    g["manual"].to_csv(d / "manual_entries" / "manual_round_2026-10.csv", index=False)
    return d
