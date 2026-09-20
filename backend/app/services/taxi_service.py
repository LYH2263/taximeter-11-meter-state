import json
from app.db import connect
from app.engines.night_compare import compare_day_night
from app.engines.tariff_breakdown import calc_fare
from app.repositories import meter as meter_repo
from app.repositories import runs, settings, tariff, trips


class MeterStateError(Exception):
    """计价器状态机非法迁移（空闲 idle / 在跑 running / 已停表 stopped）"""


class TaxiService:
    def __init__(self, conn=None):
        self._c = conn or connect()
        self._own = conn is None
    def close(self):
        if self._own: self._c.close()
    def __enter__(self): return self
    def __exit__(self, *a): self.close()
    def list_trips(self): return trips.list_all(self._c)
    def trip(self, tid): return trips.get(self._c, tid)
    def tariff(self): return tariff.get_active(self._c)
    def settings(self): return settings.get_map(self._c)
    def history(self, limit=50): return runs.list_recent(self._c, limit)
    def fare(self, distance_km, slow_min, night, trip_id, persist):
        t = tariff.get_active(self._c)
        r = calc_fare(distance_km, slow_min, night, t)
        rid = runs.insert(self._c, "fare", {"distance_km": distance_km, "slow_min": slow_min, "night": night}, r, trip_id) if persist else None
        return {"run_id": rid, **r}
    def compare(self, distance_km, slow_min, persist):
        t = tariff.get_active(self._c)
        r = compare_day_night(distance_km, slow_min, t)
        rid = runs.insert(self._c, "compare", {"distance_km": distance_km, "slow_min": slow_min}, r, None) if persist else None
        return {"run_id": rid, **r}
    def dashboard(self):
        items = trips.list_all(self._c)
        clean = [x for x in items if "种子" not in x["label"]]
        dirty = [x for x in items if "种子" in x["label"]]
        return {"trip_count": len(items), "clean": len(clean), "dirty": len(dirty)}

    # ---- 计价器状态机：idle(空闲) -> running(在跑) -> stopped(已停表) -> idle ----

    def meter_status(self):
        m = meter_repo.get(self._c)
        live = None
        if m["state"] == "running":
            live = calc_fare(m["distance_km"], m["slow_min"], bool(m["night"]), tariff.get_active(self._c))
        return {
            "state": m["state"],
            "reading": {"distance_km": m["distance_km"], "slow_min": m["slow_min"], "night": bool(m["night"])},
            "live": live,
            "snapshot": json.loads(m["snapshot_json"]) if m["snapshot_json"] else None,
            "updated_at": m["updated_at"],
        }

    def meter_start(self, night=False):
        m = meter_repo.get(self._c)
        if m["state"] == "running":
            raise MeterStateError("计价器在跑，不能重复开表")
        if m["state"] == "stopped":
            raise MeterStateError("已停表未落表，须先落表回到空闲才能再开表")
        meter_repo.save(self._c, "running", 0.0, 0.0, night, None)
        return self.meter_status()

    def meter_update_reading(self, distance_km, slow_min):
        m = meter_repo.get(self._c)
        if m["state"] == "idle":
            raise MeterStateError("计价器空闲，须先开表再更新读数")
        if m["state"] == "stopped":
            raise MeterStateError("已停表，读数已冻结，不能再改")
        meter_repo.save(self._c, "running", distance_km, slow_min, bool(m["night"]), None)
        return self.meter_status()

    def meter_stop(self):
        m = meter_repo.get(self._c)
        if m["state"] == "idle":
            raise MeterStateError("计价器空闲，须先开表")
        if m["state"] == "stopped":
            raise MeterStateError("已停表，请勿重复停表")
        snapshot = calc_fare(m["distance_km"], m["slow_min"], bool(m["night"]), tariff.get_active(self._c))
        meter_repo.save(self._c, "stopped", m["distance_km"], m["slow_min"], bool(m["night"]), snapshot)
        return self.meter_status()

    def meter_settle(self):
        m = meter_repo.get(self._c)
        if m["state"] == "idle":
            raise MeterStateError("计价器空闲，无表可落")
        if m["state"] == "running":
            raise MeterStateError("计价器在跑，须先停表再落表")
        snapshot = json.loads(m["snapshot_json"])
        rid = runs.insert(
            self._c, "fare",
            {"distance_km": snapshot["distance_km"], "slow_min": snapshot["slow_min"], "night": snapshot["night"], "source": "meter"},
            snapshot, None,
        )
        meter_repo.save(self._c, "idle", 0.0, 0.0, False, None)
        return {"run_id": rid, **self.meter_status()}
