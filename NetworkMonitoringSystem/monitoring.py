"""Device polling, persistence, and lightweight ML monitoring records."""

from __future__ import annotations

import os
import platform
import re
import json
import statistics
import sqlite3
import subprocess
import ipaddress
import socket
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil

BASE_DIR = Path(__file__).resolve().parent
POLL_INTERVAL_SECONDS = int(os.getenv("MONITORING_POLL_SECONDS", "30"))

# MAC OUI database for phone/device detection
PHONE_MANUFACTURERS = {
    "00:1a:2b", "00:1a:2d", "00:1a:5e", "00:1d:4f", "00:25:86", "00:50:f2",  # Apple
    "b0:35:9f", "5c:f3:70", "00:1e:52", "9c:a6:15", "04:fd:55", "74:33:c3",  # Samsung
    "e4:54:e8", "54:6a:5c", "e8:ba:70",  # Huawei
    "1e:10:3d", "90:a2:da", "d0:76:d0",  # OnePlus
    "8c:72:f8", "00:aa:33",  # Xiaomi
    "bc:f5:ac", "28:11:95",  # LG
    "00:0d:93", "a4:ae:12",  # Google Pixel
    "5c:6d:7e", "00:e0:4c",  # Motorola
    "7c:7a:91", "a4:2b:8c",  # HTC
    "f4:f1:e0", "84:89:ad",  # Sony
    "08:62:66", "e8:99:c4",  # Amazon
}


def _get_database_path() -> Path:
    """Get the database path based on the building name."""
    from pathlib import Path
    # Create a temporary connection to get building name
    temp_db = BASE_DIR / "monitoring.db"
    if temp_db.exists():
        try:
            temp_conn = sqlite3.connect(temp_db, timeout=10)
            temp_conn.row_factory = sqlite3.Row
            result = temp_conn.execute(
                "SELECT value FROM application_settings WHERE key = 'building_name' LIMIT 1"
            ).fetchone()
            temp_conn.close()
            if result:
                building_name = str(result["value"]).replace(" ", "_").replace("/", "_")
                return BASE_DIR / f"monitoring_{building_name}.db"
        except Exception:
            pass
    return temp_db


@property
def DATABASE_PATH():
    return _get_database_path()

DATABASE_PATH = _get_database_path()

