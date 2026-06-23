from unittest.mock import MagicMock, patch
import json
import tempfile

from sonar.discover import Discoverer
from sonar.capture import CaptureProvider, InterfaceInfo
from sonar.database import init_db, get_all_devices, get_device_by_mac, get_statistics, close
from sonar.exporter import export_json, export_table, export_summary


def test_full_pipeline():
    provider = MagicMock(spec=CaptureProvider)

    arp_packet = MagicMock()
    arp_packet.arp.src_hw_mac = "aa:bb:cc:11:22:33"
    arp_packet.arp.src_proto_ipv4 = "192.168.1.10"

    mdns_packet = MagicMock()
    del mdns_packet.arp
    mdns_packet.dns.resp_name = "printer.local"
    mdns_packet.ip.src = "192.168.1.20"

    provider.capture.return_value = iter([arp_packet, mdns_packet])
    provider.get_interfaces.return_value = [
        InterfaceInfo(name="1", description="Realtek", is_virtual=False)
    ]
    provider.check_dependencies.return_value = []

    with patch("sonar.discover.get_devices_from_arp") as mock_arp:
        mock_arp.return_value = []

        discoverer = Discoverer(provider)
        devices = discoverer.discover("eth0", 5, use_arp_cache=True, arp_only=False)

    assert len(devices) == 2

    arp_dev = next(d for d in devices if d.discovery_method == "ARP")
    mdns_dev = next(d for d in devices if d.discovery_method == "mDNS")

    assert arp_dev.mac == "AA:BB:CC:11:22:33"
    assert arp_dev.ip == "192.168.1.10"

    assert mdns_dev.mac == ":::::"
    assert mdns_dev.ip == "192.168.1.20"
    assert mdns_dev.hostname == "printer"

    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    conn = init_db(f.name)
    for d in devices:
        from sonar.database import upsert_device
        upsert_device(conn, d)

    all_devices = get_all_devices(conn)
    assert len(all_devices) == 2

    stats = get_statistics(conn)
    assert stats["total_devices"] == 2

    retrieved = get_device_by_mac(conn, "AA:BB:CC:11:22:33")
    assert retrieved is not None
    assert retrieved.ip == "192.168.1.10"

    json_output = export_json(all_devices)
    data = json.loads(json_output)
    assert len(data) == 2

    table_output = export_table(all_devices)
    assert "AA:BB:CC:11:22:33" in table_output
    assert "printer" in table_output

    summary = export_summary(all_devices)
    assert "2 device(s)" in summary

    close(conn)
