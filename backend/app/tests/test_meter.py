import pytest

from app import seed
from app.db import connect
from app.repositories import meter
from app.services.taxi_service import MeterError, TaxiService


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    import app.db as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "test.db")
    seed.init_db()
    yield


def _count_runs():
    with connect() as c:
        return c.execute("SELECT COUNT(*) n FROM calc_runs").fetchone()["n"]


def test_full_cycle_start_update_stop_checkout(db):
    with TaxiService() as s:
        st = s.meter_start(night=False)
        assert st["status"] == meter.RUNNING
        assert st["distance_km"] == 0
        assert _count_runs() == 1  # 仅种子记录，开表不写 calc_runs

        st = s.meter_update(8.0, 3.0)
        assert st["status"] == meter.RUNNING
        assert st["live"]["total"] == 25.9  # 11 + 5*2.5 + 3*0.8
        assert _count_runs() == 1  # 更新读数不写 calc_runs

        st = s.meter_stop()
        assert st["status"] == meter.STOPPED
        snap = st["snapshot"]
        assert snap["fare"]["start"] == 11
        assert snap["fare"]["mileage"] == 12.5
        assert snap["fare"]["slow_fee"] == 2.4
        assert snap["fare"]["total"] == 25.9
        assert _count_runs() == 1  # 停表也不写

        out = s.meter_checkout()
        assert out["run_id"] is not None
        assert out["status"] == meter.IDLE
        assert out["total"] == 24.9
        assert _count_runs() == 2  # 落表恰好写一条

        assert s.meter_state()["status"] == meter.IDLE


def test_checkout_rejected_from_idle_and_running_without_writing(db):
    baseline = _count_runs()
    with TaxiService() as s:
        with pytest.raises(MeterError):
            s.meter_checkout()  # 空闲直接落表
        s.meter_start(night=False)
        with pytest.raises(MeterError):
            s.meter_checkout()  # 在跑直接落表
    assert _count_runs() == baseline


def test_frozen_snapshot_immune_to_input_and_tariff_changes(db):
    with TaxiService() as s:
        s.meter_start(night=False)
        s.meter_update(8.0, 3.0)
        stopped = s.meter_stop()
        frozen_total = stopped["snapshot"]["fare"]["total"]

        # 冻结后改读数：更新接口本身被拒，库内读数变化也不得影响快照
        with pytest.raises(MeterError):
            s.meter_update(100.0, 99.0)
        with connect() as c:
            c.execute("UPDATE meter_state SET distance_km = 100, slow_min = 99")
            c.commit()
        # 在跑/停表期间改运价，不得改写已冻结快照
        with connect() as c:
            c.execute("UPDATE tariff SET per_km = 99, start_price = 999")
            c.commit()

        again = s.meter_state()
        assert again["status"] == meter.STOPPED
        assert again["snapshot"]["fare"]["total"] == frozen_total
        assert again["snapshot"]["fare"]["mileage"] == 12.5

        out = s.meter_checkout()
        assert out["total"] == frozen_total


def test_restart_while_stopped_rejected_until_checkout(db):
    with TaxiService() as s:
        s.meter_start(night=False)
        s.meter_update(5, 1)
        s.meter_stop()
        with pytest.raises(MeterError):
            s.meter_start(night=False)  # 停表后未落表再次开表
        s.meter_checkout()
        st = s.meter_start(night=True)  # 落表回空闲后可以再开
        assert st["status"] == meter.RUNNING
        assert st["night"] is True


def test_double_start_and_bad_transitions(db):
    with TaxiService() as s:
        s.meter_start(night=False)
        with pytest.raises(MeterError):
            s.meter_start(night=False)
        with pytest.raises(MeterError):
            s.meter_stop()
            s.meter_stop()  # 已停表不能再停
        with pytest.raises(MeterError):
            s.meter_update(1, 1)  # 停表后不能更新读数