_db_lock = threading.Lock()
_reference_poll_lock = threading.Lock()
_worker: threading.Thread | None = None
_stop_event = threading.Event()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    db_path = _get_database_path()
    connection = sqlite3.connect(db_path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    return connection


def initialize_database() -> None:
    with _db_lock, _connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recorded_at TEXT NOT NULL,
                device_name TEXT NOT NULL,
                target TEXT NOT NULL,
                device_type TEXT NOT NULL,
                protocol TEXT NOT NULL,
                online INTEGER NOT NULL,
                latency_ms REAL,
                packet_loss REAL NOT NULL,
                cpu_percent REAL,
                memory_percent REAL,
                bandwidth_percent REAL,
                send_kbps REAL NOT NULL DEFAULT 0,
                receive_kbps REAL NOT NULL DEFAULT 0,
                throughput_kbps REAL NOT NULL DEFAULT 0,
                mib_in_octets REAL,
                mib_out_octets REAL,
                mib_in_errors REAL,
                mib_out_errors REAL,
                mib_in_rate REAL,
                mib_out_rate REAL,
                anomaly_score REAL NOT NULL DEFAULT 0,
                anomaly_label TEXT NOT NULL DEFAULT 'normal',
                error TEXT
            );
            CREATE TABLE IF NOT EXISTS ml_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recorded_at TEXT NOT NULL,
                device_name TEXT NOT NULL,
                model_version TEXT NOT NULL,
                result TEXT NOT NULL,
                confidence REAL NOT NULL,
                status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS condition_labels (
                telemetry_id INTEGER PRIMARY KEY,
                label TEXT NOT NULL,
                reviewed_at TEXT NOT NULL,
                FOREIGN KEY (telemetry_id) REFERENCES telemetry(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS recommendation_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telemetry_id INTEGER NOT NULL,
                target TEXT NOT NULL,
                suggestion_id TEXT NOT NULL,
                suggested_action TEXT NOT NULL,
                model_sources TEXT NOT NULL,
                evidence TEXT NOT NULL,
                selected_at TEXT NOT NULL,
                outcome TEXT NOT NULL DEFAULT 'pending',
                verified_finding TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                outcome_at TEXT,
                FOREIGN KEY (telemetry_id) REFERENCES telemetry(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recorded_at TEXT NOT NULL,
                device_name TEXT NOT NULL,
                message TEXT NOT NULL,
                severity TEXT NOT NULL,
                open INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS monitored_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                target TEXT NOT NULL UNIQUE,
                active INTEGER NOT NULL DEFAULT 0,
                interval_seconds INTEGER NOT NULL DEFAULT 10,
                added_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS application_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reference_telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recorded_at TEXT NOT NULL,
                reference_kind TEXT NOT NULL,
                reference_name TEXT NOT NULL,
                target TEXT NOT NULL,
                online INTEGER NOT NULL,
                latency_ms REAL,
                latency_min_ms REAL,
                latency_median_ms REAL,
                latency_max_ms REAL,
                packet_loss REAL NOT NULL,
                ping_sent INTEGER NOT NULL,
                ping_received INTEGER NOT NULL,
                latency_readings TEXT NOT NULL DEFAULT '[]'
            );
            """
        )
        external_reference = os.getenv("EXTERNAL_PING_REFERENCE", "1.1.1.1")
        try:
            external_reference = str(ipaddress.IPv4Address(external_reference))
        except ipaddress.AddressValueError:
            external_reference = "1.1.1.1"
        connection.execute(
            "INSERT OR IGNORE INTO application_settings (key, value) VALUES ('external_reference_ipv4', ?)",
            (external_reference,),
        )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(telemetry)")}
        for column in ("send_kbps", "receive_kbps", "throughput_kbps", "mib_in_octets", "mib_out_octets", "mib_in_errors", "mib_out_errors", "mib_in_rate", "mib_out_rate", "anomaly_score", "anomaly_label"):
            if column not in columns:
                column_type = "TEXT NOT NULL DEFAULT 'normal'" if column == "anomaly_label" else "REAL NOT NULL DEFAULT 0"
                connection.execute(f"ALTER TABLE telemetry ADD COLUMN {column} {column_type}")
        columns = {row[1] for row in connection.execute("PRAGMA table_info(telemetry)")}
        additions = {
            "latency_min_ms": "REAL",
            "latency_median_ms": "REAL",
            "latency_max_ms": "REAL",
            "ping_sent": "INTEGER NOT NULL DEFAULT 5",
            "ping_received": "INTEGER NOT NULL DEFAULT 0",
            "latency_readings": "TEXT NOT NULL DEFAULT '[]'",
        }
        for column, declaration in additions.items():
            if column not in columns:
                connection.execute(f"ALTER TABLE telemetry ADD COLUMN {column} {declaration}")
        # Add mac_address column to monitored_devices if not exists
        monitored_columns = {row[1] for row in connection.execute("PRAGMA table_info(monitored_devices)")}
        if "mac_address" not in monitored_columns:
            connection.execute("ALTER TABLE monitored_devices ADD COLUMN mac_address TEXT DEFAULT ''")
        # Add device_type column to monitored_devices if not exists
        if "device_type" not in monitored_columns:
            connection.execute("ALTER TABLE monitored_devices ADD COLUMN device_type TEXT DEFAULT 'pc'")


def _ping(target: str, count: int = 5) -> dict[str, Any]:
    probe_count = max(1, min(count, 5))
    command = ["ping", "-n", str(probe_count), "-w", "400" if probe_count == 1 else "1000", target] if platform.system() == "Windows" else ["ping", "-c", str(probe_count), "-W", "1" if probe_count == 1 else "2", target]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=1.5 if probe_count == 1 else 12, check=False)
        output = f"{result.stdout}\n{result.stderr}"
        readings = []
        for match in re.finditer(r"time(?P<operator>[=<])\s*(?P<value>\d+(?:\.\d+)?)\s*ms", output, re.IGNORECASE):
            value = float(match.group("value"))
            readings.append({"display": f"<{match.group('value')}" if match.group("operator") == "<" else match.group("value"), "upper_bound_ms": value})
        values = [reading["upper_bound_ms"] for reading in readings]
        received = len(readings)
        online = received > 0 or result.returncode == 0
        median = statistics.median(values) if values else None
        ordered_readings = sorted(readings, key=lambda reading: reading["upper_bound_ms"])
        median_reading = ordered_readings[len(ordered_readings) // 2] if ordered_readings else None
        median_display = f"<{median_reading['upper_bound_ms']:g} ms" if received == probe_count and received == 5 and median_reading and median_reading["display"].startswith("<") else f"{median:g} ms" if median is not None else "-"
        return {
            "online": online,
            "latency_ms": median,
            "latency_min_ms": min(values) if values else None,
            "latency_median_ms": median,
            "latency_max_ms": max(values) if values else None,
            "latency_min_display": f"<{min(values):g} ms" if any(reading["display"].startswith("<") and reading["upper_bound_ms"] == min(values) for reading in readings) else f"{min(values):g} ms" if values else "-",
            "latency_median_display": median_display,
            "latency_max_display": f"<{max(values):g} ms" if values and all(reading["display"].startswith("<") for reading in readings) else f"{max(values):g} ms" if values else "-",
            "ping_sent": probe_count,
            "ping_received": received,
            "packet_loss": round((probe_count - received) * 100 / probe_count, 1),
            "latency_readings": json.dumps([reading["display"] for reading in readings]),
            "error": None if online else "No ping response",
        }
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"online": False, "latency_ms": None, "latency_min_ms": None, "latency_median_ms": None, "latency_max_ms": None, "latency_min_display": "-", "latency_median_display": "-", "latency_max_display": "-", "ping_sent": probe_count, "ping_received": 0, "packet_loss": 100.0, "latency_readings": "[]", "error": str(error)}


def _collect_device(device: dict[str, Any]) -> dict[str, Any]:
    target = str(device.get("target", ""))
    result = _ping(target)
    result.update({
        "recorded_at": _utc_now(),
        "device_name": device.get("name", target),
        "target": target,
        "device_type": "PC",
        "protocol": "icmp",
        "packet_loss": result["packet_loss"],
    })
    return result


def _classify(sample: dict[str, Any]) -> tuple[str, float, str]:
    if not sample["online"]:
        return "Device unreachable", 0.99, "Flagged"
    score = 0.0
    reasons = []
    if sample.get("latency_ms") and sample["latency_ms"] > 150:
        score += 0.8
        reasons.append("high latency")
    if sample.get("packet_loss", 0) > 0:
        score += 0.8
        reasons.append("packet loss")
    if score >= 0.6:
        return "Ping anomaly: " + ", ".join(reasons), min(0.99, round(score, 2)), "Flagged"
    return "Normal ping", 0.96, "Normal"


def get_local_network() -> dict[str, str]:
    candidates = []
    for interface, addresses in psutil.net_if_addrs().items():
        stats = psutil.net_if_stats().get(interface)
        if not stats or not stats.isup:
            continue
        lowered = interface.lower()
        # Explicitly skip known virtual/hypervisor adapters
        if any(token in lowered for token in ("vethernet", "hyper-v", "virtual", "docker", "wsl", "vmware", "vbox", "loopback")):
            continue
        for address in addresses:
            if address.family.name != "AF_INET" or address.address.startswith("127.") or not address.netmask:
                continue
            network = ipaddress.ip_network(f"{address.address}/{address.netmask}", strict=False)
            # Rank interfaces: prefer physical > vpn > others
            is_wifi = any(token in lowered for token in ("wi-fi", "wifi", "wireless", "wlan"))
            is_ethernet = any(token in lowered for token in ("ethernet", "eth", "lan"))
            is_vpn = "vpn" in lowered
            is_tunnel = "tunnel" in lowered
            is_radmin = "radmin" in lowered
            # Ranking: lower is better (wifi=0, ethernet=1, vpn=2, tunnel=3, radmin=4, other=5)
            if is_wifi:
                rank = 0
            elif is_ethernet:
                rank = 1
            elif is_vpn:
                rank = 2
            elif is_tunnel:
                rank = 3
            elif is_radmin:
                rank = 4
            else:
                rank = 5
            suggested = network if network.num_addresses <= 256 else ipaddress.ip_network(f"{address.address}/24", strict=False)
            candidates.append((rank, interface, address.address, network, suggested))
    if not candidates:
        raise ValueError("Could not determine an active local IPv4 subnet")
    _, interface, address, network, suggested = sorted(candidates)[0]
    return {"interface": interface, "address": address, "subnet": str(network), "suggested_subnet": str(suggested), "virtual": "false"}


def _get_mac_address(target: str) -> str:
    """Get MAC address for a given IP address using ARP cache."""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["arp", "-a", target],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            # Parse Windows arp output: look for MAC in format XX-XX-XX-XX-XX-XX
            match = re.search(r"([0-9a-f]{2}(?:-[0-9a-f]{2}){5})", result.stdout, re.IGNORECASE)
            if match:
                return match.group(1).lower()
        else:
            result = subprocess.run(
                ["arp", "-n", target],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            # Parse Unix arp output: look for MAC in format XX:XX:XX:XX:XX:XX
            match = re.search(r"([0-9a-f]{2}(?::[0-9a-f]{2}){5})", result.stdout, re.IGNORECASE)
            if match:
                return match.group(1).lower()
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def _detect_device_type(mac_address: str) -> str:
    """Detect device type from MAC address OUI."""
    if not mac_address:
        return "unknown"
    # Normalize MAC to colon format
    mac_normalized = mac_address.lower().replace("-", ":")
    # Get OUI (first 3 bytes)
    oui = ":".join(mac_normalized.split(":")[:3]) if len(mac_normalized.split(":")) >= 3 else ""
    if oui in PHONE_MANUFACTURERS:
        return "phone"
    return "pc"


def _resolve_hostname(target: str) -> str:
    """Resolve hostname from IP address using reverse DNS or NetBIOS."""
    try:
        # Try standard reverse DNS first
        hostname, _, _ = socket.gethostbyaddr(target)
        if hostname and hostname != target:
            return hostname.split('.')[0]  # Return just the hostname without FQDN
    except (socket.herror, socket.timeout, OSError):
        pass
    
    # Try Windows NetBIOS lookup for local network
    if platform.system() == "Windows":
        try:
            result = subprocess.run(
                ["nbtstat", "-A", target],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            # Parse nbtstat output for computer name (usually first entry with <00> or <20>)
            for line in result.stdout.split('\n'):
                if '<20>' in line or '<00>' in line:
                    parts = line.split()
                    if parts:
                        name = parts[0].strip()
                        if name and name != target:
                            return name
        except (OSError, subprocess.TimeoutExpired):
            pass
    
    return target


def _get_default_gateway(local_address: str, interface: str) -> str | None:
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["route.exe", "print", "-4"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            routes = re.findall(
                r"^\s*0\.0\.0\.0\s+0\.0\.0\.0\s+(\S+)\s+(\d{1,3}(?:\.\d{1,3}){3})\s+\d+\s*$",
                result.stdout,
                re.MULTILINE,
            )
            for gateway, route_interface in routes:
                if route_interface == local_address:
                    try:
                        return str(ipaddress.IPv4Address(gateway))
                    except ipaddress.AddressValueError:
                        continue
            candidate = []
        else:
            result = subprocess.run(
                ["ip", "-4", "route", "show", "default", "dev", interface],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            candidate = re.findall(r"\bvia\s+(\d{1,3}(?:\.\d{1,3}){3})\b", result.stdout)
        for value in candidate:
            try:
                return str(ipaddress.IPv4Address(value))
            except ipaddress.AddressValueError:
                continue
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    return None


def get_external_reference_target() -> str:
    initialize_database()
    with _db_lock, _connect() as connection:
        row = connection.execute(
            "SELECT value FROM application_settings WHERE key = 'external_reference_ipv4'"
        ).fetchone()
    return str(row["value"]) if row else "1.1.1.1"


def save_external_reference_target(target: str) -> str:
    try:
        address = str(ipaddress.IPv4Address(target.strip()))
    except (AttributeError, ipaddress.AddressValueError) as error:
        raise ValueError("Enter a valid external IPv4 reference address") from error
    initialize_database()
    with _db_lock, _connect() as connection:
        connection.execute(
            "INSERT INTO application_settings (key, value) VALUES ('external_reference_ipv4', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (address,),
        )
    return address


def get_network_reference_targets() -> list[dict[str, str]]:
    external_target = get_external_reference_target()
    try:
        local = get_local_network()
        gateway_target = _get_default_gateway(local["address"], local["interface"])
    except (KeyError, ValueError):
        gateway_target = None
    targets = []
    if gateway_target:
        targets.append({"kind": "gateway", "name": "Local gateway", "target": gateway_target})
    if external_target != gateway_target:
        targets.append({"kind": "external", "name": "External reference", "target": external_target})
    return targets


def _poll_network_references() -> list[dict[str, Any]]:
    if not _reference_poll_lock.acquire(blocking=False):
        return []
    try:
        targets = get_network_reference_targets()
        if not targets:
            return []
        with ThreadPoolExecutor(max_workers=len(targets)) as executor:
            results = list(executor.map(lambda target: (target, _ping(target["target"])), targets))
        recorded_at = _utc_now()
        with _db_lock, _connect() as connection:
            for target, result in results:
                result.update(target)
                result["recorded_at"] = recorded_at
                connection.execute(
                    """
                    INSERT INTO reference_telemetry
                        (recorded_at, reference_kind, reference_name, target, online, latency_ms,
                         latency_min_ms, latency_median_ms, latency_max_ms, packet_loss,
                         ping_sent, ping_received, latency_readings)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        recorded_at,
                        target["kind"],
                        target["name"],
                        target["target"],
                        int(result["online"]),
                        result["latency_ms"],
                        result["latency_min_ms"],
                        result["latency_median_ms"],
                        result["latency_max_ms"],
                        result["packet_loss"],
                        result["ping_sent"],
                        result["ping_received"],
                        result["latency_readings"],
                    ),
                )
        return [{**target, **result, "recorded_at": recorded_at} for target, result in results]
    finally:
        _reference_poll_lock.release()


