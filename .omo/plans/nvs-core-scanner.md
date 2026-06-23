# NVS — Network Device Discovery & Inventory Tool (Core Engine V1)

## TL;DR

> **Quick Summary**: Build a passive Network Device Discovery & Inventory tool for Windows — a Python CLI tool that discovers LAN devices by reading the Windows ARP cache (`Get-NetNeighbor` / `arp.exe -a`) and capturing network packets via pyshark/Npcap. It observes mDNS/SSDP/UPnP/ARP/DHCP traffic, fingerprints devices (manufacturer via full MAC OUI, hostname from DHCP/mDNS, type from service announcements), stores results in SQLite, and outputs via CLI table and JSON. No dashboard, no CVE mapping, no active scanning — those are Phase 2.
> 
> **Naming note**: This is a device inventory tool, not a vulnerability scanner. "Vulnerability scanning" (CVE lookup, port scanning, service detection) is strictly Phase 2. V1 is honest about its scope: it discovers and identifies what's on your network.
>
> **Deliverables**:
> - Python package `nvs` with CLI subcommands: `scan`, `list`, `export`, `interfaces`
> - Passive device discovery engine (mDNS, SSDP, UPnP, ARP, DHCP parsing)
> - Device fingerprinting with bundled MAC OUI manufacturer database
> - SQLite storage with proper schema
> - JSON export + rich CLI table output
> - 30+ TDD tests with mocked pyshark + offline pcap fixtures
>
> **Estimated Effort**: Medium (8-10 implementation tasks)
> **Parallel Execution**: YES — 4 waves
> **Critical Path**: Task 1 → Task 3 → Task 4 → Task 5 → Task 7 → Task 9 → F1-F4

---

## Context

### Original Request
Build a Network Device Discovery & Inventory tool for Windows based on the PRD in the project directory. V1 focuses on the core engine — passive network discovery (ARP cache + packet capture), device fingerprinting, and CLI output. Note: originally scoped as a "Vulnerability Scanner" but corrected by LLM Council review — V1 is a device inventory tool; vulnerability scanning (CVE lookup, port scanning, service detection) is Phase 2.

### Interview Summary
**Key Discussions**:
- **Tech stack**: Python 3.13, pyshark (packet capture), SQLite (stdlib), rich (CLI tables), pytest (TDD)
- **V1 scope**: Core scanner engine ONLY — no dashboard, no CVE mapping, no Windows service
- **Package name**: `nvs` — invoked as `python -m nvs scan`
- **Interface selection**: Auto-detect best non-virtual adapter, override with `--interface`
- **Default duration**: 60 seconds
- **Device dedup**: MAC address as primary key
- **MAC OUI**: Bundle offline database for manufacturer lookup
- **Test strategy**: CaptureProvider interface for mock-based unit tests; offline pcap fixtures for integration
- **Dependency isolation**: Use `.venv` (global env has corrupted packages)
- **BPF filter**: `arp or port 5353 or port 1900 or (udp port 67 or udp port 68)`

**Research Findings**:
- Npcap NOT installed — plan must include install instructions in README
- tshark NOT in PATH — pyshark needs tshark binary (comes with Wireshark or Npcap "Install tshark" option)
- Python 3.13.13 available, pyshark 0.6 (py3-none-any) should be compatible
- rich 15.0.0, click 8.4.1, pytest 9.1.0, python-dotenv 1.2.2 available globally
- Global Python env has corrupted packages (~orch, fsspec conflicts) — MUST use `.venv`
- The user's vault shows TDD + mock-interface patterns (MockOllamaClient in novel-to-video project) — this plan mirrors that pattern with CaptureProvider

### Metis Review
**Identified Gaps** (addressed):
- **15 unasked questions**: Resolved via user answers or sensible defaults (interface detection, BPF filtering, device dedup, package structure, test mocking strategy, MAC OUI bundling, etc.)
- **Npcap/tshark not installed**: Documented in plan — pre-flight check + error messaging + README install guide
- **Admin privileges**: Documented — admin required for packet capture; graceful error if missing
- **Edge cases documented**: MAC randomization, virtual adapters, no-MAC devices, switch isolation, busy networks
- **Guardrails locked**: No active scanning, no web UI, no service wrapper, no CVE in V1, no outbound calls, no ORM, no async, no config files

---

## Work Objectives

### Core Objective
Build a passive, CLI-based Network Device Discovery & Inventory tool for Windows (V1) that discovers LAN devices via the Windows ARP cache (`Get-NetNeighbor` / `arp.exe -a`) AND passive packet capture (mDNS/SSDP/UPnP/ARP/DHCP), fingerprints them (manufacturer via full MAC OUI, hostname, device type), stores results in SQLite, and outputs via CLI table and JSON — with zero active scanning, no web UI, and no CVE mapping.

### Concrete Deliverables
- `src/nvs/` — Python package with modules: `cli.py`, `capture.py`, `discover.py`, `fingerprint.py`, `models.py`, `database.py`, `exporter.py`, `arp_cache.py`
- `tests/` — Test suite with mocked CaptureProvider + offline pcap fixtures
- `nvs_oui.csv` — Bundled full IEEE MAC OUI manufacturer lookup table (~42K entries)
- `scripts/download_oui.py` — Build script to fetch and update OUI database from IEEE
- `requirements.txt` — Pinned dependencies (pyshark, rich, click, python-dotenv)
- `.env.example` — Template for future NVD_API_KEY (Phase 2)
- `README.md` — Setup guide with Npcap install instructions

### Definition of Done
- [ ] `python -m nvs scan` (with or without Npcap) exits 0 and outputs a device table (even if empty) — ARP cache fallback guarantees output without packet capture
- [ ] `python -m nvs scan --arp-only` lists devices from Windows ARP cache without requiring Npcap/admin
- [ ] `python -m nvs scan --duration 5 --format json` outputs valid JSON
- [ ] `python -m nvs list` shows previously discovered devices
- [ ] `python -m nvs export` outputs JSON array of all devices
- [ ] `python -m nvs interfaces` lists available network interfaces
- [ ] All tests pass: `pytest tests/` → green
- [ ] Missing Npcap/tshark produces clear actionable error
- [ ] Non-admin execution produces clear error about admin rights
- [ ] Database integrity: `PRAGMA integrity_check` returns "ok"

### Must Have
- **ARP cache reading** — zero-dependency device discovery via `Get-NetNeighbor` / `arp.exe -a` (works without Npcap, without admin)
- Passive packet capture via pyshark (wrapping Npcap/tshark) — supplements ARP cache with richer device info
- Device discovery from mDNS, SSDP, UPnP, ARP, DHCP traffic
- MAC-based device deduplication with `first_seen`/`last_seen` tracking
- **Full IEEE OUI manufacturer lookup** (~42K entries, not a curated subset)
- CLI subcommands: `scan`, `list`, `export`, `interfaces`; plus `scan --arp-only` for Npcap-free use
- JSON export + rich CLI table output
- Pre-flight dependency validation — check Npcap, tshark, admin elevation at startup with actionable error messages
- Graceful error handling for missing Npcap/tshark, missing admin, no traffic (ARP cache fallback keeps the tool useful without capture)
- TDD with pytest (30+ tests, CaptureProvider mock interface)
- BPF filtering to prevent resource exhaustion
- SQLite storage with WAL mode
- **Honest output labeling** — heuristic classifications flagged as experimental/low-confidence

