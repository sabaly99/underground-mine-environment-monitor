"""Settings and vocabularies.

Nothing here is a safety limit. The plausibility ranges are physical sanity bounds used only to catch
corrupt data (for example relative humidity above 100 %). Review criteria come exclusively from the
approved criteria file supplied by qualified personnel.
"""
from dataclasses import dataclass, field, asdict, fields

STD_UNITS = {"air_velocity": "m/s", "airflow": "m3/s", "o2": "%vol", "co": "ppm", "co2": "%vol", "no2": "ppm",
             "h2s": "ppm", "ch4": "%vol", "temperature": "degC", "humidity": "%RH"}
PARAM_LABEL = {"air_velocity": "Air velocity", "airflow": "Airflow", "o2": "Oxygen", "co": "Carbon monoxide",
               "co2": "Carbon dioxide", "no2": "Nitrogen dioxide", "h2s": "Hydrogen sulfide", "ch4": "Methane",
               "temperature": "Temperature", "humidity": "Relative humidity"}
UNIT_LABEL = {"m/s": "m/s", "m3/s": "m³/s", "%vol": "% vol", "ppm": "ppm", "degC": "°C", "%RH": "% RH", "m3/min": "m³/min", "degF": "°F"}
PLAUSIBLE = {"air_velocity": (0.0, 40.0), "airflow": (0.0, 500.0), "o2": (0.0, 100.0), "co": (0.0, 10000.0),
             "co2": (0.0, 100.0), "no2": (0.0, 1000.0), "h2s": (0.0, 1000.0), "ch4": (0.0, 100.0),
             "temperature": (-30.0, 100.0), "humidity": (0.0, 100.0)}
_ALIASES = {"m/s": "m/s", "mps": "m/s", "m3/s": "m3/s", "m³/s": "m3/s", "m^3/s": "m3/s", "m3/min": "m3/min", "m³/min": "m3/min",
            "%vol": "%vol", "vol%": "%vol", "%v/v": "%vol", "%(v/v)": "%vol", "ppm": "ppm", "degc": "degC", "°c": "degC", "c": "degC",
            "degf": "degF", "°f": "degF", "f": "degF", "%rh": "%RH", "rh%": "%RH", "%rh.": "%RH"}
VOL_PARAMS = {"o2", "co2", "ch4"}
# exact conversions only: (from, to) -> (factor, offset), value_to = value_from * factor + offset
CONVERSIONS = {("%vol", "ppm"): (1e4, 0.0), ("ppm", "%vol"): (1e-4, 0.0), ("m3/min", "m3/s"): (1 / 60, 0.0),
               ("degF", "degC"): (5 / 9, -160 / 9)}
QUALITY_MAP = {"good": "GOOD", "ok": "GOOD", "valid": "GOOD", "suspect": "SUSPECT", "uncertain": "SUSPECT",
               "bad": "BAD", "invalid": "BAD", "error": "BAD", "fault": "BAD"}


def canonical_unit(unit, parameter):
    """Return the canonical unit string, or None if the unit is blank/unknown."""
    if unit is None:
        return None
    u = str(unit).strip()
    if not u or u.lower() == "nan":
        return None
    k = u.lower().replace(" ", "")
    if k == "%":
        return "%vol" if parameter in VOL_PARAMS else "%RH" if parameter == "humidity" else None
    return _ALIASES.get(k)


def convert(value, from_unit, to_unit):
    """Exact conversion or None if no exact conversion is defined."""
    if from_unit == to_unit:
        return value
    f = CONVERSIONS.get((from_unit, to_unit))
    return None if f is None else value * f[0] + f[1]


@dataclass
class EnvConfig:
    site_timezone: str = "UTC"                  # naive timestamps are read as this local time
    stale_factor: float = 3.0                   # stale when age > factor x expected interval (unless stale_after_min is set)
    gap_factor: float = 2.5                     # a gap is an interval longer than factor x expected interval
    flatline_min_readings: int = 36             # identical non-zero values this many times in a row -> POSSIBLE_FLATLINE (advisory)
    flatline_params: tuple = ("air_velocity", "airflow", "temperature", "humidity")
    cal_due_soon_days: int = 30
    future_tolerance_min: float = 10.0          # readings later than as-of + this are excluded
    assume_standard_unit_when_blank: bool = False
    avail_bin_hours: int = 6
    avail_days: int = 14
    offline_max_points_per_series: int = 2000
    plausible: dict = field(default_factory=lambda: dict(PLAUSIBLE))

    @classmethod
    def from_dict(cls, d):
        names = {f.name for f in fields(cls)}
        bad = set(d) - names
        if bad:
            raise KeyError(f"Unknown config keys: {sorted(bad)}")
        return cls(**d)

    def to_dict(self):
        return asdict(self)
