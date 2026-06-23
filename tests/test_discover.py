from unittest.mock import MagicMock, patch
import pytest
from sonar.discover import PacketParser, Discoverer
from sonar.models import Device
from sonar.capture import CaptureProvider


class TestPacketParserParseARP:
    def test_returns_device_for_arp_packet(self, mock_arp_packet):
        d = PacketParser.parse_arp(mock_arp_packet)
        assert d is not None
        assert d.mac == "AA:BB:CC:DD:EE:FF"
        assert d.ip == "192.168.1.10"
        assert d.discovery_method == "ARP"

    def test_returns_none_for_non_arp_packet(self):
        pkt = MagicMock()
        del pkt.arp
        assert PacketParser.parse_arp(pkt) is None

    def test_returns_none_when_missing_fields(self):
        pkt = MagicMock()
        pkt.arp.src_hw_mac = None
        pkt.arp.src_proto_ipv4 = None
        assert PacketParser.parse_arp(pkt) is None


class TestPacketParserParseMDNS:
    def test_returns_device_for_mdns_packet(self, mock_mdns_packet):
        d = PacketParser.parse_mdns(mock_mdns_packet)
        assert d is not None
        assert d.ip == "192.168.1.20"
        assert d.hostname == "myhost"
        assert d.discovery_method == "mDNS"

    def test_returns_none_without_dns(self):
        pkt = MagicMock()
        del pkt.dns
        assert PacketParser.parse_mdns(pkt) is None

    def test_returns_none_without_ip(self):
        pkt = MagicMock()
        del pkt.ip
        assert PacketParser.parse_mdns(pkt) is None


class TestPacketParserParseSSDP:
    def test_returns_device_for_ssdp_packet(self, mock_ssdp_packet):
        d = PacketParser.parse_ssdp(mock_ssdp_packet)
        assert d is not None
        assert d.ip == "192.168.1.30"
        assert d.manufacturer == "MiniUPnP"
        assert d.discovery_method == "SSDP"

    def test_returns_none_without_ssdp(self):
        pkt = MagicMock()
        del pkt.ssdp
        assert PacketParser.parse_ssdp(pkt) is None


class TestPacketParserParseDHCP:
    def test_returns_device_for_dhcp_packet(self, mock_dhcp_packet):
        d = PacketParser.parse_dhcp(mock_dhcp_packet)
        assert d is not None
        assert d.ip == "192.168.1.40"
        assert d.hostname == "dhcp-client"
        assert d.mac == "11:22:33:44:55:66"
        assert d.discovery_method == "DHCP"

    def test_returns_none_without_dhcp(self):
        pkt = MagicMock()
        del pkt.dhcp
        assert PacketParser.parse_dhcp(pkt) is None


class TestPacketParserParsePacket:
    def test_dispatches_arp(self, mock_arp_packet):
        d = PacketParser.parse_packet(mock_arp_packet)
        assert d is not None
        assert d.discovery_method == "ARP"

    def test_dispatches_mdns(self, mock_mdns_packet):
        d = PacketParser.parse_packet(mock_mdns_packet)
        assert d is not None
        assert d.discovery_method == "mDNS"

    def test_dispatches_ssdp(self, mock_ssdp_packet):
        d = PacketParser.parse_packet(mock_ssdp_packet)
        assert d is not None
        assert d.discovery_method == "SSDP"

    def test_dispatches_dhcp(self, mock_dhcp_packet):
        d = PacketParser.parse_packet(mock_dhcp_packet)
        assert d is not None
        assert d.discovery_method == "DHCP"

    def test_returns_none_for_unknown(self):
        pkt = MagicMock()
        del pkt.arp
        del pkt.dns
        del pkt.ssdp
        del pkt.dhcp
        assert PacketParser.parse_packet(pkt) is None


class TestDiscoverer:
    @patch("sonar.discover.get_devices_from_arp")
    def test_discover_arp_only(self, mock_arp, mock_provider):
        mock_arp.return_value = [
            Device(mac="AA:BB:CC:11:22:33", ip="10.0.0.1", discovery_method="ARP_cache")
        ]
        d = Discoverer(mock_provider)
        results = d.discover("eth0", 10, use_arp_cache=True, arp_only=True)
        assert len(results) == 1
        assert results[0].ip == "10.0.0.1"

    @patch("sonar.discover.get_devices_from_arp")
    def test_discover_merges_arp_and_capture(self, mock_arp, mock_provider):
        mock_arp.return_value = [
            Device(mac="AA:BB:CC:11:22:33", ip="10.0.0.1", discovery_method="ARP_cache")
        ]

        cap_pkt = MagicMock()
        cap_pkt.arp.src_hw_mac = "aa:bb:cc:11:22:33"
        cap_pkt.arp.src_proto_ipv4 = "10.0.0.1"
        mock_provider.capture.return_value = iter([cap_pkt])

        d = Discoverer(mock_provider)
        results = d.discover("eth0", 10, use_arp_cache=True, arp_only=False)
        assert len(results) == 1

    @patch("sonar.discover.get_devices_from_arp")
    def test_discover_skips_arp_cache(self, mock_arp, mock_provider):
        mock_arp.return_value = [
            Device(mac="AA:BB:CC:11:22:33", ip="10.0.0.1", discovery_method="ARP_cache")
        ]
        d = Discoverer(mock_provider)
        results = d.discover("eth0", 10, use_arp_cache=False, arp_only=False)
        assert len(results) == 0

    @patch("sonar.discover.get_devices_from_arp")
    def test_discover_handles_capture_failure(self, mock_arp, mock_provider):
        mock_arp.return_value = []
        mock_provider.capture.side_effect = RuntimeError("boom")
        d = Discoverer(mock_provider)
        results = d.discover("eth0", 10, use_arp_cache=True, arp_only=False)
        assert results == []
