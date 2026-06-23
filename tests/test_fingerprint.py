from unittest.mock import patch
import pytest
from sonar.fingerprint import load_oui_db, lookup_manufacturer, guess_device_type, guess_os
from sonar.models import Device


class TestLoadOuiDB:
    def test_loads_csv(self, sample_oui_csv):
        db = load_oui_db(sample_oui_csv)
        assert db["AA:BB:CC"] == "TestCorp"
        assert db["DD:EE:FF:00"] == "AnotherCorp"
        assert db["11:22:33:44:55"] == "PreciseCorp"

    def test_skips_empty_and_comments(self, tmp_path):
        f = tmp_path / "oui.csv"
        f.write_text("# comment\n\nAA:BB:CC,TestCorp\n")
        db = load_oui_db(str(f))
        assert db == {"AA:BB:CC": "TestCorp"}

    def test_handles_missing_file(self):
        db = load_oui_db("/nonexistent/oui.csv")
        assert db == {}

    def test_oupper_cases_prefix(self, tmp_path):
        f = tmp_path / "oui.csv"
        f.write_text("aa:bb:cc,TestCorp\n")
        db = load_oui_db(str(f))
        assert "AA:BB:CC" in db


class TestLookupManufacturer:
    def test_lookup_8char_prefix(self):
        db = {"AA:BB:CC": "TestCorp"}
        assert lookup_manufacturer("AA:BB:CC:DD:EE:FF", db) == "TestCorp"

    def test_lookup_10char_prefix(self):
        db = {"AA:BB:CC:DD": "ExtendedCorp"}
        assert lookup_manufacturer("AA:BB:CC:DD:EE:FF", db) == "ExtendedCorp"

    def test_lookup_12char_prefix(self):
        db = {"AA:BB:CC:DD:EE:FF": "FullMACCorp"}
        assert lookup_manufacturer("AA:BB:CC:DD:EE:FF", db) == "FullMACCorp"

    def test_prefers_shorter_prefix(self):
        db = {"AA:BB:CC": "TestCorp", "AA:BB:CC:DD": "ExtendedCorp"}
        assert lookup_manufacturer("AA:BB:CC:DD:EE:FF", db) == "TestCorp"

    def test_returns_none_for_no_match(self):
        db = {"11:22:33": "Other"}
        assert lookup_manufacturer("AA:BB:CC:DD:EE:FF", db) is None

    def test_normalizes_mac(self):
        db = {"AA:BB:CC": "TestCorp"}
        assert lookup_manufacturer("aa-bb-cc-dd-ee-ff", db) == "TestCorp"

    def test_returns_none_for_short_mac(self):
        assert lookup_manufacturer("AA:BB", {"AA:BB:CC": "X"}) is None


class TestGuessDeviceType:
    def test_router_by_hostname(self):
        d = Device(mac="00:00:00:00:00:01", ip="10.0.0.1", hostname="router")
        assert guess_device_type(d) == "Router"

    def test_router_by_manufacturer(self):
        d = Device(mac="00:00:00:00:00:02", ip="10.0.0.2", manufacturer="Cisco")
        assert guess_device_type(d) == "Router"

    def test_printer_by_hostname(self):
        d = Device(mac="00:00:00:00:00:03", ip="10.0.0.3", hostname="hplaserjet")
        assert guess_device_type(d) == "Printer"

    def test_printer_by_manufacturer(self):
        d = Device(mac="00:00:00:00:00:04", ip="10.0.0.4", manufacturer="Brother")
        assert guess_device_type(d) == "Printer"

    def test_phone(self):
        d = Device(mac="00:00:00:00:00:05", ip="10.0.0.5", hostname="iphone-12")
        assert guess_device_type(d) == "Phone"

    def test_smart_tv(self):
        d = Device(mac="00:00:00:00:00:06", ip="10.0.0.6", hostname="roku-livingroom")
        assert guess_device_type(d) == "Smart TV"

    def test_smart_speaker(self):
        d = Device(mac="00:00:00:00:00:07", ip="10.0.0.7", hostname="echo-dot")
        assert guess_device_type(d) == "Smart Speaker"

    def test_gaming_console(self):
        d = Device(mac="00:00:00:00:00:08", ip="10.0.0.8", hostname="xbox-series-x")
        assert guess_device_type(d) == "Gaming Console"

    def test_computer_mac(self):
        d = Device(mac="00:00:00:00:00:09", ip="10.0.0.9", hostname="macbook-pro")
        assert guess_device_type(d) == "Computer"

    def test_single_board_computer(self):
        d = Device(mac="00:00:00:00:00:10", ip="10.0.0.10", hostname="raspberry-pi-4")
        assert guess_device_type(d) == "Single Board Computer"

    def test_returns_none_for_unknown(self):
        d = Device(mac="00:00:00:00:00:11", ip="10.0.0.11", hostname="unknown-device")
        assert guess_device_type(d) is None


class TestGuessOS:
    def test_windows(self):
        d = Device(mac="00:00:00:00:00:01", ip="10.0.0.1", hostname="DESKTOP-ABC")
        assert guess_os(d) == "Windows"

    def test_macos(self):
        d = Device(mac="00:00:00:00:00:02", ip="10.0.0.2", hostname="MacBook-Pro")
        assert guess_os(d) == "macOS/iOS"

    def test_linux(self):
        d = Device(mac="00:00:00:00:00:03", ip="10.0.0.3", hostname="raspberry-pi")
        assert guess_os(d) == "Linux"

    def test_android(self):
        d = Device(mac="00:00:00:00:00:04", ip="10.0.0.4", hostname="android-device")
        assert guess_os(d) == "Android"

    def test_returns_none_for_unknown(self):
        d = Device(mac="00:00:00:00:00:05", ip="10.0.0.5", hostname="unknown")
        assert guess_os(d) is None
