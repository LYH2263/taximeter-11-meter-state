import json
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure(conn) -> None:
    conn.execute("INSERT OR IGNORE INTO meter_state(id,state,updated_at) VALUES (1,'idle',?)", (_now(),))
    conn.commit()


def get(conn) -> dict:
    ensure(conn)
    row = conn.execute("SELECT * FROM meter_state WHERE id=1").fetchone()
    return dict(row)


def save(conn, state: str, distance_km: float, slow_min: float, night: bool, snapshot: dict | None) -> None:
    conn.execute(
        "UPDATE meter_state SET state=?, distance_km=?, slow_min=?, night=?, snapshot_json=?, updated_at=? WHERE id=1",
        (
            state,
            float(distance_km),
            float(slow_min),
            int(bool(night)),
            json.dumps(snapshot, ensure_ascii=False) if snapshot is not None else None,
            _now(),
        ),
    )
    conn.commit()
