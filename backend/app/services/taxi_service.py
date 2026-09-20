import json
from datetime import datetime, timezone

from app.db import connect
from app.engines.night_compare import compare_day_night
from app.engines.tariff_breakdown import calc_fare
from app.repositories import meter, runs, settings, tariff, trips


class MeterError(Exception):
    """非法计价器状态流转。"""

    def __init__(self, message: str, status: str):
        super().__init__(message)
        self.status = status


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaxiService:
    def __init__(self): self._c = connect()
    def close(self): self._c.close()
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

    # ---------- 计价器状态机：idle -> running -> stopped -> idle ----------

    def _meter_row(self) -> dict:
        row = meter.get(self._c)
        if row is None:
            meter.ensure_table(self._c)
            row = meter.get(self._c)
        return row

    @staticmethod
    def _require_status(row: dict, expected: str, action: str) -> None:
        if row["status"] != expected:
            raise MeterError(f"当前状态为{row['status']}，无法{action}", row["status"])

    def meter_state(self) -> dict:
        row = self._meter_row()
        snapshot = self._load_snapshot(row)
        return {
            "status": row["status"],
            "distance_km": row["distance_km"],
            "slow_min": row["slow_min"],
            "night": bool(row["night"]),
            "started_at": row["started_at"],
            "stopped_at": row["stopped_at"],
            "live": self._live_fare(row) if row["status"] == meter.RUNNING else None,
            "snapshot": snapshot,
        }

    @staticmethod
    def _load_snapshot(row: dict) -> dict | None:
        if not row.get("snapshot_json"):
            return None
        return json.loads(row["snapshot_json"])

    def _live_fare(self, row: dict) -> dict:
        t = json.loads(row["tariff_json"]) if row.get("tariff_json") else tariff.get_active(self._c)
        return calc_fare(row["distance_km"], row["slow_min"], bool(row["night"]), t)

    def meter_start(self, night: bool) -> dict:
        row = self._meter_row()
        if row["status"] == meter.STOPPED:
            raise MeterError("已停表但未落表，请先落表后再开表", row["status"])
        if row["status"] == meter.RUNNING:
            raise MeterError("计价器已在跑，无需重复开表", row["status"])
        meter.start(self._c, 0.0, 0.0, night, tariff.get_active(self._c), _now())
        return self.meter_state()

    def meter_update(self, distance_km: float, slow_min: float) -> dict:
        row = self._meter_row()
        self._require_status(row, meter.RUNNING, "更新读数")
        meter.update_readings(self._c, distance_km, slow_min)
        return self.meter_state()

    def meter_stop(self) -> dict:
        row = self._meter_row()
        self._require_status(row, meter.RUNNING, "停表")
        t = json.loads(row["tariff_json"])
        fare = calc_fare(row["distance_km"], row["slow_min"], bool(row["night"]), t)
        snapshot = {
            "inputs": {
                "distance_km": round(float(row["distance_km"]), 2),
                "slow_min": round(float(row["slow_min"]), 1),
                "night": bool(row["night"]),
            },
            "tariff": t,
            "fare": fare,
            "stopped_at": _now(),
        }
        meter.stop(self._c, snapshot, snapshot["stopped_at"])
        return self.meter_state()

    def meter_checkout(self) -> dict:
        row = self._meter_row()
        self._require_status(row, meter.STOPPED, "落表")
        snapshot = self._load_snapshot(row)
        inputs = snapshot["inputs"]
        fare = snapshot["fare"]
        rid = runs.insert(
            self._c,
            "fare",
            {"distance_km": inputs["distance_km"], "slow_min": inputs["slow_min"], "night": inputs["night"]},
            fare,
            None,
        )
        meter.reset_to_idle(self._c)
        return {"run_id": rid, "status": meter.IDLE, **fare}

    def dashboard(self):
        items = trips.list_all(self._c)
        clean = [x for x in items if "种子" not in x["label"]]
        dirty = [x for x in items if "种子" in x["label"]]
        return {"trip_count": len(items), "clean": len(clean), "dirty": len(dirty)}
