import subprocess
import platform
from abc import ABC, abstractmethod
from dataclasses import dataclass
from collections.abc import Generator
from typing import Any


DEFAULT_BPF_FILTER = "arp or port 5353 or port 1900 or (udp port 67 or udp port 68)"


@dataclass
class InterfaceInfo:
    name: str
    description: str
    is_virtual: bool = False
    is_loopback: bool = False
    is_up: bool = True


class CaptureProvider(ABC):
    @abstractmethod
    def get_interfaces(self) -> list[InterfaceInfo]:
        ...

    @abstractmethod
    def capture(self, interface: str, duration: int, bpf_filter: str = DEFAULT_BPF_FILTER) -> Generator[Any, None, None]:
        ...

    @abstractmethod
    def check_dependencies(self) -> list[str]:
        ...


class PysharkCaptureProvider(CaptureProvider):
    def check_dependencies(self) -> list[str]:
        missing = []
        if not check_tshark():
            missing.append("tshark not found on PATH. Install Wireshark or Npcap with tshark option.")
        if platform.system() == "Windows":
            try:
                result = subprocess.run(
                    ["sc", "query", "npf"],
                    capture_output=True, text=True, timeout=5
                )
                if "RUNNING" not in result.stdout and "STOPPED" not in result.stdout:
                    missing.append("Npcap service not found. Install from https://npcap.com")
            except Exception:
                missing.append("Could not check Npcap service status.")
        return missing

    def get_interfaces(self) -> list[InterfaceInfo]:
        try:
            result = subprocess.run(
                ["tshark", "-D"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return []
            interfaces = []
            for line in result.stdout.strip().split("\n"):
                if "." not in line:
                    continue
                parts = line.split(".", 1)
                name = parts[0].strip()
                desc = parts[1].strip() if len(parts) > 1 else ""
                is_virtual = any(v in desc.lower() for v in ["virtual", "vmware", "virtualbox", "hyper-v", "wsl"])
                is_loopback = "loopback" in desc.lower() or "loopback" in name.lower()
                interfaces.append(InterfaceInfo(
                    name=name, description=desc,
                    is_virtual=is_virtual, is_loopback=is_loopback
                ))
            return interfaces
        except FileNotFoundError:
            return []
        except Exception:
            return []

    def capture(self, interface: str, duration: int, bpf_filter: str = DEFAULT_BPF_FILTER) -> Generator[Any, None, None]:
        try:
            import pyshark
            capture = pyshark.LiveCapture(
                interface=interface,
                bpf_filter=bpf_filter
            )
            for packet in capture.sniff_continuously(packet_count=0):
                yield packet
        except Exception as e:
            raise RuntimeError(f"Capture failed: {e}")


def get_best_interface() -> str | None:
    try:
        result = subprocess.run(
            ["tshark", "-D"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return None
        virtual_keywords = ["virtual", "vmware", "virtualbox", "hyper-v", "wsl", "docker"]
        best = None
        for line in result.stdout.strip().split("\n"):
            if "." not in line:
                continue
            parts = line.split(".", 1)
            name = parts[0].strip()
            desc = parts[1].strip().lower() if len(parts) > 1 else ""
            if any(kw in desc for kw in virtual_keywords):
                continue
            if "loopback" in desc or "loopback" in name.lower():
                continue
            if "wi-fi" in desc or "wifi" in desc or "wireless" in desc or "802.11" in desc:
                return name
            if best is None:
                best = name
        return best
    except FileNotFoundError:
        return None
    except Exception:
        return None


def check_admin() -> bool:
    if platform.system() != "Windows":
        import os
        return os.getuid() == 0
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def check_tshark() -> bool:
    try:
        result = subprocess.run(
            ["tshark", "--version"],
            capture_output=True, timeout=5
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False
    except Exception:
        return False
