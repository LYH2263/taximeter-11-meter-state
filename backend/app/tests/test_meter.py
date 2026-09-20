import json
import sqlite3

import pytest

from app.seed import init_schema
from app.services.taxi_service import MeterStateError, TaxiService


def make_service() -> TaxiService:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    conn.execute(
        "INSERT INTO tariff(start_price,start_include_km,per_km,per_slow_min,night_factor) VALUES (11,3,2.5,0.8,1.2)"
    )
    conn.commit()
    return TaxiService(conn)


def test_full_lifecycle():
    s = make_service()
    assert s.meter_status()["state"] == "idle"

    s.meter_start(night=False)
    st = s.meter_update_reading(5, 2)
    assert st["state"] == "running"
    assert st["live"]["total"] == 17.6
    # 在跑期间更新读数不写 calc_runs
    assert s.history() == []

    st = s.meter_stop()
    assert st["state"] == "stopped"
    snap = st["snapshot"]
    assert snap["total"] == 17.6
    assert s.history() == []

    r = s.meter_settle()
    assert r["state"] == "idle"
    items = s.history()
    assert len(items) == 1
    assert items[0]["kind"] == "fare"
    rec = json.loads(items[0]["result_json"])
    # 记录页拆解须与停表快照一致
    assert rec["start"] == snap["start"]
    assert rec["mileage"] == snap["mileage"]
    assert rec["slow_fee"] == snap["slow_fee"]
    assert rec["total"] == snap["total"]


def test_settle_rejected_when_idle():
    s = make_service()
    with pytest.raises(MeterStateError):
        s.meter_settle()
    assert s.history() == []


def test_settle_rejected_when_running():
    s = make_service()
    s.meter_start()
    s.meter_update_reading(5, 2)
    with pytest.raises(MeterStateError):
        s.meter_settle()
    assert s.history() == []


def test_start_rejected_when_running():
    s = make_service()
    s.meter_start()
    with pytest.raises(MeterStateError):
        s.meter_start()


def test_start_rejected_when_stopped_until_settle():
    s = make_service()
    s.meter_start()
    s.meter_update_reading(5, 2)
    s.meter_stop()
    with pytest.raises(MeterStateError):
        s.meter_start()
    # 先落表回到空闲后才能再开表
    s.meter_settle()
    s.meter_start()
    assert s.meter_status()["state"] == "running"


def test_reading_frozen_after_stop():
    s = make_service()
    s.meter_start()
    s.meter_update_reading(5, 2)
    snap = s.meter_stop()["snapshot"]
    with pytest.raises(MeterStateError):
        s.meter_update_reading(9, 9)
    assert s.meter_status()["snapshot"] == snap


def test_tariff_change_does_not_rewrite_snapshot():
    s = make_service()
    s.meter_start()
    s.meter_update_reading(5, 2)
    snap = s.meter_stop()["snapshot"]
    # 停表后改运价，已冻结快照不变，落表记录仍按快照
    s._c.execute("UPDATE tariff SET per_km=99, start_price=99")
    s._c.commit()
    assert s.meter_status()["snapshot"] == snap
    s.meter_settle()
    rec = json.loads(s.history()[0]["result_json"])
    assert rec["total"] == snap["total"]


def test_stop_and_update_require_running():
    s = make_service()
    with pytest.raises(MeterStateError):
        s.meter_stop()
    with pytest.raises(MeterStateError):
        s.meter_update_reading(1, 1)


def test_stop_twice_rejected():
    s = make_service()
    s.meter_start()
    s.meter_stop()
    with pytest.raises(MeterStateError):
        s.meter_stop()


def test_night_flag_carries_into_snapshot():
    s = make_service()
    s.meter_start(night=True)
    st = s.meter_update_reading(18, 12)
    assert st["live"]["night"] is True
    snap = s.meter_stop()["snapshot"]
    assert snap["night"] is True
    assert snap["total"] == 69.72
    s.meter_settle()
    rec = json.loads(s.history()[0]["result_json"])
    assert rec["total"] == 69.72