def poll_network_references() -> list[dict[str, Any]]:
    return _poll_network_references()


def _rolling_ping_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    recent = rows[-5:]
    if not recent:
        return {"sample_count": 0, "online": None, "packet_loss_percent": None, "latency_median_ms": None, "latency_variation_ms": None}
    sent = sum(int(row.get("ping_sent") or 0) for row in recent)
    received = sum(int(row.get("ping_received") or 0) for row in recent)
    latencies = [
        float(row.get("latency_median_ms") or row.get("latency_ms"))
        for row in recent
        if row.get("latency_median_ms") is not None or row.get("latency_ms") is not None
    ]
    changes = [abs(later - earlier) for earlier, later in zip(latencies, latencies[1:])]
    return {
        "sample_count": len(recent),
        "online": bool(recent[-1].get("online")),
        "packet_loss_percent": round((sent - received) * 100 / sent, 1) if sent else None,
        "latency_median_ms": round(statistics.median(latencies), 2) if latencies else None,
        "latency_variation_ms": round(statistics.median(changes), 2) if changes else None,
        "latest_recorded_at": recent[-1].get("recorded_at"),
    }


def get_network_reference_status() -> dict[str, Any]:
    targets = get_network_reference_targets()
    with _db_lock, _connect() as connection:
        reference_rows = connection.execute(
            "SELECT * FROM reference_telemetry ORDER BY id DESC LIMIT 200"
        ).fetchall()
        pc_rows = connection.execute(
            """
            SELECT * FROM telemetry WHERE protocol = 'icmp' AND device_type = 'PC'
            ORDER BY id DESC LIMIT 2000
            """
        ).fetchall()
    references_by_target: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in reversed(reference_rows):
        references_by_target[str(row["target"])].append(_row_dict(row))
    reference_summaries = []
    for target in targets:
        rows = references_by_target.get(target["target"], [])
        summary = _rolling_ping_summary(rows)
        reference_summaries.append({**target, **summary})
    gateway = next((item for item in reference_summaries if item["kind"] == "gateway"), None)
    external = next((item for item in reference_summaries if item["kind"] == "external"), None)

    devices_by_target: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in reversed(pc_rows):
        sample = _row_dict(row)
        if (sample["online"] and sample["ping_received"] > 0 and (sample["latency_median_ms"] is not None or sample["latency_ms"] is not None)) or (not sample["online"] and sample["ping_received"] == 0):
            devices_by_target[str(sample["target"])].append(sample)
    devices = []
    for target, rows in devices_by_target.items():
        summary = _rolling_ping_summary(rows)
        if gateway is None or gateway["sample_count"] == 0:
            comparison = "Gateway comparison unavailable; continue using the PC's own rolling ping results."
        elif not gateway["online"]:
            comparison = "Gateway did not reply; local-path degradation is possible, but ICMP filtering may also explain it."
        elif external is not None and external["sample_count"] and not external["online"]:
            comparison = "Gateway replies but the external reference does not; upstream path issues or external ICMP filtering are possible."
        elif not summary["online"] and gateway["online"]:
            comparison = "Gateway replies while this PC does not; check the endpoint, its connection, or its ICMP policy."
        elif summary["packet_loss_percent"] is not None and summary["packet_loss_percent"] > 0:
            comparison = "PC packet loss is present; compare its rolling loss and latency variation with the gateway and other PCs."
        else:
            comparison = "PC and gateway are responding; no clear shared-path issue is visible in these samples."
        devices.append({"target": target, **summary, "comparison": comparison})
    return {
        "gateway": gateway,
        "external": external,
        "external_reference_target": get_external_reference_target(),
        "devices": devices,
        "window_samples": 5,
        "probes_per_sample": 5,
        "note": "ICMP comparisons are indicators only; filtering and endpoint policies can affect replies.",
    }


