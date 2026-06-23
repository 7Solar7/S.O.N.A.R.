import logging
from sonar.models import Device, _utcnow_iso
from sonar.capture import CaptureProvider
from sonar.arp_cache import get_devices_from_arp

logger = logging.getLogger(__name__)


class PacketParser:
    @staticmethod
    def parse_arp(packet) -> Device | None:
        try:
            if not hasattr(packet, 'arp'):
                return None
            arp = packet.arp
            mac = getattr(arp, 'src_hw_mac', None)
            ip = getattr(arp, 'src_proto_ipv4', None)
            if not mac or not ip:
                return None
            return Device(mac=mac, ip=ip, discovery_method="ARP")
        except Exception as e:
            logger.debug(f"Failed to parse ARP: {e}")
            return None

    @staticmethod
    def parse_mdns(packet) -> Device | None:
        try:
            if not hasattr(packet, 'dns') or not hasattr(packet, 'ip'):
                return None
            dns = packet.dns
            ip = getattr(packet.ip, 'src', None)
            if not ip:
                return None
            hostname = None
            if hasattr(dns, 'resp_name') and dns.resp_name:
                name = dns.resp_name[0] if isinstance(dns.resp_name, list) else dns.resp_name
                hostname = name.replace('.local', '').replace('.local.', '')
            return Device(mac="", ip=ip, hostname=hostname, discovery_method="mDNS")
        except Exception as e:
            logger.debug(f"Failed to parse mDNS: {e}")
            return None

    @staticmethod
    def parse_ssdp(packet) -> Device | None:
        try:
            if not hasattr(packet, 'ssdp'):
                return None
            ssdp = packet.ssdp
            location = getattr(ssdp, 'location', '')
            ip = ""
            if location:
                import re
                match = re.search(r'(\d+\.\d+\.\d+\.\d+)', location)
                if match:
                    ip = match.group(1)
            if not ip:
                return None
            manufacturer = None
            server = getattr(ssdp, 'server', '')
            if server:
                parts = server.split('/')
                if len(parts) > 1:
                    manufacturer = parts[-1].strip()
                elif parts:
                    manufacturer = parts[0].strip()
            return Device(mac="", ip=ip, manufacturer=manufacturer, discovery_method="SSDP")
        except Exception as e:
            logger.debug(f"Failed to parse SSDP: {e}")
            return None

    @staticmethod
    def parse_dhcp(packet) -> Device | None:
        try:
            if not hasattr(packet, 'dhcp'):
                return None
            dhcp = packet.dhcp
            hostname = getattr(dhcp, 'option_hostname', None)
            ip = getattr(dhcp, 'ip', None)
            mac = None
            if hasattr(packet, 'eth'):
                mac = getattr(packet.eth, 'src', None)
            if not mac and not ip:
                return None
            return Device(mac=mac or "", ip=ip or "", hostname=hostname, discovery_method="DHCP")
        except Exception as e:
            logger.debug(f"Failed to parse DHCP: {e}")
            return None

    @staticmethod
    def parse_upnp(packet) -> Device | None:
        try:
            if not hasattr(packet, 'http'):
                return None
            return None
        except Exception:
            return None

    @staticmethod
    def parse_packet(packet) -> Device | None:
        if hasattr(packet, 'arp'):
            return PacketParser.parse_arp(packet)
        if hasattr(packet, 'dns') and hasattr(packet, 'ip'):
            return PacketParser.parse_mdns(packet)
        if hasattr(packet, 'ssdp'):
            return PacketParser.parse_ssdp(packet)
        if hasattr(packet, 'dhcp'):
            return PacketParser.parse_dhcp(packet)
        return None


class Discoverer:
    def __init__(self, capture_provider: CaptureProvider):
        self._provider = capture_provider

    def discover(self, interface: str, duration: int, use_arp_cache: bool = True, arp_only: bool = False) -> list[Device]:
        devices: dict[str, Device] = {}
        
        if use_arp_cache:
            arp_devices = get_devices_from_arp()
            for d in arp_devices:
                devices[d.mac] = d
        
        if not arp_only:
            try:
                for packet in self._provider.capture(interface, duration):
                    device = PacketParser.parse_packet(packet)
                    if device and device.mac:
                        raw = device.mac.replace(":", "").replace("-", "").upper()
                        normalized = ":".join(raw[i:i+2] for i in range(0, 12, 2))
                        if normalized in devices:
                            existing = devices[normalized]
                            if device.ip and device.ip != existing.ip:
                                existing.ip = device.ip
                            if device.hostname and not existing.hostname:
                                existing.hostname = device.hostname
                            if device.manufacturer and not existing.manufacturer:
                                existing.manufacturer = device.manufacturer
                            existing.last_seen = _utcnow_iso()
                        else:
                            device.mac = normalized
                            devices[normalized] = device
            except Exception as e:
                logger.warning(f"Packet capture failed: {e}")
        
        return list(devices.values())
