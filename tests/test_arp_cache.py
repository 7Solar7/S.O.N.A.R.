from unittest.mock import patch
from sonar.arp_cache import ArpEntry, get_devices_from_arp


class TestGetDevicesFromArp:
    def test_empty_list(self):
        assert get_devices_from_arp([]) == []

    def test_with_entries(self):
        entries = [
            ArpEntry(ip="10.0.0.1", mac="aa:bb:cc:11:22:33", state="Reachable"),
            ArpEntry(ip="10.0.0.2", mac="DD:EE:FF:00:11:22", state="Stale"),
        ]
        devices = get_devices_from_arp(entries)
        assert len(devices) == 2
        assert devices[0].mac == "AA:BB:CC:11:22:33"
        assert devices[0].ip == "10.0.0.1"
        assert devices[0].discovery_method == "ARP_cache"
        assert devices[1].mac == "DD:EE:FF:00:11:22"

    def test_skips_incomplete_state(self):
        entries = [
            ArpEntry(ip="10.0.0.1", mac="aa:bb:cc:11:22:33", state="Reachable"),
            ArpEntry(ip="10.0.0.2", mac="dd:ee:ff:00:11:22", state="Incomplete"),
            ArpEntry(ip="10.0.0.3", mac="11:22:33:44:55:66", state=""),
        ]
        devices = get_devices_from_arp(entries)
        assert len(devices) == 1

    def test_invalid_macs_skipped(self):
        entries = [
            ArpEntry(ip="10.0.0.1", mac="00:00:00:00:00:00", state="Reachable"),
            ArpEntry(ip="10.0.0.2", mac="aa:bb:cc", state="Reachable"),
            ArpEntry(ip="10.0.0.3", mac="", state="Reachable"),
        ]
        devices = get_devices_from_arp(entries)
        assert len(devices) == 0

    def test_mac_normalization(self):
        entries = [
            ArpEntry(ip="10.0.0.1", mac="aa-bb-cc-dd-ee-ff", state="Reachable"),
            ArpEntry(ip="10.0.0.2", mac="AABBCCDDEEFF", state="Reachable"),
        ]
        devices = get_devices_from_arp(entries)
        assert len(devices) == 2
        assert devices[0].mac == "AA:BB:CC:DD:EE:FF"
        assert devices[1].mac == "AA:BB:CC:DD:EE:FF"

    @patch("sonar.arp_cache.read_arp_cache")
    def test_none_calls_read_arp_cache(self, mock_read):
        mock_read.return_value = [
            ArpEntry(ip="10.0.0.1", mac="aa:bb:cc:11:22:33", state="Reachable")
        ]
        devices = get_devices_from_arp()
        assert len(devices) == 1
        mock_read.assert_called_once()
