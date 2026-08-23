"""SQLite persistence for ingredient counts and owned appliances."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.catalog import APPLIANCE_IDS, DATA_DIR

DB_PATH = DATA_DIR / "inventory.db"


def connect(path: Path | None = None) -> sqlite3.Connection:
    db_path = path or DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS inventory (
            item_id TEXT PRIMARY KEY,
            count INTEGER NOT NULL CHECK (count >= 0)
        );
        CREATE TABLE IF NOT EXISTS appliances (
            id TEXT PRIMARY KEY,
            owned INTEGER NOT NULL CHECK (owned IN (0, 1))
        );
        """
    )
    for appliance_id in APPLIANCE_IDS:
        conn.execute(
            "INSERT OR IGNORE INTO appliances (id, owned) VALUES (?, 0)",
            (appliance_id,),
        )
    conn.commit()


def get_inventory(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute("SELECT item_id, count FROM inventory WHERE count > 0")
    return {row["item_id"]: int(row["count"]) for row in rows}


def get_count(conn: sqlite3.Connection, item_id: str) -> int:
    row = conn.execute(
        "SELECT count FROM inventory WHERE item_id = ?", (item_id,)
    ).fetchone()
    return int(row["count"]) if row else 0


def set_count(conn: sqlite3.Connection, item_id: str, count: int) -> int:
    count = max(0, int(count))
    conn.execute(
        """
        INSERT INTO inventory (item_id, count) VALUES (?, ?)
        ON CONFLICT(item_id) DO UPDATE SET count = excluded.count
        """,
        (item_id, count),
    )
    conn.commit()
    return count


def get_appliances(conn: sqlite3.Connection) -> dict[str, bool]:
    rows = conn.execute("SELECT id, owned FROM appliances")
    owned = {row["id"]: bool(row["owned"]) for row in rows}
    for appliance_id in APPLIANCE_IDS:
        owned.setdefault(appliance_id, False)
    return owned


def set_appliance(conn: sqlite3.Connection, appliance_id: str, owned: bool) -> bool:
    if appliance_id not in APPLIANCE_IDS:
        raise ValueError(f"Unknown appliance: {appliance_id}")
    flag = 1 if owned else 0
    conn.execute(
        """
        INSERT INTO appliances (id, owned) VALUES (?, ?)
        ON CONFLICT(id) DO UPDATE SET owned = excluded.owned
        """,
        (appliance_id, flag),
    )
    conn.commit()
    return bool(flag)


def apply_inventory(conn: sqlite3.Connection, new_inventory: dict[str, int]) -> None:
    for item_id, count in new_inventory.items():
        count = max(0, int(count))
        conn.execute(
            """
            INSERT INTO inventory (item_id, count) VALUES (?, ?)
            ON CONFLICT(item_id) DO UPDATE SET count = excluded.count
            """,
            (item_id, count),
        )
    conn.commit()
