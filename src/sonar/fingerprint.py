import csv
import os
import logging
from sonar.models import Device

logger = logging.getLogger(__name__)

OUI_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "sonar_oui.csv")


oui_cache: dict[str, str] | None = None


def load_oui_db(path: str | None = None) -> dict[str, str]:
    global oui_cache
    if oui_cache is not None and path is None:
        return oui_cache

    db_path = path or OUI_DB_PATH
    result = {}
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(",", 1)
                if len(parts) == 2:
                    prefix = parts[0].strip().upper()
                    manufacturer = parts[1].strip()
                    result[prefix] = manufacturer
    except FileNotFoundError:
        logger.warning(f"OUI database not found at {db_path}")

    if path is None:
        oui_cache = result
    return result


def lookup_manufacturer(mac: str, oui_db: dict[str, str]) -> str | None:
    raw = mac.replace(":", "").replace("-", "").upper()
    if len(raw) < 6:
        return None

    prefix8 = ":".join(raw[i:i+2] for i in range(0, 6, 2))
    if prefix8 in oui_db:
        return oui_db[prefix8]

    prefix10 = ":".join(raw[i:i+2] for i in range(0, 8, 2))
    if prefix10 in oui_db:
        return oui_db[prefix10]

    prefix12 = ":".join(raw[i:i+2] for i in range(0, 12, 2))
    if prefix12 in oui_db:
        return oui_db[prefix12]

    return None


def guess_device_type(device: Device) -> str | None:
    """EXPERIMENTAL: Best-effort heuristic classification."""
    hostname = (device.hostname or "").lower()
    manufacturer = (device.manufacturer or "").lower()

    router_keywords = ["router", "gateway", "asus", "netgear", "tplink", "tp-link", "linksys", "dlink", "d-link"]
    if any(kw in hostname for kw in router_keywords):
        return "Router"
    router_manufacturers = ["cisco", "netgear", "tp-link", "tplink", "asus", "linksys", "d-link", "dlink", "ubiquiti"]
    if any(mf in manufacturer for mf in router_manufacturers):
        return "Router"

    printer_keywords = ["printer", "hp", "canon", "brother", "epson", "lexmark"]
    if any(kw in hostname for kw in printer_keywords):
        return "Printer"
    printer_manufacturers = ["hp", "hewlett", "canon", "brother", "epson", "lexmark", "xerox"]
    if any(mf in manufacturer for mf in printer_manufacturers):
        return "Printer"

    phone_keywords = ["iphone", "android", "samsung galaxy", "pixel", "oneplus", "phone"]
    if any(kw in hostname for kw in phone_keywords):
        return "Phone"

    tv_keywords = ["smarttv", "smart-tv", "roku", "chromecast", "fire-tv", "apple-tv"]
    if any(kw in hostname for kw in tv_keywords):
        return "Smart TV"

    speaker_keywords = ["echo", "google home", "sonos", "alexa", "speaker"]
    if any(kw in hostname for kw in speaker_keywords):
        return "Smart Speaker"

    gaming_keywords = ["xbox", "playstation", "ps5", "ps4", "switch", "gaming"]
    if any(kw in hostname for kw in gaming_keywords):
        return "Gaming Console"

    mac_keywords = ["macbook", "imac", "mac"]
    if any(kw in hostname for kw in mac_keywords):
        return "Computer"

    windows_keywords = ["desktop", "laptop", "pc", "workstation"]
    if any(kw in hostname for kw in windows_keywords):
        return "Computer"

    pi_keywords = ["raspberry", "rpi", "pi-"]
    if any(kw in hostname for kw in pi_keywords):
        return "Single Board Computer"

    return None


def guess_os(device: Device) -> str | None:
    """EXPERIMENTAL: Best-effort OS detection from hostname patterns."""
    hostname = (device.hostname or "").lower()

    windows_patterns = ["desktop", "laptop", "windows", "pc-", "workstation", "msft"]
    if any(p in hostname for p in windows_patterns):
        return "Windows"

    mac_patterns = ["macbook", "imac", "mac-", "iphone", "ipad", "apple"]
    if any(p in hostname for p in mac_patterns):
        return "macOS/iOS"

    linux_patterns = ["raspberry", "rpi", "ubuntu", "debian", "linux", "pi-", "openwrt"]
    if any(p in hostname for p in linux_patterns):
        return "Linux"

    android_patterns = ["android", "samsung", "pixel", "oneplus", "xiaomi"]
    if any(p in hostname for p in android_patterns):
        return "Android"

    return None
