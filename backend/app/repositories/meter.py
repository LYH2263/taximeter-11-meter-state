import json
import sqlite3

IDLE = "idle"
RUNNING = "running"
STOPPED = "stopped"

_ROW_ID = 1


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meter_state(
            id INTEGER PRIMARY KEY CHECK (id = 1),
            status TEXT NOT NULL DEFAULT 'idle',
            distance_km REAL NOT NULL DEFAULT 0,
            slow_min REAL NOT NULL DEFAULT 0,
            night INTEGER NOT NULL DEFAULT 0,
            tariff_json TEXT,
            snapshot_json TEXT,
            started_at TEXT,
            stopped_at TEXT
        )
        """
    )
    conn.execute(
        "INSERT OR IGNORE INTO meter_state(id, status) VALUES (?, ?)",
        (_ROW_ID, IDLE),
    )
    conn.commit()


def get(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute("SELECT * FROM meter_state WHERE id = ?", (_ROW_ID,)).fetchone()
    return dict(row) if row else None


def start(
    conn: sqlite3.Connection,
    distance_km: float,
    slow_min: float,
    night: bool,
    tariff: dict,
    started_at: str,
) -> None:
    conn.execute(
        """
        UPDATE meter_state
           SET status = ?, distance_km = ?, slow_min = ?, night = ?,
               tariff_json = ?, snapshot_json = NULL,
               started_at = ?, stopped_at = NULL
         WHERE id = ?
        """,
        (
            RUNNING,
            distance_km,
            slow_min,
            1 if night else 0,
            json.dumps(tariff, ensure_ascii=False),
            started_at,
            _ROW_ID,
        ),
    )
    conn.commit()


def update_readings(conn: sqlite3.Connection, distance_km: float, slow_min: float) -> None:
    conn.execute(
        "UPDATE meter_state SET distance_km = ?, slow_min = ? WHERE id = ?",
        (distance_km, slow_min, _ROW_ID),
    )
    conn.commit()


def stop(conn: sqlite3.Connection, snapshot: dict, stopped_at: str) -> None:
    conn.execute(
        "UPDATE meter_state SET status = ?, snapshot_json = ?, stopped_at = ? WHERE id = ?",
        (STOPPED, json.dumps(snapshot, ensure_ascii=False), stopped_at, _ROW_ID),
    )
    conn.commit()


def reset_to_idle(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        UPDATE meter_state
           SET status = ?, distance_km = 0, slow_min = 0, night = 0,
               tariff_json = NULL, snapshot_json = NULL,
               started_at = NULL, stopped_at = NULL
         WHERE id = ?
        """,
        (IDLE, _ROW_ID),
    )
    conn.commit()