### Must NOT Have (Guardrails)
- ❌ NO CVE lookup or NVD API calls (Phase 2)
- ❌ NO web dashboard or HTTP server (Phase 2)
- ❌ NO Windows service or background process (Phase 2)
- ❌ NO active scanning (SYN scans, ICMP pings, ARP probes) (Phase 2) — reading the Windows ARP cache (`Get-NetNeighbor` / `arp.exe -a`) is NOT active scanning; it's reading an OS-maintained table, zero packets sent
- ❌ NO marketing claims that this is a "vulnerability scanner" — V1 is a device inventory tool; the name and documentation MUST be honest about scope
- ❌ NO outbound network calls of any kind
- ❌ NO async/await or event loop
- ❌ NO ORM (SQLAlchemy, Peewee) — stdlib `sqlite3` only
- ❌ NO config file parsing (YAML/TOML/JSON) — CLI args + `.env` only
- ❌ NO empty tables for future features (no `vulnerabilities` table)
- ❌ NO continuous/watch mode (Phase 2)
- ❌ NO debug web endpoints or health check endpoints
- ❌ NO AI slop: no over-abstraction, no factory factories, no premature caching

---

## Verification Strategy

### Test Decision
- **Infrastructure**: TDD with pytest 9.1.0 (confirmed available)
- **Framework**: pytest with `pytest-mock` for CaptureProvider mocking
- **TDD**: Each functional task follows RED (failing test) → GREEN (minimal impl) → REFACTOR
- **Integration**: Offline pcap fixtures for end-to-end capture→discover→store→export testing

### QA Policy
Every task MUST include agent-executed QA scenarios. Evidence saved to `.omo/evidence/task-{N}-{scenario-slug}.{ext}`.

- **CLI/testing**: Use Bash — run commands with `python -m nvs`, assert exit codes + stdout/stderr content
- **Database verification**: Use inline Python — `python -c "import sqlite3; ..."` to assert schema and data
- **JSON validation**: Use Python — `python -c "import json,sys; json.load(sys.stdin)"` to validate export output

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — parallel):
├── Task 1: Project scaffolding + venv + dependency install [quick]
└── Task 2: Data model (Device dataclass) + SQLite schema + CRUD [quick]

Wave 2 (Core engine — sequential pipeline, parallel with DB):
├── Task 3: CaptureProvider interface + pyshark wrapper [deep]
├── Task 4: Device discovery — packet parsing (depends on Task 3) [deep]
└── Task 5: Database CRUD implementation — parallel (depends only on Task 2) [quick]

Wave 3 (Higher-level logic — parallel):
├── Task 6: Device fingerprinting + MAC OUI lookup [deep]
├── Task 7: CLI interface (click) — scan/list/export/interfaces [unspecified-high]
└── Task 8: JSON export + rich table output [quick]

Wave 4 (Integration + polish):
├── Task 9: Integration tests + offline pcap fixtures [deep]
└── Task 10: README, .env.example, .gitignore, documentation [writing]

