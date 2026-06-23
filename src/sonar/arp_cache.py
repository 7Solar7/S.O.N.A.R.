import subprocess
import re
from dataclasses import dataclass
from sonar.models import Device, _utcnow_iso


@dataclass
class ArpEntry:
    ip: str
    mac: str
    state: str


def read_arp_cache() -> list[ArpEntry]:
    entries = []
    try:
        result = subprocess.run(
            ["powershell", "-Command", "Get-NetNeighbor | Select-Object IPAddress, LinkLayerAddress, State | ConvertTo-Json"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            import json
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                data = [data]
            for item in data:
                ip = item.get("IPAddress", "")
                mac = item.get("LinkLayerAddress", "")
                state = item.get("State", "Unknown")
                if ip and mac and ":" not in ip and state != "Incomplete":
                    entries.append(ArpEntry(ip=ip, mac=mac, state=state))
            return entries
    except Exception:
        pass
    
    try:
        result = subprocess.run(
            ["arp", "-a"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                match = re.match(r"\s*(\d+\.\d+\.\d+\.\d+)\s+([\da-fA-F:-]{17})\s+(\w+)", line)
                if match:
                    ip, mac, state = match.groups()
                    entries.append(ArpEntry(ip=ip, mac=mac, state=state))
    except Exception:
        pass
    
    return entries


def get_devices_from_arp(cache_entries: list[ArpEntry] | None = None) -> list[Device]:
    if cache_entries is None:
        cache_entries = read_arp_cache()
    
    devices = []
    for entry in cache_entries:
        if entry.state in ("Incomplete", ""): 
            continue
        raw = entry.mac.replace(":", "").replace("-", "").upper()
        if len(raw) != 12 or raw == "000000000000":
            continue
        normalized_mac = ":".join(raw[i:i+2] for i in range(0, 12, 2))
        devices.append(Device(
            mac=normalized_mac,
            ip=entry.ip,
            discovery_method="ARP_cache",
        ))
    return devices
