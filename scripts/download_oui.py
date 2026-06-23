import argparse
import csv
import io
import logging
import os
import sys
import urllib.request
import urllib.error

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("download_oui")

IEEE_URLS = {
    "MA-L": "https://standards-oui.ieee.org/oui/oui.csv",
    "MA-M": "https://standards-oui.ieee.org/oui28/mam.csv",
    "MA-S": "https://standards-oui.ieee.org/oui36/oui36.csv",
}


def normalize_prefix(raw: str, oui_type: str) -> str | None:
    raw = raw.strip().replace("-", "").replace(":", "").upper()
    if not raw or not all(c in "0123456789ABCDEF" for c in raw):
        return None
    if oui_type == "MA-L":
        if len(raw) != 6:
            return None
        return ":".join(raw[i : i + 2] for i in range(0, 6, 2))
    if oui_type == "MA-M":
        if len(raw) != 7:
            return None
        raw = raw + "0"
        return ":".join(raw[i : i + 2] for i in range(0, 8, 2))
    if oui_type == "MA-S":
        if len(raw) != 9:
            return None
        raw = raw + "000"
        return ":".join(raw[i : i + 2] for i in range(0, 12, 2))
    return None


def download_csv(url: str, label: str) -> str | None:
    logger.info(f"Downloading {label} ...")
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "SONAR-OUI-Downloader/1.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read().decode("utf-8", errors="replace")
        if not data.strip():
            logger.warning(f"Empty response from {label}")
            return None
        return data
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP {e.code} for {label}: {e.reason}")
    except urllib.error.URLError as e:
        logger.error(f"URL error for {label}: {e.reason}")
    except OSError as e:
        logger.error(f"Network error for {label}: {e}")
    return None


def parse_ieee_csv(data: str, oui_type: str) -> dict[str, str]:
    result: dict[str, str] = {}
    reader = csv.reader(io.StringIO(data))
    for row in reader:
        if not row or len(row) < 2:
            continue
        if row[0].strip().lower() in ("registry", ""):
            continue
        assignment = row[1].strip() if len(row) > 1 else ""
        organization = row[2].strip() if len(row) > 2 else ""
        if not assignment or not organization:
            continue
        prefix = normalize_prefix(assignment, oui_type)
        if prefix is None:
            continue
        if prefix not in result:
            result[prefix] = organization
    return result


def build_database(output_path: str) -> int:
    all_ouis: dict[str, str] = {}

    for oui_type, url in IEEE_URLS.items():
        data = download_csv(url, oui_type)
        if data is None:
            continue
        parsed = parse_ieee_csv(data, oui_type)
        logger.info(f"  {oui_type}: {len(parsed)} entries")
        all_ouis.update(parsed)

    if not all_ouis:
        logger.error("No OUI data downloaded. Output file not created.")
        return 1

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for prefix in sorted(all_ouis):
            writer.writerow([prefix, all_ouis[prefix]])

    logger.info(f"Written {len(all_ouis)} OUI entries to {output_path}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download IEEE OUI database and convert to S.O.N.A.R. CSV format"
    )
    parser.add_argument(
        "--output",
        default="sonar_oui.csv",
        help="Output CSV path (default: sonar_oui.csv)",
    )
    args = parser.parse_args()
    sys.exit(build_database(args.output))


if __name__ == "__main__":
    main()
