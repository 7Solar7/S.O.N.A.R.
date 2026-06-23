from collections.abc import Generator
from unittest.mock import MagicMock, patch, create_autospec
from typing import Any
import tempfile
import pytest
from sonar.models import Device
from sonar.arp_cache import ArpEntry
from sonar.capture import CaptureProvider, InterfaceInfo


@pytest.fixture
def sample_device() -> Device:
    return Device(
        mac="aa:bb:cc:dd:ee:ff",
        ip="192.168.1.100",
        hostname="test-device",
        manufacturer="TestCorp",
        os="Linux",
        device_type="Computer",
        first_seen="2024-01-01T00:00:00Z",
        last_seen="2024-01-01T00:00:00Z",
        discovery_method="ARP",
    )


@pytest.fixture
def sample_entries() -> list[ArpEntry]:
    return [
        ArpEntry(ip="192.168.1.1", mac="aa:bb:cc:11:22:33", state="Reachable"),
        ArpEntry(ip="192.168.1.2", mac="DD:EE:FF-00-11-22", state="Stale"),
        ArpEntry(ip="192.168.1.3", mac="11:22:33:44:55:66", state="Permanent"),
    ]


@pytest.fixture
def mock_provider() -> MagicMock:
    provider = create_autospec(CaptureProvider, instance=True)

    def fake_capture(*args, **kwargs) -> Generator[Any, None, None]:
        yield from ()

    provider.capture.side_effect = fake_capture
    provider.get_interfaces.return_value = [
        InterfaceInfo(name="1", description="Realtek", is_virtual=False, is_loopback=False, is_up=True),
        InterfaceInfo(name="2", description="VMware Virtual Ethernet", is_virtual=True, is_loopback=False, is_up=True),
    ]
    provider.check_dependencies.return_value = []
    return provider


@pytest.fixture
def test_db():
    conn = None
    try:
        from sonar.database import init_db, close
        f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        f.close()
        conn = init_db(f.name)
        yield conn, f.name
    finally:
        if conn:
            close(conn)


@pytest.fixture
def mock_arp_packet() -> MagicMock:
    pkt = MagicMock()
    pkt.arp.src_hw_mac = "aa:bb:cc:dd:ee:ff"
    pkt.arp.src_proto_ipv4 = "192.168.1.10"
    return pkt


@pytest.fixture
def mock_mdns_packet() -> MagicMock:
    pkt = MagicMock()
    del pkt.arp
    pkt.dns.resp_name = "myhost.local"
    pkt.ip.src = "192.168.1.20"
    return pkt


@pytest.fixture
def mock_ssdp_packet() -> MagicMock:
    pkt = MagicMock()
    del pkt.arp
    del pkt.dns
    pkt.ssdp.location = "http://192.168.1.30:5000/desc.xml"
    pkt.ssdp.server = "MiniUPnP"
    return pkt


@pytest.fixture
def mock_dhcp_packet() -> MagicMock:
    pkt = MagicMock()
    del pkt.arp
    del pkt.dns
    del pkt.ssdp
    pkt.dhcp.option_hostname = "dhcp-client"
    pkt.dhcp.ip = "192.168.1.40"
    pkt.eth.src = "11:22:33:44:55:66"
    return pkt


@pytest.fixture
def sample_oui_csv(tmp_path) -> str:
    content = (
        "AA:BB:CC,TestCorp\n"
        "DD:EE:FF:00,AnotherCorp\n"
        "11:22:33:44:55,PreciseCorp\n"
    )
    f = tmp_path / "sonar_oui.csv"
    f.write_text(content)
    return str(f)
