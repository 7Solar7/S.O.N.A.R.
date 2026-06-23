import json
import sqlite3
import tempfile

import pytest
from sonar.database import (
    init_db, upsert_device, get_all_devices, get_device_by_mac,
    get_device_count, delete_device, get_devices_by_type,
    get_statistics, export_to_json, import_from_json, close,
)
from sonar.models import Device


@pytest.fixture
def conn():
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    db = init_db(f.name)
    yield db
    close(db)


@pytest.fixture
def sample(conn):
    d = Device(
        mac="aa:bb:cc:dd:ee:ff",
        ip="192.168.1.100",
        hostname="test",
        manufacturer="TestCorp",
        os="Linux",
        device_type="Computer",
        first_seen="2024-01-01T00:00:00Z",
        last_seen="2024-01-01T00:00:00Z",
        discovery_method="ARP",
    )
    upsert_device(conn, d)
    return d


class TestInitDB:
    def test_creates_table(self, conn):
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        assert any(row[0] == "devices" for row in tables)

    def test_returns_connection(self, conn):
        assert isinstance(conn, sqlite3.Connection)


class TestCRUD:
    def test_upsert_and_get_by_mac(self, conn, sample):
        found = get_device_by_mac(conn, "aa:bb:cc:dd:ee:ff")
        assert found is not None
        assert found.ip == "192.168.1.100"

    def test_get_all_devices(self, conn, sample):
        assert len(get_all_devices(conn)) == 1

    def test_get_device_count(self, conn, sample):
        assert get_device_count(conn) == 1

    def test_delete_returns_true(self, conn, sample):
        assert delete_device(conn, "aa:bb:cc:dd:ee:ff") is True

    def test_delete_returns_false(self, conn):
        assert delete_device(conn, "ff:ee:dd:cc:bb:aa") is False

    def test_delete_removes_device(self, conn, sample):
        delete_device(conn, "aa:bb:cc:dd:ee:ff")
        assert get_device_count(conn) == 0


class TestUpsertPreservesFirstSeen:
    def test_first_seen_preserved(self, conn):
        d1 = Device(
            mac="aa:bb:cc:dd:ee:ff", ip="192.168.1.100",
            first_seen="2023-01-01T00:00:00Z", last_seen="2023-01-01T00:00:00Z",
        )
        upsert_device(conn, d1)
        d2 = Device(
            mac="aa:bb:cc:dd:ee:ff", ip="192.168.1.200",
            first_seen="2099-01-01T00:00:00Z", last_seen="2099-01-01T00:00:00Z",
        )
        upsert_device(conn, d2)
        found = get_device_by_mac(conn, "aa:bb:cc:dd:ee:ff")
        assert found.first_seen == "2023-01-01T00:00:00Z"
        assert found.last_seen == "2099-01-01T00:00:00Z"


class TestMACNormalization:
    def test_query_with_dashes(self, conn, sample):
        found = get_device_by_mac(conn, "AA-BB-CC-DD-EE-FF")
        assert found is not None

    def test_query_without_separators(self, conn, sample):
        found = get_device_by_mac(conn, "AABBCCDDEEFF")
        assert found is not None

    def test_query_lowercase(self, conn, sample):
        found = get_device_by_mac(conn, "aa:bb:cc:dd:ee:ff")
        assert found is not None


class TestGetDevicesByType:
    def test_by_type(self, conn, sample):
        devices = get_devices_by_type(conn, "Computer")
        assert len(devices) == 1

    def test_by_type_no_match(self, conn, sample):
        devices = get_devices_by_type(conn, "Router")
        assert len(devices) == 0


class TestStatistics:
    def test_statistics_empty(self, conn):
        stats = get_statistics(conn)
        assert stats["total_devices"] == 0
        assert stats["by_type"] == {}
        assert stats["by_manufacturer"] == {}

    def test_statistics_with_data(self, conn, sample):
        stats = get_statistics(conn)
        assert stats["total_devices"] == 1
        assert stats["by_type"]["Computer"] == 1
        assert stats["by_manufacturer"]["TestCorp"] == 1


class TestJSONRoundTrip:
    def test_export_import_roundtrip(self, conn, sample, tmp_path):
        f = tmp_path / "export.json"
        export_to_json(conn, str(f))
        assert f.exists()
        count_before = get_device_count(conn)

        conn2_f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        conn2_f.close()
        conn2 = init_db(conn2_f.name)
        imported = import_from_json(conn2, str(f))
        assert imported == count_before
        assert get_device_count(conn2) == count_before
        close(conn2)

    def test_export_json_format(self, conn, sample, tmp_path):
        f = tmp_path / "export.json"
        export_to_json(conn, str(f))
        data = json.loads(f.read_text())
        assert isinstance(data, list)
        assert data[0]["mac"] == "AA:BB:CC:DD:EE:FF"