def get_network_reference_samples(limit: int = 2000) -> list[dict[str, Any]]:
    initialize_database()
    with _db_lock, _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM reference_telemetry ORDER BY id DESC LIMIT ?",
            (max(1, min(int(limit), 10000)),),
        ).fetchall()
    return [_row_dict(row) for row in reversed(rows)]


def discover_hosts(subnet: str, limit: int = 0) -> list[dict[str, str]]:
    local_network = ipaddress.ip_network(get_local_network()["subnet"], strict=False)
    requested_network = ipaddress.ip_network(subnet, strict=False)
    if requested_network.version != 4 or not requested_network.subnet_of(local_network):
        raise ValueError("Discovery is limited to an IPv4 subnet within the active local network")
    if requested_network.num_addresses > 256:
        raise ValueError("Choose a subnet with no more than 256 addresses")
    candidates = [str(address) for address in requested_network.hosts()]
    found = []
    limit_val = max(1, min(int(limit), 999)) if limit > 0 else len(candidates)
    with ThreadPoolExecutor(max_workers=128) as executor:
        tasks = {executor.submit(_ping, target, 1): target for target in candidates}
        for task in as_completed(tasks):
            if len(found) >= limit_val:
                break
            target = tasks[task]
            try:
                result = task.result()
            except Exception:
                continue
            if result["online"]:
                mac_addr = _get_mac_address(target)
                device_type = _detect_device_type(mac_addr)
                found.append({"name": target, "target": target, "mac_address": mac_addr, "device_type": device_type})
    return sorted(found, key=lambda item: ipaddress.ip_address(item["target"]))


