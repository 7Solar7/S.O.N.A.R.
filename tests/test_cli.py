from unittest.mock import patch, MagicMock
from click.testing import CliRunner
import pytest
from sonar.cli import main
from sonar.arp_cache import ArpEntry
from sonar.models import Device


@pytest.fixture
def runner():
    return CliRunner()


class TestInterfacesCommand:
    @patch("sonar.cli.PysharkCaptureProvider")
    def test_interfaces_no_tshark(self, mock_provider_cls, runner):
        provider = mock_provider_cls.return_value
        provider.get_interfaces.return_value = []
        result = runner.invoke(main, ["interfaces"])
        assert result.exit_code == 0
        assert "No interfaces found" in result.output

    @patch("sonar.cli.get_best_interface")
    @patch("sonar.cli.PysharkCaptureProvider")
    def test_interfaces_with_ifaces(self, mock_provider_cls, mock_best, runner):
        from sonar.capture import InterfaceInfo
        provider = mock_provider_cls.return_value
        provider.get_interfaces.return_value = [
            InterfaceInfo(name="1", description="Realtek", is_virtual=False),
        ]
        mock_best.return_value = "1"
        result = runner.invoke(main, ["interfaces"])
        assert result.exit_code == 0
        assert "Realtek" in result.output
        assert "recommended" in result.output


class TestScanCommand:
    @patch("sonar.cli.PysharkCaptureProvider")
    @patch("sonar.cli.get_devices_from_arp")
    @patch("sonar.cli.init_db")
    @patch("sonar.cli.load_oui_db")
    def test_scan_arp_only_empty(
        self, mock_oui, mock_db, mock_arp, mock_provider_cls, runner
    ):
        mock_arp.return_value = []
        result = runner.invoke(main, ["scan", "--arp-only"])
        assert result.exit_code == 0
        assert "Phase 1" in result.output
        assert "ARP cache is empty" in result.output

    @patch("sonar.cli.get_device_count")
    @patch("sonar.cli.PysharkCaptureProvider")
    @patch("sonar.cli.get_devices_from_arp")
    @patch("sonar.cli.init_db")
    @patch("sonar.cli.load_oui_db")
    def test_scan_arp_only_with_devices(
        self, mock_oui, mock_db, mock_arp, mock_provider_cls, mock_count, runner
    ):
        mock_arp.return_value = [
            Device(mac="AA:BB:CC:11:22:33", ip="10.0.0.1", discovery_method="ARP_cache")
        ]
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_count.return_value = 1
        result = runner.invoke(main, ["scan", "--arp-only", "--format", "json"])
        assert result.exit_code == 0
        assert "AA:BB:CC:11:22:33" in result.output
        assert "Scan complete" in result.output


class TestListCommand:
    @patch("sonar.cli.init_db")
    def test_list_empty_db(self, mock_db, runner):
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []
        result = runner.invoke(main, ["list"])
        assert result.exit_code == 0
        assert "No devices discovered" in result.output

    @patch("sonar.cli.init_db")
    def test_list_with_devices(self, mock_db, runner):
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        row = {
            "mac": "AA:BB:CC:11:22:33", "ip": "10.0.0.1", "hostname": None,
            "manufacturer": "TestCorp", "os": None, "device_type": "Router",
            "first_seen": "2024-01-01T00:00:00Z", "last_seen": "2024-01-01T00:00:00Z",
            "discovery_method": "ARP",
        }
        mock_conn.execute.return_value.fetchall.return_value = [row]
        result = runner.invoke(main, ["list"])
        assert result.exit_code == 0
        assert "AA:BB:CC:11:22:33" in result.output

    @patch("sonar.cli.init_db")
    def test_list_filter_by_type(self, mock_db, runner):
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []
        result = runner.invoke(main, ["list", "--type", "Router"])
        assert result.exit_code == 0


class TestExportCommand:
    @patch("sonar.cli.init_db")
    def test_export_empty_db(self, mock_db, runner):
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []
        result = runner.invoke(main, ["export"])
        assert result.exit_code == 0
        assert result.output.strip() == "[]"

    @patch("sonar.cli.init_db")
    def test_export_with_devices(self, mock_db, runner):
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        row = {
            "mac": "AA:BB:CC:11:22:33", "ip": "10.0.0.1", "hostname": None,
            "manufacturer": "TestCorp", "os": None, "device_type": None,
            "first_seen": "2024-01-01T00:00:00Z", "last_seen": "2024-01-01T00:00:00Z",
            "discovery_method": "ARP",
        }
        mock_conn.execute.return_value.fetchall.return_value = [row]
        result = runner.invoke(main, ["export"])
        assert result.exit_code == 0
        assert "AA:BB:CC:11:22:33" in result.output

    @patch("sonar.cli.init_db")
    def test_export_to_file(self, mock_db, runner, tmp_path):
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = []
        out = tmp_path / "out.json"
        result = runner.invoke(main, ["export", "--output", str(out)])
        assert result.exit_code == 0
