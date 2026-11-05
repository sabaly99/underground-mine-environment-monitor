import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mineenv import demo, loaders, analysis              # noqa: E402
from mineenv.config import EnvConfig                      # noqa: E402

LOC = "location_id,name,level,type,x,y\nL1,Test drift,1000L,heading,10,10\nL2,Empty place,1000L,heading,50,10\n"
INS = ("instrument_id,instrument_type,serial_no,location_id,parameters,status,expected_interval_min,stale_after_min,last_calibration_date,calibration_interval_days\n"
       "I1,fixed gas,S1,L1,co,in_service,10,,2026-10-01,365\n")
CRIT_HEAD = "criterion_id,parameter,comparator,threshold,unit,name,source_reference,approved_by,approval_date\n"
CRIT = CRIT_HEAD + "C1,co,>,25,ppm,test criterion,TEST-DOC-1,Test Approver,2026-01-01\n"
T0 = pd.Timestamp("2026-11-01 00:00")


def readings(values, start=T0, step=10, inst="I1", param="co", unit="ppm", **extra):
    rows = []
    for i, v in enumerate(values):
        if v is None:
            continue
        rows.append(dict(timestamp=(start + pd.Timedelta(minutes=i * step)).strftime("%Y-%m-%d %H:%M:%S"), instrument_id=inst, parameter=param,
                         value=v, unit=unit, quality="", source="sensor", entered_by="", comment="", location_id="", **extra))
    return rows


def run(tmp_path, rows, ins=INS, crit=CRIT, loc=LOC, as_of=None, cfg=None):
    d = Path(tmp_path)
    (d / "locations.csv").write_text(loc)
    (d / "instruments.csv").write_text(ins)
    if crit is not None:
        (d / "review_criteria.csv").write_text(crit)
    pd.DataFrame(rows).to_csv(d / "measurements.csv", index=False)
    cfg = cfg or EnvConfig()
    L = loaders.load_locations(d / "locations.csv")
    I = loaders.load_instruments(d / "instruments.csv", L)
    C = loaders.load_criteria(d / "review_criteria.csv") if crit is not None else None
    raw = loaders.load_measurements(["measurements.csv"], d)
    parsed, rej = analysis.parse_raw(raw, cfg)
    as_of = pd.Timestamp(as_of) if as_of else pd.to_datetime(parsed["timestamp"]).max()
    return analysis.analyse(parsed, rej, I, L, C, cfg, as_of)


@pytest.fixture(scope="session")
def demo_dir(tmp_path_factory):
    return demo.write_demo(tmp_path_factory.mktemp("demo"))


@pytest.fixture(scope="session")
def demo_run(demo_dir):
    cfg = EnvConfig()
    L = loaders.load_locations(demo_dir / "locations.csv")
    I = loaders.load_instruments(demo_dir / "instruments.csv", L)
    C = loaders.load_criteria(demo_dir / "review_criteria.csv")
    raw = loaders.load_measurements(["measurements*.csv", "manual_entries/*.csv"], demo_dir)
    parsed, rej = analysis.parse_raw(raw, cfg)
    A = analysis.analyse(parsed, rej, I, L, C, cfg, demo.AS_OF)
    return dict(A=A, parsed=parsed, cfg=cfg, L=L, I=I, C=C)
