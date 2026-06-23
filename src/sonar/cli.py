import sys
import io
import click
from sonar.database import init_db, upsert_device, get_all_devices, get_device_count, close
from sonar.arp_cache import get_devices_from_arp
from sonar.discover import Discoverer
from sonar.capture import PysharkCaptureProvider, get_best_interface, check_admin
from sonar.fingerprint import load_oui_db, lookup_manufacturer, guess_device_type, guess_os
from sonar.exporter import export_json, export_table, export_summary


@click.group()
def main():
    """S.O.N.A.R. - Silent Observer for Network ARP & Reconnaissance"""
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


@main.command()
@click.option("--interface", "-i", default=None, help="Network interface to capture on")
@click.option("--duration", "-d", default=60, type=int, help="Capture duration in seconds")
@click.option("--format", "-f", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.option("--db-path", default="./sonar_devices.db", help="Path to SQLite database")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Verbose output")
@click.option("--arp-only", is_flag=True, default=False, help="Skip packet capture, use ARP cache only")
def scan(interface, duration, output_format, db_path, verbose, arp_only):
    """Scan the network for devices."""
    conn = init_db(db_path)
    oui_db = load_oui_db()

    click.echo("Phase 1: Reading ARP cache...")
    arp_devices = get_devices_from_arp()

    if not arp_devices:
        click.echo("ARP cache is empty. No devices found.")
    else:
        click.echo(f"  Found {len(arp_devices)} device(s) in ARP cache.")

    all_devices = {d.mac: d for d in arp_devices}

    if not arp_only:
        click.echo("\nPhase 2: Checking dependencies...")
        provider = PysharkCaptureProvider()
        missing = provider.check_dependencies()

        if missing:
            click.echo("Packet capture unavailable:")
            for msg in missing:
                click.echo(f"  - {msg}")
            click.echo("  Falling back to ARP cache only.")
        else:
            if not check_admin():
                click.echo("Not running as admin. Some capture features may be limited.")

            target_interface = interface or get_best_interface()
            if not target_interface:
                click.echo("No suitable network interface found.")
                click.echo("  Falling back to ARP cache only.")
            else:
                click.echo(f"  Capturing on interface: {target_interface}")
                click.echo(f"  Duration: {duration}s")

                try:
                    discoverer = Discoverer(provider)
                    captured = discoverer.discover(target_interface, duration, use_arp_cache=False)

                    if not captured:
                        click.echo("Packet capture returned zero packets.")
                    else:
                        click.echo(f"  Captured {len(captured)} device(s) from packets.")
                        for d in captured:
                            if d.mac not in all_devices:
                                all_devices[d.mac] = d
                            else:
                                existing = all_devices[d.mac]
                                if d.ip and d.ip != existing.ip:
                                    existing.ip = d.ip
                                if d.hostname and not existing.hostname:
                                    existing.hostname = d.hostname
                                if d.manufacturer and not existing.manufacturer:
                                    existing.manufacturer = d.manufacturer
                except Exception as e:
                    click.echo(f"Capture failed: {e}")
                    click.echo("  Continuing with ARP cache data.")

    click.echo("\nPhase 3: Fingerprinting...")
    for mac, device in all_devices.items():
        if not device.manufacturer:
            device.manufacturer = lookup_manufacturer(device.mac, oui_db)
        if not device.device_type:
            device.device_type = guess_device_type(device)
        if not device.os:
            device.os = guess_os(device)

    click.echo("\nPhase 4: Storing results...")
    for device in all_devices.values():
        upsert_device(conn, device)

    total = get_device_count(conn)
    click.echo(f"  Total devices in database: {total}")

    devices_list = list(all_devices.values())
    click.echo(f"\nScan complete. {len(devices_list)} device(s) discovered this scan.\n")

    if output_format == "json":
        click.echo(export_json(devices_list))
    else:
        click.echo(export_table(devices_list))
        click.echo()
        click.echo(export_summary(devices_list))

    close(conn)


@main.command("list")
@click.option("--db-path", default="./sonar_devices.db", help="Path to SQLite database")
@click.option("--format", "-f", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.option("--type", "device_type", default=None, help="Filter by device type")
def list_devices(db_path, output_format, device_type):
    """List discovered devices."""
    conn = init_db(db_path)
    devices = get_all_devices(conn)
    close(conn)

    if device_type:
        devices = [d for d in devices if d.device_type and d.device_type.lower() == device_type.lower()]

    if not devices:
        click.echo("No devices discovered yet. Run 'sonar scan' first.")
        return

    if output_format == "json":
        click.echo(export_json(devices))
    else:
        click.echo(export_table(devices))
        click.echo()
        click.echo(export_summary(devices))


@main.command()
@click.option("--db-path", default="./sonar_devices.db", help="Path to SQLite database")
@click.option("--output", "-o", default=None, help="Output file path (stdout if not specified)")
def export(db_path, output):
    """Export all devices as JSON."""
    conn = init_db(db_path)
    devices = get_all_devices(conn)
    close(conn)

    if not devices:
        click.echo("[]")
        return

    if output:
        export_json(devices, filepath=output)
        click.echo(f"Exported {len(devices)} device(s) to {output}")
    else:
        click.echo(export_json(devices))


@main.command()
def interfaces():
    """List available network interfaces."""
    provider = PysharkCaptureProvider()
    ifaces = provider.get_interfaces()

    if not ifaces:
        click.echo("No interfaces found. Is tshark/Npcap installed?")
        return

    best = get_best_interface()
    click.echo("Available network interfaces:\n")
    for iface in ifaces:
        flags = []
        if iface.is_virtual:
            flags.append("virtual")
        if iface.is_loopback:
            flags.append("loopback")
        if not iface.is_up:
            flags.append("down")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        recommended = " <- recommended" if best == iface.name else ""
        click.echo(f"  {iface.name}: {iface.description}{flag_str}{recommended}")
