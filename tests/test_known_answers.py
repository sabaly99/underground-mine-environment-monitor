import pandas as pd
import pytest

from conftest import run, readings, CRIT_HEAD, CRIT, INS, T0
from mineenv.loaders import load_criteria, DataError


def state(A, loc="L1"):
    return A.channels[A.channels.location_id == loc].iloc[0]["state"]


def test_comparator_boundary_strict_greater(tmp_path):
    A = run(tmp_path, readings([10, 25, 25.0001, 30]))
    hits = A.readings[A.readings.criteria_met != ""]
    assert list(hits.value) == [25.0001, 30]


def test_comparator_boundary_greater_equal(tmp_path):
    crit = CRIT_HEAD + "C1,co,>=,25,ppm,t,DOC,Approver,2026-01-01\n"
    A = run(tmp_path, readings([10, 25, 24.99]), crit=crit)
    assert list(A.readings[A.readings.criteria_met != ""].value) == [25]


def test_events_group_consecutive_hits_and_active_flag(tmp_path):
    vals = [1, 1, 30, 31, 32, 1, 1, 40, 41]            # two runs; last run reaches final reading
    A = run(tmp_path, readings(vals))
    ev = A.events.sort_values("start_ts")
    assert len(ev) == 2
    assert list(ev.n_readings) == [3, 2]
    assert list(ev.peak_value) == [32, 41]
    assert list(ev.active) == [False, True]
    assert state(A) == "CRITERION_MET"


def test_gap_detected_with_known_length(tmp_path):
    vals = [1.0] * 30
    for i in range(10, 16):
        vals[i] = None                                  # readings 10..15 missing -> 70 min between 9 and 16
    A = run(tmp_path, readings(vals))
    closed = A.gaps[~A.gaps["open"]]
    assert len(closed) == 1
    assert closed.iloc[0]["minutes"] == pytest.approx(70)


def test_open_trailing_gap_and_stale_is_not_safe(tmp_path):
    A = run(tmp_path, readings([1.0] * 10), as_of=T0 + pd.Timedelta(hours=10))
    assert state(A) == "STALE"
    assert A.gaps["open"].any()
    assert "unknown" in A.channels.iloc[0]["state_reason"].lower()


def test_missing_is_never_reported_as_no_criterion_met(tmp_path):
    A = run(tmp_path, readings([1.0] * 10), as_of=T0 + pd.Timedelta(hours=10))
    assert (A.channels.state == "NO_CRITERION_MET").sum() == 0
    l2 = A.locations.set_index("location_id").loc["L2"]
    assert l2["state"] == "NO_DATA"                    # location with no instrument at all


def test_fresh_clean_data_is_no_criterion_met_not_safe(tmp_path):
    A = run(tmp_path, readings([1.0, 2.0, 1.5, 1.2, 1.1, 1.3]))
    assert state(A) == "NO_CRITERION_MET"
    assert "safe" not in A.channels.iloc[0]["state_reason"].lower().replace("not safe", "")


def test_no_criteria_configured_state(tmp_path):
    A = run(tmp_path, readings([1.0, 2.0, 500.0]), crit=CRIT_HEAD)   # empty criteria file
    assert state(A) == "NO_CRITERIA_CONFIGURED"
    assert (A.readings.criteria_met == "").all()


def test_out_of_service_state(tmp_path):
    ins = INS.replace("in_service", "out_of_service")
    A = run(tmp_path, readings([1.0] * 5), ins=ins)
    assert state(A) == "OUT_OF_SERVICE"


def test_calibration_is_time_aware(tmp_path):
    ins = INS.replace("2026-10-01,365", "2026-01-01,305")     # due 2026-11-02 00:00
    vals = [1.0] * 400                                         # 2026-11-01 00:00 .. 11-03 18:30
    A = run(tmp_path, readings(vals), ins=ins)
    r = A.readings.sort_values("ts")
    before = r[r.ts < pd.Timestamp("2026-11-02")]
    after = r[r.ts > pd.Timestamp("2026-11-02 00:30")]
    assert not before["flags"].str.contains("CALIBRATION_OVERDUE").any()
    assert after["flags"].str.contains("CALIBRATION_OVERDUE").all()


def test_unit_conversion_exact(tmp_path):
    rows = readings([10000], param="co", unit="ppm") + readings([1], start=T0 + pd.Timedelta(minutes=10), param="co", unit="%vol")
    A = run(tmp_path, rows, ins=INS.replace(",co,", ",co;o2,"))
    vals = sorted(A.readings.value)
    assert vals == [pytest.approx(10000), pytest.approx(10000)]


def test_unit_missing_gives_nan_and_flag(tmp_path):
    A = run(tmp_path, readings([5.0, 6.0], unit=""))
    assert A.readings.value.isna().all()
    assert A.readings["flags"].str.contains("UNIT_MISSING").all()


def test_implausible_value_flagged_not_hidden(tmp_path):
    A = run(tmp_path, readings([1.0, -5.0, 50000.0]))
    bad = A.readings[A.readings["flags"].str.contains("IMPLAUSIBLE")]
    assert len(bad) == 2


def test_flatline_flag_on_sensor_with_identical_nonzero_values(tmp_path):
    ins = INS.replace(",co,", ",temperature,")
    rows = readings([21.5] * 50, param="temperature", unit="degC")
    A = run(tmp_path, rows, ins=ins, crit=CRIT_HEAD)
    assert A.readings["flags"].str.contains("POSSIBLE_FLATLINE").any()


def test_exact_duplicates_dropped_and_conflicts_flagged(tmp_path):
    rows = readings([1.0, 2.0, 3.0])
    rows = rows + [dict(rows[0])]                                # exact duplicate
    c = dict(rows[1]); c["value"] = 9.0
    rows.append(c)                                               # same timestamp, different value
    A = run(tmp_path, rows)
    assert len(A.readings) == 4
    assert A.readings["flags"].str.contains("DUPLICATE_CONFLICT").sum() == 2


def test_quality_flag_never_hides_criterion_hit(tmp_path):
    rows = readings([1.0, 40.0, 1.0])
    rows[1]["quality"] = "bad"
    A = run(tmp_path, rows)
    r = A.readings.sort_values("ts").iloc[1]
    assert r.criteria_met != "" and r.quality_state == "BAD"


def test_criteria_without_approver_or_source_rejected(tmp_path):
    for bad in (CRIT_HEAD + "C1,co,>,25,ppm,t,DOC,,2026-01-01\n", CRIT_HEAD + "C1,co,>,25,ppm,t,,Approver,2026-01-01\n",
                CRIT_HEAD + "C1,co,>,25,ppm,t,DOC,Approver,\n"):
        p = tmp_path / "c.csv"; p.write_text(bad)
        with pytest.raises(DataError):
            load_criteria(p)


def test_criteria_bad_comparator_rejected(tmp_path):
    p = tmp_path / "c.csv"; p.write_text(CRIT_HEAD + "C1,co,==,25,ppm,t,DOC,Approver,2026-01-01\n")
    with pytest.raises(DataError):
        load_criteria(p)


def test_instrument_without_interval_rejected(tmp_path):
    ins = INS.replace(",10,,", ",,,")
    with pytest.raises(DataError):
        run(tmp_path, readings([1.0]), ins=ins)


def test_demo_criteria_marked_demo(demo_run):
    assert demo_run["C"]["is_demo"].all()
    assert demo_run["A"].notes["demo_criteria"]
