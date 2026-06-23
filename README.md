# Sonar — Network Device Discovery & Inventory Tool

A passive, CLI-based Network Device Discovery & Inventory tool for Windows. Discovers LAN devices via ARP cache and passive packet capture, fingerprints them, and presents results through a rich CLI interface.

> **Note**: This is V1 — a device inventory tool, not a vulnerability scanner. CVE lookups, port scanning, and service detection are planned for Phase 2.

## Prerequisites

- **Windows 10/11**
- **Python 3.10+**
- **Npcap** (optional, for enhanced packet capture) — [Download from npcap.com](https://npcap.com)
  - During installation, check "WinPcap API-compatible Mode"
  - Install Wireshark for tshark (comes with Npcap installer option)

## Quick Start

### Without Npcap (Zero Dependencies)

Works without Npcap or admin privileges — uses Windows ARP cache:

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Discover devices from ARP cache
python -m sonar scan --arp-only

# View discovered devices
python -m sonar list

# Export to JSON
python -m sonar export --output devices.json
```

### With Npcap (Full Capture)

For enhanced device discovery with mDNS, SSDP, UPnP, and DHCP traffic:

```bash
# Run as Administrator (required for packet capture)
python -m sonar scan --duration 30
```

## Usage

### Scan Command

```bash
python -m sonar scan [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--arp-only` | Skip packet capture, use ARP cache only |
| `--duration, -d` | Capture duration in seconds (default: 60) |
| `--interface, -i` | Network interface to capture on (auto-detect if not specified) |
| `--format, -f` | Output format: table or json (default: table) |
| `--db-path` | Path to SQLite database (default: ./sonar_devices.db) |
| `--verbose, -v` | Verbose output |

### List Command

```bash
python -m sonar list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--format, -f` | Output format: table or json |
| `--type` | Filter by device type (e.g., Router, Phone, Printer) |
| `--db-path` | Path to SQLite database |

### Export Command

```bash
python -m sonar export [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--output, -o` | Output file path (stdout if not specified) |
| `--db-path` | Path to SQLite database |

### Interfaces Command

```bash
python -m sonar interfaces
```

Lists available network interfaces with recommendations.

## How It Works

### ARP Cache Discovery

Sonar reads the Windows ARP cache (`Get-NetNeighbor` / `arp.exe -a`) to discover devices your computer has recently communicated with. This requires:
- No packet capture tools
- No admin privileges
- Works immediately after install

### Packet Capture (Optional)

With Npcap installed, Sonar captures broadcast/multicast traffic to discover additional devices:
- **mDNS** (port 5353): Apple Bonjour, mDNSResponder
- **SSDP** (port 1900): UPnP device discovery
- **UPnP**: Device manufacturer and type information
- **ARP**: IP-to-MAC mappings
- **DHCP** (ports 67/68): Hostnames and vendor information

### Device Fingerprinting

- **Manufacturer**: Full IEEE MAC OUI database (~40K entries)
- **Device Type**: Heuristic classification from hostname, manufacturer, and service types
- **Operating System**: Basic OS detection from hostname patterns

> ⚠️ Device type and OS classification are experimental heuristics. Accuracy depends on device behavior.

## Limitations

- This is a device inventory tool, not a vulnerability scanner (CVE lookups, port scanning, service detection are Phase 2)
- Passive packet capture only sees broadcast/multicast traffic on switched networks
- ARP cache only shows devices the host has recently communicated with
- Heuristic device type/OS classification may be inaccurate
- IPv4 only (V1)
- Requires admin privileges for packet capture (ARP cache works without admin)

## Troubleshooting

### No devices found from ARP cache
- Ensure you're connected to a network
- Try pinging other devices first to populate the ARP cache
- Check `Get-NetNeighbor` in PowerShell to verify ARP cache contents

### Npcap not detected
- Install Npcap from [npcap.com](https://npcap.com)
- Check "WinPcap API-compatible Mode" during installation
- Restart the application after installation

### Admin rights required
- Right-click Command Prompt → "Run as administrator"
- Or use `--arp-only` flag for non-admin operation

### Wi-Fi capture shows zero packets
- Some Windows configurations restrict Wi-Fi capture
- Try using an Ethernet connection for better capture results
- Use `--arp-only` as fallback

## Development

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_database.py -v
```

### Updating OUI Database

```bash
python scripts/download_oui.py
```

## License

MIT
