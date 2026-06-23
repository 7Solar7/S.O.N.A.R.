from dataclasses import dataclass, field
from datetime import datetime, timezone


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Device:
    mac: str  # primary key, normalized uppercase with colons
    ip: str  # last known IP
    hostname: str | None = None
    manufacturer: str | None = None
    os: str | None = None
    device_type: str | None = None
    first_seen: str = field(default_factory=_utcnow_iso)
    last_seen: str = field(default_factory=_utcnow_iso)
    discovery_method: str = "unknown"

    def __post_init__(self):
        raw = self.mac.replace(":", "").replace("-", "").upper()
        self.mac = ":".join(raw[i : i + 2] for i in range(0, 12, 2))
