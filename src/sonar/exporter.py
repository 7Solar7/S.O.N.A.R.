import io
import json
from sonar.models import Device
from rich.console import Console
from rich.table import Table


def export_json(devices: list[Device], filepath: str | None = None) -> str:
    data = [
        {
            "mac": d.mac,
            "ip": d.ip,
            "hostname": d.hostname,
            "manufacturer": d.manufacturer,
            "os": d.os,
            "device_type": d.device_type,
            "first_seen": d.first_seen,
            "last_seen": d.last_seen,
            "discovery_method": d.discovery_method,
        }
        for d in devices
    ]
    json_str = json.dumps(data, indent=2)
    if filepath:
        with open(filepath, "w") as f:
            f.write(json_str)
    return json_str


def export_table(devices: list[Device]) -> str:
    if not devices:
        return handle_empty(devices)
    
    table = Table(title="Discovered Devices")
    table.add_column("MAC", style="cyan", no_wrap=True)
    table.add_column("IP", style="green")
    table.add_column("Hostname", style="yellow")
    table.add_column("Manufacturer", style="blue")
    table.add_column("Type", style="magenta")
    table.add_column("OS", style="red")
    table.add_column("First Seen", style="dim")
    table.add_column("Last Seen", style="dim")
    
    for d in devices:
        table.add_row(
            d.mac,
            d.ip,
            d.hostname or "-",
            d.manufacturer or "-",
            d.device_type or "-",
            d.os or "-",
            d.first_seen,
            d.last_seen,
        )
    
    console = Console(record=True, file=io.StringIO(), width=200)
    console.print(table)
    return console.export_text()


def export_summary(devices: list[Device]) -> str:
    if not devices:
        return handle_empty(devices)
    
    total = len(devices)
    by_type = {}
    by_manufacturer = {}
    
    for d in devices:
        t = d.device_type or "Unknown"
        by_type[t] = by_type.get(t, 0) + 1
        m = d.manufacturer or "Unknown"
        by_manufacturer[m] = by_manufacturer.get(m, 0) + 1
    
    lines = [f"Network Summary: {total} device(s) discovered"]
    lines.append("")
    lines.append("By Type:")
    for t, count in sorted(by_type.items(), key=lambda x: -x[1]):
        lines.append(f"  {t}: {count}")
    lines.append("")
    lines.append("By Manufacturer:")
    for m, count in sorted(by_manufacturer.items(), key=lambda x: -x[1]):
        lines.append(f"  {m}: {count}")
    
    return "\n".join(lines)


def handle_empty(devices: list[Device]) -> str:
    if not devices:
        return "No devices discovered yet. Run 'sonar scan' first."
    return export_table(devices)