Wave FINAL (Verification — parallel):
├── F1: Plan compliance audit (oracle)
├── F2: Code quality review (unspecified-high)
├── F3: Real manual QA (unspecified-high)
└── F4: Scope fidelity check (deep)
```

### Dependency Matrix
- **1**: - → 3, 4, 7 (provides venv + deps)
- **2**: - → 5, 7, 8 (provides data model + schema)
- **3**: 1 → 4, 7 (provides CaptureProvider)
- **4**: 1, 3 → 6, 7, 9 (provides discovery engine)
- **5**: 2 → 7, 8 (provides DB operations)
- **6**: 2, 4 → 7, 9 (provides fingerprinting)
- **7**: 1, 3, 4, 5, 6 → 9, 10 (provides CLI interface)
- **8**: 2, 5 → 10 (provides export)
- **9**: 4, 6, 7 → F1-F4 (provides integration tests)
- **10**: 7, 8 → F1-F4 (provides docs)
- **F1-F4**: 9, 10, ALL (final verification)

### Agent Dispatch Summary
- **Wave 1**: 2 agents — T1 → `quick`, T2 → `quick`
- **Wave 2**: 3 agents — T3 → `deep`, T4 → `deep`, T5 → `quick`
- **Wave 3**: 3 agents — T6 → `deep`, T7 → `unspecified-high`, T8 → `quick`
- **Wave 4**: 2 agents — T9 → `deep`, T10 → `writing`
- **Wave FINAL**: 4 agents — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

> **TDD note**: Every Task marked [TDD] follows: write failing test first → implement minimally → refactor.
> **QA note**: Every task includes Agent-Executed QA Scenarios. The executing agent MUST run these after implementation.
> **Evidence**: All QA evidence saved to `.omo/evidence/task-{N}-{scenario}.{ext}`.

---

- [ ] 1. **Project Scaffolding + Virtual Environment**

  **What to do**:
  - Create directory structure: `src/nvs/`, `tests/`, `tests/fixtures/pcap/`, `.omo/evidence/`
  - Create `src/nvs/__init__.py` and `src/nvs/__main__.py` (minimal entry point that calls `cli.main()`)
  - Create `requirements.txt` with pinned deps: `pyshark==0.6`, `rich==15.0.0`, `click==8.4.1`, `python-dotenv==1.2.2`
  - Create `.env.example` with placeholder: `NVD_API_KEY=your-key-here` (for Phase 2)
  - Create `.gitignore` (`.venv/`, `__pycache__/`, `*.db`, `.env`, `.omo/`)
  - Create Python virtual environment `.venv/` and install dependencies
  - Verify `pyshark` imports cleanly in the venv (Python 3.13 compatibility test)
  - Create `pyproject.toml` with basic metadata (name="nvs", version="0.1.0", python=">=3.10")

  **Must NOT do**:
  - Do NOT add any application logic — just scaffolding
  - Do NOT create empty test files yet
  - Do NOT add non-essential deps (no flask, no sqlalchemy, no requests)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: None needed
  - **Reason**: Pure scaffolding — file creation, pip install, gitignore

  **Parallelization**:
  - **Can Run In Parallel**: YES (Wave 1, with Task 2)
  - **Blocks**: Tasks 3, 4, 7
  - **Blocked By**: None (start immediately)

  **References**:
  - N/A — this is a greenfield project

  **Acceptance Criteria**:

  **QA Scenarios**:
  ```
  Scenario: Virtual environment created and pyshark imports
    Tool: Bash
    Preconditions: None (fresh directory)
    Steps:
      1. Run: `& ".venv\Scripts\python.exe" -c "import pyshark; print(pyshark.__version__)"` from NVS directory
    Expected Result: Exit code 0, prints pyshark version (e.g., "0.6")
    Evidence: .omo/evidence/task-1-venv-pyshark.txt

  Scenario: Requirements installed and CLI entry point exists
    Tool: Bash
    Preconditions: Virtual environment created
    Steps:
      1. Run: `& ".venv\Scripts\python.exe" -c "import rich, click, dotenv; print('all deps ok')"` from NVS directory
      2. Verify src/nvs/__main__.py exists: `Test-Path src/nvs/__main__.py`
    Expected Result: Exit code 0, prints "all deps ok", __main__.py exists
    Evidence: .omo/evidence/task-1-deps.txt

  Scenario: .env.example and .gitignore exist
    Tool: Bash
    Preconditions: None
    Steps:
      1. Run: `Test-Path .env.example`
      2. Run: `Test-Path .gitignore`
    Expected Result: Both files exist
    Evidence: .omo/evidence/task-1-files.txt
  ```

  **Commit**: YES
  - Message: `build(nvs): scaffold project structure with venv, deps, gitignore`
  - Files: `src/nvs/`, `requirements.txt`, `.env.example`, `.gitignore`, `pyproject.toml`, `.venv/`

---

- [ ] 2. **Data Model + SQLite Schema** [TDD]

  **What to do**:
  - Create `src/nvs/models.py` with a `Device` dataclass containing:
    - `mac: str` (primary key, normalized to uppercase with colons)
    - `ip: str` (last known IP)
    - `hostname: str | None`
    - `manufacturer: str | None` (from MAC OUI lookup)
    - `os: str | None` (fingerprinted OS)
    - `device_type: str | None` (router, printer, phone, etc.)
    - `first_seen: str` (ISO 8601 UTC)
    - `last_seen: str` (ISO 8601 UTC)
    - `discovery_method: str` (mDNS, SSDP, ARP, DHCP)
  - Create `src/nvs/database.py` with SQLite CRUD:
    - `init_db(db_path: str) → sqlite3.Connection` — creates DB + table, enables WAL mode
    - `upsert_device(conn, device: Device) → None` — INSERT OR REPLACE on MAC
    - `get_all_devices(conn) → list[Device]` — returns all known devices
    - `get_device_by_mac(conn, mac: str) → Device | None`
    - `get_device_count(conn) → int`
  - Write tests FIRST (TDD):
    - `tests/test_database.py`: 8-10 tests covering init_db, upsert, dedup, get_all, get_by_mac, count, WAL mode, integrity

  **Must NOT do**:
  - Do NOT add indexes beyond PRIMARY KEY (V1 has small data volume)
  - Do NOT add migration logic (V1 uses single table, recreate if schema changes)
  - Do NOT add `vulnerabilities` table or any Phase 2 columns

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: None needed
  - **Reason**: Well-defined data model + CRUD operations — standard Python, no complex logic

  **Parallelization**:
  - **Can Run In Parallel**: YES (Wave 1, with Task 1)
  - **Blocks**: Tasks 5, 7, 8
  - **Blocked By**: None (start immediately after or alongside Task 1)

  **References**:
  - **External**: https://docs.python.org/3/library/sqlite3.html — stdlib sqlite3 module reference
  - **Pattern**: ISO 8601 UTC timestamps, WAL mode for concurrent reads, parameterized queries

  **Acceptance Criteria**:

  **QA Scenarios**:
  ```
  Scenario: Database created with correct schema
    Tool: Bash
    Preconditions: models.py and database.py exist
    Steps:
      1. Run: `& ".venv\Scripts\python.exe" -c "import sqlite3; c=sqlite3.connect(':memory:'); c.executescript(open('src/nvs/database.py').read().split('def ')[0]); print('schema ok')"`
      2. Or run: `cd tests && & "..\.venv\Scripts\python.exe" -m pytest test_database.py -v --tb=short`
    Expected Result: All database tests pass (exit 0), schema created correctly
    Evidence: .omo/evidence/task-2-db-tests.txt

  Scenario: Upsert deduplicates on same MAC
    Tool: Bash
    Preconditions: database.py and models.py importable
    Steps:
      1. Create a temporary test script that inserts device "AA:BB:CC:DD:EE:FF" twice with different IPs
      2. Assert only 1 row exists, and last_seen is the later timestamp
    Expected Result: Dedup works — 1 device with updated last_seen
    Evidence: .omo/evidence/task-2-dedup.txt

  Scenario: WAL mode is enabled
    Tool: Bash
    Preconditions: database.py creates a DB file
    Steps:
      1. Run inline Python to init DB and check journal_mode pragma
    Expected Result: journal_mode = "wal"
    Evidence: .omo/evidence/task-2-wal.txt
  ```

  **Commit**: YES (separate — scope differs from Task 1)
  - Message: `feat(nvs): add Device model and SQLite CRUD operations`
  - Files: `src/nvs/models.py`, `src/nvs/database.py`, `tests/test_database.py`
  - Pre-commit: `pytest tests/test_database.py -v`

---

- [ ] 3. **CaptureProvider Interface + pyshark Wrapper** [TDD]

  **What to do**:
  - Create `src/nvs/capture.py` with:
    - `CaptureProvider` ABC/Protocol with methods:
      - `get_interfaces() → list[InterfaceInfo]` (name, description, is_virtual, is_loopback)
      - `capture(interface: str, duration: int, bpf_filter: str) → AsyncGenerator[Packet, None]`
      - `check_dependencies() → list[str]` (returns missing dependency messages)
    - `PysharkCaptureProvider` concrete implementation:
      - Wraps `pyshark.LiveCapture` with BPF filter
      - Iterates packets for given duration
      - Catches common errors (interface not found, no Npcap, permission denied)
    - `get_best_interface() → str | None` — auto-detect non-virtual, non-loopback adapter
    - `DEFAULT_BPF_FILTER = "arp or port 5353 or port 1900 or (udp port 67 or udp port 68)"`
    - `check_admin() → bool` — checks if running as admin
    - `check_tshark() → bool` — checks if tshark is on PATH
  - Write tests FIRST (TDD):
    - `tests/test_capture.py`: 8-10 tests with mocked pyshark — test interface listing, capture lifecycle, BPF filter, dependency checks, admin check, error cases (no Npcap, no tshark, interface not found)

  **Must NOT do**:
  - Do NOT implement actual packet parsing here — just raw packet capture
  - Do NOT add async iteration support beyond what pyshark requires
  - Do NOT add continuous/wait mode (V1 is duration-based only)

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: None needed
  - **Reason**: Requires understanding of pyshark API, Windows packet capture quirks, BPF filtering, and careful error handling for missing dependencies. Also needs clean interface design for testability.

  **Parallelization**:
  - **Can Run In Parallel**: NO (sequential — depends on Task 1)
  - **Blocks**: Task 4, 7
  - **Blocked By**: Task 1

  **References**:
  - **External**: https://github.com/KimiNewt/pyshark — pyshark API reference (LiveCapture, FileCapture, BPF filter parameter)
  - **External**: https://biot.com/capstats/bpf.html — BPF filter syntax reference
  - **External**: https://npcap.com/vs-winpcap — Npcap vs WinPcap, install instructions

  **Acceptance Criteria**:

  **QA Scenarios**:
  ```
  Scenario: CaptureProvider interface exists and mock tests pass
    Tool: Bash
    Preconditions: .venv active, capture.py exists
    Steps:
      1. Run: `cd tests && & "..\.venv\Scripts\python.exe" -m pytest test_capture.py -v --tb=short`
    Expected Result: All tests pass (exit 0)
    Evidence: .omo/evidence/task-3-capture-tests.txt

  Scenario: Dependency checks work without Npcap
    Tool: Bash
    Preconditions: Npcap NOT installed (true on this system)
    Steps:
      1. Run: `& ".venv\Scripts\python.exe" -c "from nvs.capture import PysharkCaptureProvider; p=PysharkCaptureProvider(); print(p.check_dependencies())"`
    Expected Result: Reports missing dependencies (Npcap/tshark not found), does NOT crash
    Evidence: .omo/evidence/task-3-deps.txt

  Scenario: get_best_interface returns None or a valid interface name
    Tool: Bash
    Preconditions: pyshark installed
    Steps:
      1. Run: `& ".venv\Scripts\python.exe" -c "from nvs.capture import get_best_interface; print(get_best_interface())"`
    Expected Result: No crash — returns None (if no suitable) or a string interface name
    Evidence: .omo/evidence/task-3-interface.txt
  ```

  **Commit**: YES
  - Message: `feat(nvs): add CaptureProvider interface and pyshark wrapper`
  - Files: `src/nvs/capture.py`, `tests/test_capture.py`
  - Pre-commit: `pytest tests/test_capture.py -v`

---

- [ ] 4. **Device Discovery — ARP Cache + Packet Parsing** [TDD]

  **What to do**:
  - Create `src/nvs/arp_cache.py` for zero-dependency Windows ARP cache reading:
    - `read_arp_cache() → list[ArpEntry]` — runs `Get-NetNeighbor` (PowerShell) or `arp.exe -a` (fallback), parses IP + MAC + state
    - `ArpEntry` namedtuple: `ip: str`, `mac: str`, `state: str` (Reachable, Stale, etc.)
    - Graceful handling: PowerShell not available, no entries, parse errors
    - Cross-reference MAC OUIs (reuse fingerprint module) to add manufacturer info
    - `get_devices_from_arp() → list[Device]` — wraps read_arp_cache, converts to Device objects, sets discovery_method="ARP_cache"
  - Create `src/nvs/discover.py` with packet parsing logic:
    - `PacketParser` class that takes raw pyshark packets and extracts device info
    - `parse_mdns(packet) → Device | None` — extract from mDNS (port 5353): hostname.local, IP, device type (from service type like _airplay, _googlecast, etc.)
    - `parse_ssdp(packet) → Device | None` — extract from SSDP (port 1900): manufacturer (SERVER header), device type (USN/ST fields), IP
    - `parse_upnp(packet) → Device | None` — extract from UPnP broadcasts: manufacturer, device type, friendly name
    - `parse_arp(packet) → Device | None` — extract MAC + IP from ARP requests/replies
    - `parse_dhcp(packet) → Device | None` — extract hostname (Option 12), vendor class (Option 60), MAC, IP from DHCP
    - `parse_packet(packet) → Device | None` — dispatch to above parsers based on packet type
    - `Discoverer` class:
      - Takes `CaptureProvider` (enables mocking)
      - `discover(interface: str, duration: int, use_arp_cache: bool = True) → list[Device]` — ALWAYS reads ARP cache first (zero-dependency), THEN captures for duration if Npcap available, merges and deduplicates by MAC
      - Supports `arp_only=True` mode — skip packet capture entirely, just return ARP cache results
      - Graceful handling of malformed packets (log warning, skip, continue)
  - Write tests FIRST (TDD):
    - `tests/test_arp_cache.py`: 5-7 tests — test ARP cache parsing from mock output, test empty cache, test PowerShell vs arp.exe fallback, test MAC normalization, test error handling
    - `tests/test_discover.py`: 10-12 tests — test each protocol parser individually (mocked packets), test Discoverer with mocked CaptureProvider + ARP cache, test merge/dedup from both sources, test malformed packets, test no-traffic scenario, test partial packet (missing MAC layer)

  **Must NOT do**:
  - Do NOT implement any protocol parsing beyond the 5 listed (no HTTP header analysis, no TLS fingerprinting)
  - Do NOT add any outbound network calls for discovery
  - Do NOT implement passive OS fingerprinting via TTL — that goes in Task 6
  - Do NOT cache ARP results — read fresh every scan (ARP cache is volatile and cheap to query)

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: None needed
  - **Reason**: Packet dissection requires understanding pyshark's packet layer structure, protocol field access patterns, and careful null-handling for partial/malformed packets. Each protocol parser is a mini-domain.

  **Parallelization**:
  - **Can Run In Parallel**: NO (sequential — depends on Task 3)
  - **Blocks**: Tasks 6, 7, 9
  - **Blocked By**: Tasks 1, 3

  **References**:
  - **External**: https://github.com/KimiNewt/pyshark/blob/master/docs/working_with_packets.md — pyshark packet field access patterns
  - **External**: https://datatracker.ietf.org/doc/html/rfc6762 — mDNS (RFC 6762) protocol reference
  - **External**: https://datatracker.ietf.org/doc/html/rfc2131 — DHCP (RFC 2131) Option 12 (hostname) and Option 60 (vendor)
  - **Pattern**: `pkt.dhcp.option.hostname` for DHCP hostname extraction, `pkt.dns.resp.name` for mDNS hostname

  **Acceptance Criteria**:

  **QA Scenarios**:
  ```
  Scenario: All discovery tests pass
    Tool: Bash
    Preconditions: discover.py and its tests exist
    Steps:
      1. Run: `cd tests && & "..\.venv\Scripts\python.exe" -m pytest test_discover.py -v --tb=short`
    Expected Result: All tests pass (exit 0)
    Evidence: .omo/evidence/task-4-discover-tests.txt

  Scenario: Discoverer produces device list with mocked CaptureProvider
    Tool: Bash
    Preconditions: discover.py, capture.py, models.py importable
    Steps:
      1. Run inline Python: mock CaptureProvider returns 2 packets (mDNS + ARP), call Discoverer.discover()
      2. Assert returned list has 2 Device objects with correct MAC, IP, hostname fields
    Expected Result: 2 devices found, fields populated from mock packets
    Evidence: .omo/evidence/task-4-mock-discover.txt

  Scenario: Empty capture produces empty list (no crash)
    Tool: Bash
    Preconditions: As above
    Steps:
      1. Run inline Python: mock CaptureProvider returns 0 packets, call Discoverer.discover()
      2. Assert returned list is empty
    Expected Result: Empty list, no crash, no exception
    Evidence: .omo/evidence/task-4-empty.txt
  ```

  **Commit**: YES
  - Message: `feat(nvs): add device discovery with mDNS/SSDP/UPnP/ARP/DHCP parsing`
  - Files: `src/nvs/discover.py`, `tests/test_discover.py`
  - Pre-commit: `pytest tests/test_discover.py -v`

---

- [ ] 5. **Database CRUD Operations (Expanded)** [TDD]

  **What to do**:
  - Expand `src/nvs/database.py` with additional operations beyond Task 2:
    - `delete_device(conn, mac: str) → bool` — remove a device
    - `get_devices_by_type(conn, device_type: str) → list[Device]`
    - `get_statistics(conn) → dict` — return {total_devices, by_type, by_manufacturer}
    - `export_to_json(conn, filepath: str) → None` — write full device list as JSON array
    - `import_from_json(conn, filepath: str) → int` — import devices from JSON, returns count
    - `close(conn)` — close connection cleanly
  - Write tests FIRST (TDD):
    - `tests/test_database.py`: Expand with 5-6 additional tests — delete, get_by_type, statistics, export/import round-trip, close behavior

  **Must NOT do**:
  - Do NOT add any indexing beyond PK (YAGNI for V1 scale)
  - Do NOT add migration or versioning (V1 is single-schema)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: None needed
  - **Reason**: Standard SQLite CRUD — straightforward after schema is defined

  **Parallelization**:
  - **Can Run In Parallel**: YES (Wave 2, with Tasks 3 and 4)
  - **Blocks**: Tasks 7, 8
  - **Blocked By**: Task 2

  **References**:
  - **External**: https://docs.python.org/3/library/sqlite3.html — sqlite3 module, `connection.executemany()`, `connection.row_factory`

  **Acceptance Criteria**:

  **QA Scenarios**:
  ```
  Scenario: All database tests pass (expanded)
    Tool: Bash
    Preconditions: database.py, test_database.py
    Steps:
      1. Run: `cd tests && & "..\.venv\Scripts\python.exe" -m pytest test_database.py -v --tb=short`
    Expected Result: All tests pass (exit 0)
    Evidence: .omo/evidence/task-5-db-tests.txt

  Scenario: Export to JSON produces valid array of device objects
    Tool: Bash
    Preconditions: database.py with test DB containing 2 devices
    Steps:
      1. Create test DB with 2 devices, export to temp.json
      2. Validate: `& "..\.venv\Scripts\python.exe" -c "import json; data=json.load(open('temp.json')); assert len(data)==2; assert all(d.get('mac') for d in data); print('valid')"`
    Expected Result: JSON valid, 2 devices with mac fields
    Evidence: .omo/evidence/task-5-export.txt

  Scenario: Statistics returns correct counts
    Tool: Bash
    Preconditions: database.py with test DB
    Steps:
      1. Insert 3 devices of 2 types into test DB
      2. Call get_statistics(), assert total=3, by_type has correct counts
    Expected Result: Statistics accurate
    Evidence: .omo/evidence/task-5-stats.txt
  ```

  **Commit**: YES (groups with Task 4)
  - Message: `feat(nvs): expand DB CRUD with export/import/statistics`
  - Files: `src/nvs/database.py`, `tests/test_database.py`
  - Pre-commit: `pytest tests/test_database.py -v`

---

- [ ] 6. **Device Fingerprinting + MAC OUI Lookup** [TDD]

  **What to do**:
  - Create `src/nvs/fingerprint.py`:
    - `MAC_OUI_DB_PATH` — path to bundled `nvs_oui.csv`
    - `load_oui_db(path: str) → dict[str, str]` — load MAC prefix → manufacturer mapping
    - `lookup_manufacturer(mac: str, oui_db: dict) → str | None` — match first 3/6/8 hex bytes against OUI prefixes
    - **EXPERIMENTAL** `guess_device_type(device: Device) → str | None` — heuristic classification (see limitations below):
      - Router: known MAC OUIs (Cisco, Netgear, TP-Link, Asus, etc.) OR hostname contains "router", "gateway"
      - Printer: known printer OUIs (HP, Brother, Canon, Epson) OR mDNS service _printer, _ipp
      - Phone: mDNS/SSDP service types, hostname patterns (iPhone, Android)
      - Smart TV/Speaker: _airplay, _googlecast, _spotify-connect
      - Gaming console: _xbox, _playstation
      - Unknown: default
    - **EXPERIMENTAL** `guess_os(device: Device) → str | None` — basic OS hints from:
      - DHCP vendor class (Option 60): "MSFT 5.0" = Windows, "dhcpcd-*" = Linux, "Android*" = Android
      - mDNS hostname patterns
    - Both heuristic functions MUST include documentation noting: "This is a best-effort heuristic classification. Accuracy depends on device behavior and may be incorrect. Do not rely on this for security-critical decisions."
  - Create `nvs_oui.csv` — bundled OUI database:
    - Download from https://standards-oui.ieee.org/oui/oui.csv (public, ~42K entries, no API key)
    - OR use a build script: `python scripts/download_oui.py` that fetches and converts to `prefix,manufacturer` format
    - Include ALL entries (IEEE MA-L + MA-M + MA-S). No curated subset — the full registry costs nothing and prevents "Unknown manufacturer" on real hardware
    - Format: `prefix,manufacturer` (e.g., `00:1A:79, Cisco Systems`)
  - Write tests FIRST (TDD):
    - `tests/test_fingerprint.py`: 8-10 tests — test OUI loading, manufacturer lookup (match + no-match + partial), device type classification for each category, OS guessing, edge cases (unknown MAC, empty hostname, malformed MAC)

  **Must NOT do**:
  - Do NOT add external API calls for manufacturer lookup (offline only)
  - Do NOT add ML-based fingerprinting
  - Do NOT add port-based OS detection (requires active scanning)

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: None needed
  - **Reason**: Combines data processing (OUI CSV, ~42K entries), heuristic logic (device type from service types), and careful edge case handling (missing MAC, unknown prefixes, malformed input)

  **Parallelization**:
  - **Can Run In Parallel**: YES (Wave 3, with Tasks 7 and 8)
  - **Blocks**: Task 7, 9
  - **Blocked By**: Tasks 2, 4

  **References**:
  - **External**: https://standards-oui.ieee.org/oui/oui.csv — IEEE OUI database (public, no API key)
  - **External**: https://www.iana.org/assignments/dhcpv6-parameters/dhcpv6-parameters.xhtml#vendor-class — DHCP vendor class identifiers
  - **Pattern**: MAC OUI matching — check first 3 bytes (24-bit) first, then 4 bytes (28-bit), then 6 bytes (36-bit) for full match

  **Acceptance Criteria**:

  **QA Scenarios**:
  ```
  Scenario: Fingerprinting tests pass
    Tool: Bash
    Preconditions: fingerprint.py, nvs_oui.csv, test_fingerprint.py
    Steps:
      1. Run: `cd tests && & "..\.venv\Scripts\python.exe" -m pytest test_fingerprint.py -v --tb=short`
    Expected Result: All tests pass (exit 0)
    Evidence: .omo/evidence/task-6-fingerprint-tests.txt

  Scenario: OUI database loads and matches known manufacturer
    Tool: Bash
    Preconditions: nvs_oui.csv exists
    Steps:
      1. Run: `& ".venv\Scripts\python.exe" -c "from nvs.fingerprint import load_oui_db, lookup_manufacturer; db=load_oui_db('nvs_oui.csv'); print(lookup_manufacturer('00:1A:79:AB:CD:EF', db))"`
    Expected Result: Returns manufacturer string (e.g., "Cisco Systems, Inc") — not None
    Evidence: .omo/evidence/task-6-oui-match.txt

  Scenario: Unknown MAC returns None (no crash)
    Tool: Bash
    Preconditions: As above
    Steps:
      1. Run: `& ".venv\Scripts\python.exe" -c "from nvs.fingerprint import load_oui_db, lookup_manufacturer; db=load_oui_db('nvs_oui.csv'); print(lookup_manufacturer('FF:FF:FF:AB:CD:EF', db))"`
    Expected Result: Returns None, no exception
    Evidence: .omo/evidence/task-6-oui-unknown.txt

  Scenario: Device type classification for known service types
    Tool: Bash
    Preconditions: fingerprint.py importable
    Steps:
      1. Run inline Python that creates a Device with mDNS service "_googlecast._tcp.local" and calls guess_device_type()
    Expected Result: Returns "Smart TV/Speaker" or appropriate type
    Evidence: .omo/evidence/task-6-device-type.txt
  ```

  **Commit**: YES
  - Message: `feat(nvs): add device fingerprinting with MAC OUI lookup and type classification`
  - Files: `src/nvs/fingerprint.py`, `nvs_oui.csv`, `tests/test_fingerprint.py`
  - Pre-commit: `pytest tests/test_fingerprint.py -v`

---

- [ ] 7. **CLI Interface (click)** [TDD]

  **What to do**:
  - Create `src/nvs/cli.py` with click-based CLI:
    - `@click.group()` — `nvs` top-level group
    - `scan` subcommand:
      - `--interface`, `-i` (str, default=None for auto-detect)
      - `--duration`, `-d` (int, default=60)
      - `--format`, `-f` (choice: table|json, default=table)
      - `--db-path` (str, default="./nvs_devices.db")
      - `--verbose`, `-v` (flag, default=False)
      - `--arp-only` (flag, default=False) — skip packet capture entirely, just read ARP cache
      - Logic:
        1. ALWAYS read ARP cache first (`arp_cache.get_devices_from_arp()`) — zero-dependency, works without Npcap/admin
        2. If not `--arp-only`: check Npcap/tshark/admin availability via pre-flight validation
        3. If deps available: auto-detect interface → create CaptureProvider → run Discoverer for packet capture
        4. Merge ARP cache results + capture results (dedup by MAC)
        5. Run fingerprinting (MAC OUI lookup + heuristic type/OS) on merged set
        6. Store in DB via upsert
        7. Output results via exporter (table or JSON)
    - `list` subcommand:
      - `--db-path` (str, default="./nvs_devices.db")
      - `--format` (choice: table|json, default=table)
      - `--type` (str, optional — filter by device type)
      - Logic: read DB, output formatted device list
    - `export` subcommand:
      - `--db-path` (str, default="./nvs_devices.db")
      - `--output`, `-o` (str, default=None for stdout)
      - Logic: read DB, output JSON array
    - `interfaces` subcommand:
      - Logic: list available interfaces via CaptureProvider, mark virtual/loopback, recommend best
    - Wire `__main__.py` to call `cli.main()`
    - Pre-flight validation (on every `scan` command):
      - Phase 1 (always runs): read ARP cache. Warn if empty: "⚠ ARP cache is empty. No devices found. Ensure you are connected to a network."
      - Phase 2 (conditional on packet capture requested): check admin + tshark + Npcap service. If missing:
        - "ℹ Packet capture unavailable: [specific reason]. Falling back to ARP cache only."
        - "  Tip: Run with --arp-only to suppress this message, or install Npcap for full capture."
      - Phase 3 (packet capture fails at runtime): "⚠ Packet capture returned zero packets. Devices shown are from ARP cache only."
      - Print clear, actionable messages for each failure mode, then PROCEED with ARP cache data (tool is still useful)
  - Write tests FIRST (TDD):
    - `tests/test_cli.py`: 8-10 tests — test help output, test scan with mocked dependencies, test list with test DB, test export output, test interfaces listing, test argument parsing (--help, --duration validation, --interface overrides)

  **Must NOT do**:
  - Do NOT add any web serving capability
  - Do NOT add Windows service registration flags
  - Do NOT add --continuous or --watch flags
  - Do NOT add config file loading (--config flag)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: None needed
  - **Reason**: Integration-heavy task wiring together capture, discovery, fingerprinting, and database layers. Requires careful error handling and CLI design.

  **Parallelization**:
  - **Can Run In Parallel**: YES (Wave 3, with Tasks 6 and 8)
  - **Blocks**: Tasks 9, 10
  - **Blocked By**: Tasks 1, 3, 4, 5, 6

  **References**:
  - **External**: https://click.palletsprojects.com/en/8.1.x/ — click CLI framework reference
  - **Pattern**: `@click.option`, `@click.argument`, `@click.pass_context`, click group + subcommand pattern
  - **Reference**: `tests/test_cli.py` — use CliRunner from `click.testing` for CLI test isolation

  **Acceptance Criteria**:

  **QA Scenarios**:
  ```
  Scenario: --help shows all 4 subcommands
    Tool: Bash
    Preconditions: cli.py, .venv active
    Steps:
      1. Run: `& ".venv\Scripts\python.exe" -m nvs --help`
    Expected Result: Exit 0, stdout contains "scan", "list", "export", "interfaces"
    Evidence: .omo/evidence/task-7-help.txt

  Scenario: scan without admin still produces output (ARP cache fallback)
    Tool: Bash
    Preconditions: Not running as admin, cli.py importable
    Steps:
      1. Run: `& ".venv\Scripts\python.exe" -m nvs scan --arp-only`
    Expected Result: Exit 0, stdout contains device table from ARP cache (or "No devices found in ARP cache" if empty). Does NOT crash.
    Evidence: .omo/evidence/task-7-arp-fallback.txt

  Scenario: --arp-only produces device list without Npcap
    Tool: Bash
    Preconditions: cli.py, arp_cache.py importable
    Steps:
      1. Run: `& ".venv\Scripts\python.exe" -m nvs scan --arp-only`
    Expected Result: Exit 0, stdout lists devices found in Windows ARP cache (IP + MAC)
    Evidence: .omo/evidence/task-7-arp-only.txt

  Scenario: list on empty DB shows "No devices discovered yet"
    Tool: Bash
    Preconditions: Empty test DB, cli.py and database.py
    Steps:
      1. Run: `& ".venv\Scripts\python.exe" -m nvs list --db-path test_empty.db`
    Expected Result: Exit 0, stdout contains "No devices discovered yet" or similar empty-state message
    Evidence: .omo/evidence/task-7-list-empty.txt

  Scenario: interfaces subcommand runs without error
    Tool: Bash
    Preconditions: .venv active
    Steps:
      1. Run: `& ".venv\Scripts\python.exe" -m nvs interfaces`
    Expected Result: Exit 0, stdout lists interface names with descriptions, or shows "No suitable interface found" message
    Evidence: .omo/evidence/task-7-interfaces.txt

  Scenario: --duration 0 is rejected
    Tool: Bash
    Preconditions: cli.py importable
    Steps:
      1. Run: `& ".venv\Scripts\python.exe" -m nvs scan --duration 0`
    Expected Result: Non-zero exit, error message about invalid duration
    Evidence: .omo/evidence/task-7-duration-0.txt
  ```

  **Commit**: YES
  - Message: `feat(nvs): add CLI interface with scan/list/export/interfaces commands`
  - Files: `src/nvs/cli.py`, `src/nvs/__main__.py`, `tests/test_cli.py`
  - Pre-commit: `pytest tests/test_cli.py -v`

---

- [ ] 8. **JSON Export + rich Table Output** [TDD]

  **What to do**:
  - Create `src/nvs/exporter.py`:
    - `export_json(devices: list[Device], filepath: str | None = None) → str` — serialize to JSON array, write to file if path given, return JSON string
    - `export_table(devices: list[Device]) → str` — render rich Table with columns: MAC, IP, Hostname, Manufacturer, Type, OS, First Seen, Last Seen
    - `export_summary(devices: list[Device]) → str` — render a summary panel (total devices, by type, by manufacturer)
    - `handle_empty(devices: list[Device]) → str` — return appropriate message ("No devices discovered yet. Run 'nvs scan' first.")
    - JSON schema per device object:
      ```json
      {
        "mac": "AA:BB:CC:DD:EE:FF",
        "ip": "192.168.1.100",
        "hostname": "iPhone-de-casa",
        "manufacturer": "Apple, Inc.",
        "os": "iOS",
        "device_type": "Phone",
        "first_seen": "2026-06-23T10:30:00Z",
        "last_seen": "2026-06-23T10:31:00Z",
        "discovery_method": "mDNS"
      }
      ```
  - Wire export into CLI (`nvs export` and `nvs scan --format json`)
  - Write tests FIRST (TDD):
    - `tests/test_exporter.py`: 6-8 tests — JSON output validation, table output format, empty list handling, summary statistics, export with file write, verify round-trip (export→import→compare)

  **Must NOT do**:
  - Do NOT add CSV export (Phase 2)
  - Do NOT add HTML export (that's the dashboard)
  - Do NOT add XML or any other format

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: None needed
  - **Reason**: Well-defined output formatting — JSON serialization + rich Table rendering. Straightforward.

  **Parallelization**:
  - **Can Run In Parallel**: YES (Wave 3, with Tasks 6 and 7)
  - **Blocks**: Task 10
  - **Blocked By**: Tasks 2, 5

  **References**:
  - **External**: https://rich.readthedocs.io/en/stable/table.html — rich Table API
  - **External**: https://docs.python.org/3/library/json.html — stdlib JSON module

  **Acceptance Criteria**:

  **QA Scenarios**:
  ```
  Scenario: Exporter tests pass
    Tool: Bash
    Preconditions: exporter.py, test_exporter.py
    Steps:
      1. Run: `cd tests && & "..\.venv\Scripts\python.exe" -m pytest test_exporter.py -v --tb=short`
    Expected Result: All tests pass (exit 0)
    Evidence: .omo/evidence/task-8-exporter-tests.txt

  Scenario: JSON output validates against schema
    Tool: Bash
    Preconditions: exporter.py with test Devices
    Steps:
      1. Run inline Python that creates 2 Device objects, calls export_json()
      2. Parse output with json.loads()
      3. Assert each device has all required fields (mac, ip, hostname, manufacturer, os, device_type, first_seen, last_seen, discovery_method)
    Expected Result: Valid JSON, all required fields present, nulls for unknown fields
    Evidence: .omo/evidence/task-8-json-valid.txt

  Scenario: Empty device list returns helpful message, not empty output
    Tool: Bash
    Preconditions: exporter.py
    Steps:
      1. Run inline Python: call export_table([]) or handle_empty([])
    Expected Result: Returns message like "No devices discovered yet"
    Evidence: .omo/evidence/task-8-empty.txt
  ```

  **Commit**: YES (groups with Task 7)
  - Message: `feat(nvs): add JSON export and rich table output formatting`
  - Files: `src/nvs/exporter.py`, `tests/test_exporter.py`
  - Pre-commit: `pytest tests/test_exporter.py -v`

---

- [ ] 9. **Integration Tests + Offline pcap Fixtures** [TDD]

  **What to do**:
  - Create offline pcap test fixtures:
    - `tests/fixtures/pcap/mdns_only.pcap` — 1 mDNS packet (query for _services._dns-sd._udp.local)
    - `tests/fixtures/pcap/ssdp_only.pcap` — 1 SSDP NOTIFY packet
    - `tests/fixtures/pcap/arp_only.pcap` — 1 ARP request
    - `tests/fixtures/pcap/dhcp_only.pcap` — 1 DHCP OFFER with option 12 (hostname) + option 60 (vendor)
    - `tests/fixtures/pcap/mixed.pcap` — 5-6 packets with multiple protocols
    - Use tshark/pyshark to generate or capture these, OR create them using packet crafting tools
    - Alternatively: use pre-generated pcap files from public sources or create via `scapy.utils` if available
  - Create `tests/test_integration.py`:
    - `test_capture_from_pcap` — use pyshark.FileCapture on each pcap fixture, verify packets parse
    - `test_full_pipeline_mocked` — mock CaptureProvider to return synthetic packets, run full pipeline: capture → discover → fingerprint → store → export
    - `test_db_roundtrip` — scan to DB → list from DB → export → verify device count matches
    - `test_missing_deps_error_msg` — verify dependency check output text matches expected
    - `test_duplicate_scan` — run scan twice, verify dedup works (count stays same or grows correctly)
  - Write a `tests/conftest.py` with shared fixtures:
    - `test_db_path(tmp_path)` — temporary DB for test isolation
    - `mock_capture_provider()` — returns CaptureProvider that yields synthetic packets
    - `sample_devices()` — returns list of Device objects for testing
    - `oui_db()` — loads OUI DB once per session

  **Must NOT do**:
  - Do NOT add pcap files > 100KB each
  - Do NOT add integration tests that require live network capture (offline only)
  - Do NOT add performance/load tests (V1 is functional only)

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: None needed
  - **Reason**: Requires creating valid pcap files (packet crafting), designing integration test flow, and ensuring all modules wire together correctly under test conditions.

  **Parallelization**:
  - **Can Run In Parallel**: NO (sequential — depends on Tasks 4, 6, 7)
  - **Blocks**: None (but should pass before Final Verification)
  - **Blocked By**: Tasks 4, 6, 7

  **References**:
  - **External**: https://github.com/KimiNewt/pyshark/blob/master/docs/working_with_packets.md — pyshark FileCapture for offline pcap reading
  - **Pattern**: `pyshark.FileCapture('tests/fixtures/pcap/mdns_only.pcap')` for offline packet reading
  - **Tool**: `scapy.utils.rdpcap()` / `scapy.utils.wrpcap()` if scapy is available for pcap crafting

  **Acceptance Criteria**:

  **QA Scenarios**:
  ```
  Scenario: Integration tests pass
    Tool: Bash
    Preconditions: All modules implemented, pcap fixtures exist
    Steps:
      1. Run: `cd tests && & "..\.venv\Scripts\python.exe" -m pytest test_integration.py -v --tb=short`
    Expected Result: All integration tests pass (exit 0)
    Evidence: .omo/evidence/task-9-integration-tests.txt

  Scenario: Full pipeline end-to-end with mocked capture
    Tool: Bash
    Preconditions: test_integration.py
    Steps:
      1. Run specific test: `cd tests && & "..\.venv\Scripts\python.exe" -m pytest test_integration.py::test_full_pipeline_mocked -v --tb=short`
    Expected Result: Pipeline completes without error, devices stored and retrievable
    Evidence: .omo/evidence/task-9-pipeline.txt

  Scenario: All tests across all test files pass
    Tool: Bash
    Preconditions: All test files exist
    Steps:
      1. Run full test suite: `cd tests && & "..\.venv\Scripts\python.exe" -m pytest -v --tb=short`
    Expected Result: All tests pass (exit 0) — count should be 30+
    Evidence: .omo/evidence/task-9-all-tests.txt
  ```

  **Commit**: YES
  - Message: `test(nvs): add integration tests with offline pcap fixtures`
  - Files: `tests/test_integration.py`, `tests/conftest.py`, `tests/fixtures/pcap/*`
  - Pre-commit: `pytest tests/ -v`

---

- [ ] 10. **README + Documentation + Project Configuration**

  **What to do**:
  - Create `README.md` with:
    - **Overview**: what NVS is (passive, CLI-based network device inventory tool — NOT a vulnerability scanner in V1)
    - **Prerequisites**: Windows, Python 3.10+; Npcap (with Wireshark tools) optional for enhanced capture
    - **Quick Start** (works WITHOUT Npcap — ARP cache is zero-dependency):
      1. `python -m venv .venv && .venv\Scripts\activate`
      2. `pip install -r requirements.txt`
      3. `python -m nvs scan --arp-only` (discover devices from ARP cache, no admin needed)
      4. `python -m nvs list` (show results)
      5. `python -m nvs scan` (with Npcap: full capture + ARP cache merge)
      6. `python -m nvs export --output devices.json` (export)
    - **How ARP Cache Discovery Works**: Explains that `Get-NetNeighbor` / `arp.exe -a` gives you every device the local machine has recently communicated with — no packet capture required
    - **Npcap Installation Guide**: Step-by-step with screenshots-or-text (check "WinPcap API-compatible Mode" + install Wireshark). Note: Wi-Fi adapter capture may yield zero packets on some Windows configurations
    - **Usage**: Detailed command reference for scan (`--arp-only`, `--duration`, `--format`), list, export, interfaces
    - **Limitations** (critical for user trust!):
      - This is a device inventory tool, not a vulnerability scanner (CVE lookups, port scanning, service detection are Phase 2)
      - Passive packet capture only sees broadcast/multicast traffic on switched networks
      - ARP cache only shows devices the host has recently communicated with
      - Heuristic device type/OS classification is experimental and may be inaccurate
      - IPv4 only (V1)
    - **FAQ**: Troubleshooting (no devices found from ARP cache, Npcap not detected, admin rights, Wi-Fi capture shows zero packets)
    - **Architecture**: Brief overview of the module structure (ARP cache + packet capture → merge → fingerprint → store → output)
    - **Development**: How to run tests, project structure, OUI database update (`python scripts/download_oui.py`)
  - Update `pyproject.toml` with `[project.scripts]` entry: `nvs = "nvs.cli:main"`
  - Update `.env.example` with all env vars documented
  - Create `.gitignore` with comprehensive Python + Windows patterns

  **Must NOT do**:
  - Do NOT create mkdocs or sphinx documentation (too heavy for V1 CLI tool)
  - Do NOT add code comments beyond docstrings (code should be self-documenting)

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: None needed
  - **Reason**: Pure documentation — README, setup guide, usage reference

  **Parallelization**:
  - **Can Run In Parallel**: NO (sequential — depends on Tasks 7, 8)
  - **Blocks**: Final Verification
  - **Blocked By**: Tasks 7, 8

  **References**:
  - **Pattern**: PRD in project root — reference it for feature completeness
  - **Pattern**: vault's other project READMEs (novel-to-video, A.R.C.) for tone and structure

  **Acceptance Criteria**:

  **QA Scenarios**:
  ```
  Scenario: README exists and contains required sections
    Tool: Bash
    Preconditions: README.md exists
    Steps:
      1. Read README.md and check for sections: Overview, Prerequisites, Quick Start, Usage, Limitations, Development
    Expected Result: All sections present, Npcap install instructions included
    Evidence: .omo/evidence/task-10-readme-sections.txt

  Scenario: pip install works from pyproject.toml
    Tool: Bash
    Preconditions: pyproject.toml, .venv
    Steps:
      1. Run: `& ".venv\Scripts\python.exe" -m pip install -e .` from NVS directory
    Expected Result: Package installs without error
    Evidence: .omo/evidence/task-10-install.txt

  Scenario: CLI runs after pip install
    Tool: Bash
    Preconditions: package installed in editable mode
    Steps:
      1. Run: `python -m nvs --help` (using system Python's venv)
    Expected Result: Help text with all 4 subcommands
    Evidence: .omo/evidence/task-10-cli.txt
  ```

  **Commit**: YES
  - Message: `docs(nvs): add README, pyproject.toml scripts entry, and project config`
  - Files: `README.md`, `pyproject.toml`, `.gitignore`, `.env.example`
  - Pre-commit: `pytest tests/ -v`

---

## Final Verification Wave

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run tests, check CLI output). For each "Must NOT Have": search codebase for forbidden patterns (no NVD calls, no web server, no async, no ORM, no active scanning code). Check evidence files exist in `.omo/evidence/`. Compare deliverables against PRD.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `& ".venv\Scripts\python.exe" -m pytest tests/ -v` (all tests pass). Run `& ".venv\Scripts\python.exe" -c "import py_compile; py_compile.compile('src/nvs/cli.py')"` (validates syntax). Review all changed files for: `# type: ignore` without comment, broad `except:`, `print()` in library code (use logging), commented-out code, unused imports, functions over 50 lines. Check AI slop: over-abstraction, generic names (data/result/item/temp), excessive comments.
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high`
  Start from clean test DB. Execute every QA scenario from every task — follow exact steps, capture evidence. Test cross-task integration: scan→list→export round-trip. Test edge cases: `--db-path` with non-existent dir, `--duration 1` (minimum), `--format json` with pipe to Python validation, `--help` on every subcommand. Save to `.omo/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination: Task N touching Task M's files. Flag unaccounted changes. Specifically check: no web server code, no NVD API calls, no async/await, no ORM imports.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

| Batch | Message | Scope |
|-------|---------|-------|
| 1 | `build(nvs): scaffold project structure with venv, deps, gitignore` | Project setup |
| 2 | `feat(nvs): add Device model and SQLite CRUD operations` | Data layer |
| 3 | `feat(nvs): add CaptureProvider interface and pyshark wrapper` | Capture engine |
| 4 | `feat(nvs): add device discovery with mDNS/SSDP/UPnP/ARP/DHCP parsing` | Discovery |
| 4b | `feat(nvs): expand DB CRUD with export/import/statistics` | Data layer |
| 5 | `feat(nvs): add device fingerprinting with MAC OUI lookup and type classification` | Fingerprinting |
| 6 | `feat(nvs): add CLI interface with scan/list/export/interfaces commands` | CLI |
| 6b | `feat(nvs): add JSON export and rich table output formatting` | Output |
| 7 | `test(nvs): add integration tests with offline pcap fixtures` | Testing |
| 8 | `docs(nvs): add README, pyproject.toml scripts entry, and project config` | Documentation |

---

## Success Criteria

### Verification Commands
```bash
# Full test suite
cd tests && & "..\.venv\Scripts\python.exe" -m pytest -v --tb=short
# Expected: All 30+ tests pass

# CLI help
& ".venv\Scripts\python.exe" -m nvs --help
# Expected: Shows scan, list, export, interfaces

# Scan with ARP-only (works WITHOUT Npcap, without admin)
& ".venv\Scripts\python.exe" -m nvs scan --arp-only
# Expected: Shows devices from Windows ARP cache (or empty-state message)

# Full scan (requires admin + Npcap on actual hardware)
# & ".venv\Scripts\python.exe" -m nvs scan --duration 30

# List devices
& ".venv\Scripts\python.exe" -m nvs list
# Expected: Shows discovered devices or empty-state message

# Export to JSON
& ".venv\Scripts\python.exe" -m nvs export
# Expected: Valid JSON array

# List interfaces
& ".venv\Scripts\python.exe" -m nvs interfaces
# Expected: Shows available network interfaces
```

### Final Checklist
- [ ] All 30+ tests pass: `pytest tests/ -v`
- [ ] CLI help shows all 4 subcommands (plus `--arp-only` flag on scan)
- [ ] `nvs scan --arp-only` works without Npcap, without admin — returns ARP cache devices
- [ ] `nvs scan` completes without error (with admin + Npcap)
- [ ] `nvs list` shows devices
- [ ] `nvs export` produces valid JSON
- [ ] `nvs interfaces` lists available adapters
- [ ] Missing Npcap/tshark produces graceful fallback message ("using ARP cache only")
- [ ] Non-admin execution still works (ARP cache fallback, no crash)
- [ ] All "Must Have" items present (including ARP cache, full OUI, pre-flight validation)
- [ ] All "Must NOT Have" items absent (no NVD, no web, no async, no ORM, no active scanning, no vulnerability claims)
- [ ] Documentation covers: Quick Start, Npcap install, limitations, development
- [ ] Evidence files in `.omo/evidence/` for all task QA scenarios
