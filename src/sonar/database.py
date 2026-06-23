import json
import sqlite3
from sonar.models import Device, _utcnow_iso


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            mac TEXT PRIMARY KEY,
            ip TEXT NOT NULL,
            hostname TEXT,
            manufacturer TEXT,
            os TEXT,
            device_type TEXT,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            discovery_method TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def upsert_device(conn: sqlite3.Connection, device: Device) -> None:
    existing = get_device_by_mac(conn, device.mac)
    if existing:
        device.first_seen = existing.first_seen
    conn.execute("""
        INSERT OR REPLACE INTO devices (mac, ip, hostname, manufacturer, os, device_type, first_seen, last_seen, discovery_method)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (device.mac, device.ip, device.hostname, device.manufacturer, device.os,
          device.device_type, device.first_seen, device.last_seen, device.discovery_method))
    conn.commit()


def get_all_devices(conn: sqlite3.Connection) -> list[Device]:
    rows = conn.execute("SELECT * FROM devices").fetchall()
    return [_row_to_device(row) for row in rows]


def get_device_by_mac(conn: sqlite3.Connection, mac: str) -> Device | None:
    raw = mac.replace(":", "").replace("-", "").upper()
    normalized = ":".join(raw[i : i + 2] for i in range(0, 12, 2))
    row = conn.execute("SELECT * FROM devices WHERE mac = ?", (normalized,)).fetchone()
    return _row_to_device(row) if row else None


def get_device_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0]


def _row_to_device(row: sqlite3.Row) -> Device:
    return Device(
        mac=row["mac"],
        ip=row["ip"],
        hostname=row["hostname"],
        manufacturer=row["manufacturer"],
        os=row["os"],
        device_type=row["device_type"],
        first_seen=row["first_seen"],
        last_seen=row["last_seen"],
        discovery_method=row["discovery_method"],
    )


def delete_device(conn: sqlite3.Connection, mac: str) -> bool:
    raw = mac.replace(":", "").replace("-", "").upper()
    normalized = ":".join(raw[i : i + 2] for i in range(0, 12, 2))
    cursor = conn.execute("DELETE FROM devices WHERE mac = ?", (normalized,))
    conn.commit()
    return cursor.rowcount > 0


def get_devices_by_type(conn: sqlite3.Connection, device_type: str) -> list[Device]:
    rows = conn.execute("SELECT * FROM devices WHERE device_type = ?", (device_type,)).fetchall()
    return [_row_to_device(row) for row in rows]


def get_statistics(conn: sqlite3.Connection) -> dict:
    total = conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
    by_type = {}
    for row in conn.execute("SELECT device_type, COUNT(*) as cnt FROM devices WHERE device_type IS NOT NULL GROUP BY device_type"):
        by_type[row[0]] = row[1]
    by_manufacturer = {}
    for row in conn.execute("SELECT manufacturer, COUNT(*) as cnt FROM devices WHERE manufacturer IS NOT NULL GROUP BY manufacturer"):
        by_manufacturer[row[0]] = row[1]
    return {
        "total_devices": total,
        "by_type": by_type,
        "by_manufacturer": by_manufacturer,
    }


def export_to_json(conn: sqlite3.Connection, filepath: str) -> None:
    devices = get_all_devices(conn)
    data = [
        {
            "mac": d.mac,
            "ip": d.ip,
            "hostname": d.hostname,
            "manufacturer": d.manufacturer,
            "os": d.os,
            "device_type": d.device_type,
            "first_seen": d.first_seen,
            "last_seen": d.last_seen,
            "discovery_method": d.discovery_method,
        }
        for d in devices
    ]
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def import_from_json(conn: sqlite3.Connection, filepath: str) -> int:
    with open(filepath) as f:
        data = json.load(f)
    count = 0
    for item in data:
        device = Device(
            mac=item["mac"],
            ip=item["ip"],
            hostname=item.get("hostname"),
            manufacturer=item.get("manufacturer"),
            os=item.get("os"),
            device_type=item.get("device_type"),
            first_seen=item.get("first_seen", _utcnow_iso()),
            last_seen=item.get("last_seen", _utcnow_iso()),
            discovery_method=item.get("discovery_method", "unknown"),
        )
        upsert_device(conn, device)
        count += 1
    return count


def close(conn: sqlite3.Connection) -> None:
    conn.close()