def get_monitored_devices() -> list[dict[str, Any]]:
    initialize_database()
    with _db_lock, _connect() as connection:
        rows = connection.execute("SELECT * FROM monitored_devices ORDER BY name COLLATE NOCASE").fetchall()
    return [_row_dict(row) for row in rows]


def add_monitored_device(name: str, target: str) -> dict[str, Any]:
    initialize_database()
    address = ipaddress.ip_address(target)
    mac_addr = _get_mac_address(str(address))
    device_type = _detect_device_type(mac_addr)
    
    # Auto-resolve hostname if name is empty or just an IP address
    clean_name = name.strip()[:100] if name.strip() else ""
    if not clean_name or clean_name == str(address):
        resolved_name = _resolve_hostname(str(address))
        if resolved_name and resolved_name != str(address):
            clean_name = resolved_name
        else:
            clean_name = str(address)
    
    with _db_lock, _connect() as connection:
        connection.execute(
            "INSERT INTO monitored_devices (name, target, active, interval_seconds, added_at, mac_address, device_type) VALUES (?, ?, 0, ?, ?, ?, ?) ON CONFLICT(target) DO UPDATE SET name = excluded.name, mac_address = excluded.mac_address, device_type = excluded.device_type",
            (clean_name, str(address), POLL_INTERVAL_SECONDS, _utc_now(), mac_addr, device_type),
        )
        row = connection.execute("SELECT * FROM monitored_devices WHERE target = ?", (str(address),)).fetchone()
    return _row_dict(row)


