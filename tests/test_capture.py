import os
from unittest.mock import patch, MagicMock
from sonar.capture import (
    check_tshark, check_admin, get_best_interface,
    InterfaceInfo, PysharkCaptureProvider, CaptureProvider,
)


class TestCheckTshark:
    @patch("sonar.capture.subprocess.run")
    def test_returns_false_when_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError
        assert check_tshark() is False

    @patch("sonar.capture.subprocess.run")
    def test_returns_false_on_error(self, mock_run):
        mock_run.side_effect = PermissionError
        assert check_tshark() is False

    @patch("sonar.capture.subprocess.run")
    def test_returns_true_when_found(self, mock_run):
        mock_run.return_value.returncode = 0
        assert check_tshark() is True

    @patch("sonar.capture.subprocess.run")
    def test_returns_false_nonzero_exit(self, mock_run):
        mock_run.return_value.returncode = 1
        assert check_tshark() is False


class TestCheckAdmin:
    @patch("sonar.capture.platform.system", return_value="Windows")
    @patch("ctypes.windll.shell32.IsUserAnAdmin", return_value=True)
    def test_admin_windows(self, mock_admin, mock_system):
        assert check_admin() is True

    @patch("sonar.capture.platform.system", return_value="Windows")
    @patch("ctypes.windll.shell32.IsUserAnAdmin", return_value=False)
    def test_not_admin_windows(self, mock_admin, mock_system):
        assert check_admin() is False

    @patch("sonar.capture.platform.system", return_value="Linux")
    @patch.object(os, "getuid", return_value=0, create=True)
    def test_admin_linux(self, mock_getuid, mock_system):
        assert check_admin() is True

    @patch("sonar.capture.platform.system", return_value="Linux")
    @patch.object(os, "getuid", return_value=1000, create=True)
    def test_not_admin_linux(self, mock_getuid, mock_system):
        assert check_admin() is False


class TestPysharkCaptureProvider:
    def test_mock_capture_provider(self):
        class MockProvider(CaptureProvider):
            def get_interfaces(self):
                return [InterfaceInfo(name="eth0", description="Test", is_up=True)]

            def capture(self, interface, duration, bpf_filter=""):
                return iter([])

            def check_dependencies(self):
                return []

        p = MockProvider()
        assert len(p.get_interfaces()) == 1
        assert list(p.capture("eth0", 5)) == []
        assert p.check_dependencies() == []

    @patch("sonar.capture.subprocess.run")
    def test_get_interfaces_parse(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = (
            "1. Realtek PCIe GbE Family Controller\n"
            "2. VMware Virtual Ethernet Adapter\n"
            "3. Loopback Pseudo-Interface 1\n"
        )
        provider = PysharkCaptureProvider()
        ifaces = provider.get_interfaces()
        assert len(ifaces) == 3
        assert ifaces[0].name == "1"
        assert ifaces[0].is_virtual is False
        assert ifaces[0].is_loopback is False
        assert ifaces[1].name == "2"
        assert ifaces[1].is_virtual is True
        assert ifaces[2].name == "3"
        assert ifaces[2].is_loopback is True

    @patch("sonar.capture.subprocess.run")
    def test_get_interfaces_tshark_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError
        provider = PysharkCaptureProvider()
        assert provider.get_interfaces() == []

    @patch("sonar.capture.subprocess.run")
    def test_check_dependencies_tshark_missing(self, mock_run):
        mock_run.side_effect = FileNotFoundError
        provider = PysharkCaptureProvider()
        deps = provider.check_dependencies()
        assert any("tshark" in d for d in deps)


class TestGetBestInterface:
    @patch("sonar.capture.subprocess.run")
    def test_prefers_wireless(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = (
            "1. Realtek PCIe GbE Family Controller\n"
            "2. Intel Wi-Fi 6 AX201\n"
        )
        assert get_best_interface() == "2"

    @patch("sonar.capture.subprocess.run")
    def test_skips_virtual_and_loopback(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = (
            "1. VMware Virtual Ethernet Adapter\n"
            "2. Loopback Pseudo-Interface 1\n"
            "3. Realtek PCIe GbE Family Controller\n"
        )
        assert get_best_interface() == "3"

    @patch("sonar.capture.subprocess.run")
    def test_returns_none_when_tshark_missing(self, mock_run):
        mock_run.side_effect = FileNotFoundError
        assert get_best_interface() is None

    @patch("sonar.capture.subprocess.run")
    def test_returns_none_on_failure(self, mock_run):
        mock_run.return_value.returncode = 1
        assert get_best_interface() is None

    @patch("sonar.capture.subprocess.run")
    def test_returns_first_non_virtual(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "1. Realtek PCIe GbE Family Controller\n"
        assert get_best_interface() == "1"