def update_monitored_device(device_id: int, *, active: bool | None = None, interval_seconds: int | None = None) -> bool:
    initialize_database()
    with _db_lock, _connect() as connection:
        if active is not None:
            connection.execute("UPDATE monitored_devices SET active = ? WHERE id = ?", (int(active), device_id))
        if interval_seconds is not None:
            interval = max(5, min(int(interval_seconds), 3600))
            connection.execute("UPDATE monitored_devices SET interval_seconds = ? WHERE id = ?", (interval, device_id))
        return connection.execute("SELECT changes()").fetchone()[0] > 0


def remove_monitored_device(device_id: int) -> bool:
    initialize_database()
    with _db_lock, _connect() as connection:
        connection.execute("DELETE FROM monitored_devices WHERE id = ?", (device_id,))
        return connection.execute("SELECT changes()").fetchone()[0] > 0


def _poll_devices(devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    with ThreadPoolExecutor(max_workers=min(32, max(1, len(devices)))) as executor:
        samples = list(executor.map(_collect_device, devices))
    with _db_lock, _connect() as connection:
        for sample in samples:
            result, confidence, status = _classify(sample)
            anomaly_score = 1.0 if status == "Flagged" else 0.0
            sample.update({"anomaly_label": result, "anomaly_score": anomaly_score, "status": status})
            connection.execute(
                "INSERT INTO telemetry (recorded_at, device_name, target, device_type, protocol, online, latency_ms, packet_loss, latency_min_ms, latency_median_ms, latency_max_ms, ping_sent, ping_received, latency_readings, anomaly_score, anomaly_label, error) VALUES (?, ?, ?, 'PC', 'icmp', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sample["recorded_at"], sample["device_name"], sample["target"], int(sample["online"]), sample["latency_ms"], sample["packet_loss"], sample["latency_min_ms"], sample["latency_median_ms"], sample["latency_max_ms"], sample["ping_sent"], sample["ping_received"], sample["latency_readings"], anomaly_score, result, sample["error"]),
            )
            connection.execute(
                "INSERT INTO ml_records (recorded_at, device_name, model_version, result, confidence, status) VALUES (?, ?, 'icmp-ping-v1', ?, ?, ?)",
                (sample["recorded_at"], sample["device_name"], result, confidence, status),
            )
            if status == "Flagged":
                connection.execute(
                    "INSERT INTO alerts (recorded_at, device_name, message, severity) VALUES (?, ?, ?, ?)",
                    (sample["recorded_at"], sample["device_name"], result, "high" if not sample["online"] else "medium"),
                )
    return samples


def poll_once() -> list[dict[str, Any]]:
    initialize_database()
    devices = [device for device in get_monitored_devices() if device["active"]]
    return _poll_devices(devices)


def _poll_loop() -> None:
    last_poll: dict[int, float] = {}
    last_reference_poll = 0.0
    reference_worker: threading.Thread | None = None
    while not _stop_event.is_set():
        try:
            now = time.monotonic()
            if now - last_reference_poll >= POLL_INTERVAL_SECONDS and (
                reference_worker is None or not reference_worker.is_alive()
            ):
                last_reference_poll = now
                reference_worker = threading.Thread(
                    target=_poll_network_references,
                    name="network-reference-monitor",
                    daemon=True,
                )
                reference_worker.start()
            due = []
            for device in get_monitored_devices():
                if not device["active"]:
                    last_poll.pop(device["id"], None)
                    continue
                if now - last_poll.get(device["id"], 0) >= device["interval_seconds"]:
                    due.append(device)
                    last_poll[device["id"]] = now
            if due:
                _poll_devices(due)
        except Exception:
            pass
        _stop_event.wait(0.5)


def start_monitoring() -> None:
    global _worker
    initialize_database()
    if _worker and _worker.is_alive():
        return
    _stop_event.clear()
    _worker = threading.Thread(target=_poll_loop, name="network-monitor", daemon=True)
    _worker.start()


def stop_monitoring() -> None:
    _stop_event.set()


def _row_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def _latency_display(sample: dict[str, Any], statistic: str) -> str:
    readings = json.loads(sample.get("latency_readings") or "[]")
    sub_ms_count = sum(str(reading).startswith("<") for reading in readings)
    value = sample.get(f"latency_{statistic}_ms")
    if value is None and statistic == "median":
        value = sample.get("latency_ms")
    if value is None:
        return "-"
    if statistic == "min" and sub_ms_count and value <= 1:
        return "<1 ms"
    if statistic == "median" and sample.get("ping_sent", 5) == 5 and sub_ms_count >= 3:
        return "<1 ms"
    if statistic == "max" and readings and sub_ms_count == len(readings) and value <= 1:
        return "<1 ms"
    return f"{value:g} ms"


def get_monitoring_data() -> dict[str, Any]:
    initialize_database()
    with _db_lock, _connect() as connection:
        telemetry = [
            _row_dict(row)
            for row in connection.execute(
                """
                SELECT * FROM telemetry
                WHERE protocol = 'icmp'
                  AND ((online = 1 AND ping_received > 0
                        AND COALESCE(latency_median_ms, latency_ms) IS NOT NULL)
                       OR (online = 0 AND ping_received = 0))
                ORDER BY id DESC LIMIT 100
                """
            )
        ]
        ml_records = [_row_dict(row) for row in connection.execute("SELECT * FROM ml_records WHERE model_version = 'icmp-ping-v1' ORDER BY id DESC LIMIT 50")]
        alerts = [_row_dict(row) for row in connection.execute("SELECT alerts.* FROM alerts WHERE open = 1 AND EXISTS (SELECT 1 FROM ml_records WHERE ml_records.recorded_at = alerts.recorded_at AND ml_records.device_name = alerts.device_name AND ml_records.model_version = 'icmp-ping-v1') ORDER BY alerts.id DESC LIMIT 20")]
    for sample in telemetry:
        sample["latency_min_display"] = _latency_display(sample, "min")
        sample["latency_median_display"] = _latency_display(sample, "median")
        sample["latency_max_display"] = _latency_display(sample, "max")
    return {"devices": get_monitored_devices(), "telemetry": telemetry, "ml_records": ml_records, "alerts": alerts}


def get_ml_training_data() -> tuple[list[dict[str, Any]], dict[int, str]]:
    initialize_database()
    with _db_lock, _connect() as connection:
        samples = [
            _row_dict(row)
            for row in connection.execute(
                "SELECT * FROM telemetry WHERE protocol = 'icmp' ORDER BY id"
            )
        ]
        labels = {
            int(row["telemetry_id"]): str(row["label"])
            for row in connection.execute("SELECT telemetry_id, label FROM condition_labels")
        }
    return samples, labels


def get_ml_labeling_samples(limit: int = 100) -> list[dict[str, Any]]:
    initialize_database()
    with _db_lock, _connect() as connection:
        rows = connection.execute(
            """
            SELECT telemetry.id, telemetry.recorded_at, telemetry.device_name, telemetry.target,
                   telemetry.online, telemetry.latency_median_ms, telemetry.latency_ms,
                   telemetry.packet_loss, telemetry.ping_sent, telemetry.ping_received,
                   condition_labels.label AS condition_label
            FROM telemetry
            LEFT JOIN condition_labels ON condition_labels.telemetry_id = telemetry.id
            WHERE telemetry.protocol = 'icmp'
              AND ((telemetry.online = 1 AND telemetry.ping_received > 0
                    AND COALESCE(telemetry.latency_median_ms, telemetry.latency_ms) IS NOT NULL)
                   OR (telemetry.online = 0 AND telemetry.ping_received = 0))
            ORDER BY telemetry.id DESC LIMIT ?
            """,
            (max(1, min(int(limit), 500)),),
        ).fetchall()
    return [_row_dict(row) for row in rows]


def save_condition_label(telemetry_id: int, label: str) -> bool:
    allowed_labels = {"Normal", "High Latency", "Packet Loss", "Unreachable"}
    if label not in allowed_labels:
        raise ValueError("Choose a supported condition label")
    initialize_database()
    with _db_lock, _connect() as connection:
        sample = connection.execute(
            """
            SELECT id FROM telemetry
            WHERE id = ? AND protocol = 'icmp'
              AND ((online = 1 AND ping_received > 0
                    AND COALESCE(latency_median_ms, latency_ms) IS NOT NULL)
                   OR (online = 0 AND ping_received = 0))
            """,
            (telemetry_id,),
        ).fetchone()
        if not sample:
            return False
        connection.execute(
            """
            INSERT INTO condition_labels (telemetry_id, label, reviewed_at)
            VALUES (?, ?, ?)
            ON CONFLICT(telemetry_id) DO UPDATE SET label = excluded.label, reviewed_at = excluded.reviewed_at
            """,
            (telemetry_id, label, _utc_now()),
        )
    return True


def save_recommendation_selection(
    telemetry_id: int,
    target: str,
    suggestion: dict[str, Any],
) -> int | None:
    initialize_database()
    with _db_lock, _connect() as connection:
        sample = connection.execute(
            """
            SELECT id FROM telemetry
            WHERE id = ? AND target = ? AND protocol = 'icmp'
              AND ((online = 1 AND ping_received > 0
                    AND COALESCE(latency_median_ms, latency_ms) IS NOT NULL)
                   OR (online = 0 AND ping_received = 0))
            """,
            (telemetry_id, target),
        ).fetchone()
        if not sample:
            return None
        cursor = connection.execute(
            """
            INSERT INTO recommendation_feedback
                (telemetry_id, target, suggestion_id, suggested_action, model_sources,
                 evidence, selected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                telemetry_id,
                target,
                suggestion["id"],
                suggestion["action"],
                json.dumps(suggestion["model_sources"]),
                json.dumps(suggestion["evidence"]),
                _utc_now(),
            ),
        )
        return int(cursor.lastrowid)


def get_recommendation_feedback(limit: int = 100) -> list[dict[str, Any]]:
    initialize_database()
    with _db_lock, _connect() as connection:
        rows = connection.execute(
            """
            SELECT recommendation_feedback.*, telemetry.device_name, telemetry.recorded_at
            FROM recommendation_feedback
            JOIN telemetry ON telemetry.id = recommendation_feedback.telemetry_id
            ORDER BY recommendation_feedback.id DESC LIMIT ?
            """,
            (max(1, min(int(limit), 500)),),
        ).fetchall()
    results = [_row_dict(row) for row in rows]
    for row in results:
        row["model_sources"] = json.loads(row["model_sources"])
        row["evidence"] = json.loads(row["evidence"])
    return results


def save_recommendation_outcome(
    feedback_id: int,
    outcome: str,
    verified_finding: str,
    notes: str,
) -> bool:
    allowed_outcomes = {"resolved", "not_resolved", "unknown"}
    allowed_findings = {
        "",
        "Shared path degradation",
        "Device-specific issue",
        "ICMP blocked",
        "No issue found",
        "Other / unknown",
    }
    if outcome not in allowed_outcomes:
        raise ValueError("Choose Resolved, Not resolved, or Unknown")
    if verified_finding not in allowed_findings:
        raise ValueError("Choose a supported verified finding")
    initialize_database()
    with _db_lock, _connect() as connection:
        connection.execute(
            """
            UPDATE recommendation_feedback
            SET outcome = ?, verified_finding = ?, notes = ?, outcome_at = ?
            WHERE id = ?
            """,
            (outcome, verified_finding, notes.strip()[:1000], _utc_now(), feedback_id),
        )
        return connection.execute("SELECT changes()").fetchone()[0] > 0


def get_building_name() -> str:
    """Get the current building name from application settings."""
    initialize_database()
    with _db_lock, _connect() as connection:
        row = connection.execute(
            "SELECT value FROM application_settings WHERE key = 'building_name'"
        ).fetchone()
    return str(row["value"]) if row else "Unknown Building"


def save_building_name(name: str) -> str:
    """Save the building name to application settings."""
    clean_name = name.strip()[:100] or "Unknown Building"
    initialize_database()
    with _db_lock, _connect() as connection:
        connection.execute(
            "INSERT INTO application_settings (key, value) VALUES ('building_name', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (clean_name,),
        )
    return clean_name


def get_available_databases() -> list[dict[str, str]]:
    """Get list of available databases (monitoring_*.db files)."""
    databases = []
    seen_names = set()
    try:
        # Check for base monitoring.db
        if (BASE_DIR / "monitoring.db").exists():
            databases.append({"name": "Unknown Building", "filename": "monitoring.db", "path": str(BASE_DIR / "monitoring.db")})
            seen_names.add("Unknown Building")
        
        # Check for monitoring_*.db files
        for db_file in BASE_DIR.glob("monitoring_*.db"):
            # Extract building name from filename
            filename = db_file.name  # e.g., "monitoring_Building_1.db"
            building_name = filename.replace("monitoring_", "").replace(".db", "").replace("_", " ")
            # Skip duplicates
            if building_name not in seen_names:
                databases.append({"name": building_name, "filename": db_file.name, "path": str(db_file)})
                seen_names.add(building_name)
    except Exception:
        pass
    
    return sorted(databases, key=lambda x: x["name"])
