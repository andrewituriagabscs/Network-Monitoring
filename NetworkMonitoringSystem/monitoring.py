"""Device polling, persistence, and lightweight ML monitoring records."""

from __future__ import annotations

import json
import os
import platform
import re
import sqlite3
import subprocess
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "monitoring.db"
POLL_INTERVAL_SECONDS = int(os.getenv("MONITORING_POLL_SECONDS", "30"))

# Add devices here or provide a JSON file through MONITORING_DEVICES_FILE.
# Supported protocols: icmp, http, and snmp.
DEFAULT_DEVICES = [
    {"name": "Local machine", "target": "127.0.0.1", "type": "server", "protocol": "icmp"},
]

_db_lock = threading.Lock()
_worker: threading.Thread | None = None
_stop_event = threading.Event()
_last_network_bytes: tuple[int, int, float] | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_connection_info() -> dict[str, Any]:
    """Identify the active local network adapter without inspecting credentials."""
    candidates = []
    for name, stats in psutil.net_if_stats().items():
        if not stats.isup or stats.speed <= 0:
            continue
        addresses = psutil.net_if_addrs().get(name, [])
        has_ipv4 = any(address.family.name == "AF_INET" and not address.address.startswith("127.") for address in addresses)
        if not has_ipv4:
            continue
        lowered = name.lower()
        if any(token in lowered for token in ("wi-fi", "wifi", "wireless", "wlan")):
            connection_type = "Wi-Fi"
        elif any(token in lowered for token in ("ethernet", "eth", "lan")):
            connection_type = "Ethernet"
        else:
            connection_type = "Network"
        candidates.append({"type": connection_type, "interface": name, "speed": f"{stats.speed} Mbps"})
    return candidates[0] if candidates else {"type": "Unknown", "interface": "No active adapter", "speed": "-"}


def get_throughput() -> dict[str, float]:
    """Return current send/receive throughput in Kbps for active adapters."""
    global _last_network_bytes
    now = time.perf_counter()
    sent = 0
    received = 0
    active_names = {item["interface"] for item in [get_connection_info()]}
    for name, counters in psutil.net_io_counters(pernic=True).items():
        if name in active_names:
            sent += counters.bytes_sent
            received += counters.bytes_recv
    if _last_network_bytes is None:
        _last_network_bytes = (sent, received, now)
        return {"send_kbps": 0.0, "receive_kbps": 0.0, "throughput_kbps": 0.0}
    previous_sent, previous_received, previous_time = _last_network_bytes
    elapsed = max(now - previous_time, 0.001)
    _last_network_bytes = (sent, received, now)
    send_kbps = max(0.0, (sent - previous_sent) * 8 / elapsed / 1000)
    receive_kbps = max(0.0, (received - previous_received) * 8 / elapsed / 1000)
    return {"send_kbps": round(send_kbps, 1), "receive_kbps": round(receive_kbps, 1), "throughput_kbps": round(send_kbps + receive_kbps, 1)}


def _load_devices() -> list[dict[str, Any]]:
    path = os.getenv("MONITORING_DEVICES_FILE") or str(BASE_DIR / "devices.json")
    if not path:
        return DEFAULT_DEVICES
    try:
        with open(path, "r", encoding="utf-8") as device_file:
            devices = json.load(device_file)
        if not isinstance(devices, list):
            raise ValueError("device configuration must be a JSON list")
        return devices
    except (OSError, ValueError, json.JSONDecodeError):
        return DEFAULT_DEVICES


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
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
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recorded_at TEXT NOT NULL,
                device_name TEXT NOT NULL,
                message TEXT NOT NULL,
                severity TEXT NOT NULL,
                open INTEGER NOT NULL DEFAULT 1
            );
            """
        )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(telemetry)")}
        for column in ("send_kbps", "receive_kbps", "throughput_kbps"):
            if column not in columns:
                connection.execute(f"ALTER TABLE telemetry ADD COLUMN {column} REAL NOT NULL DEFAULT 0")


def _ping(target: str) -> dict[str, Any]:
    command = ["ping", "-n", "1", "-w", "1500", target] if platform.system() == "Windows" else ["ping", "-c", "1", "-W", "2", target]
    started = time.perf_counter()
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=4, check=False)
        output = f"{result.stdout}\n{result.stderr}"
        match = re.search(r"(?:time[=<]|Average = )\s*(\d+(?:\.\d+)?)\s*ms", output, re.IGNORECASE)
        online = result.returncode == 0
        return {"online": online, "latency_ms": float(match.group(1)) if match else round((time.perf_counter() - started) * 1000, 1) if online else None, "error": None if online else "No ping response"}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"online": False, "latency_ms": None, "error": str(error)}


def _http_check(url: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return {"online": 200 <= response.status < 400, "latency_ms": round((time.perf_counter() - started) * 1000, 1), "error": None}
    except (OSError, urllib.error.URLError) as error:
        return {"online": False, "latency_ms": None, "error": str(error)}


def _snmp_check(device: dict[str, Any]) -> dict[str, Any]:
    """Read common host metrics when pysnmp and a community string are configured."""
    try:
        from pysnmp.hlapi.v3arch.asyncio import CommunityData, ContextData, ObjectType, ObjectIdentity, SnmpEngine, UdpTransportTarget, get_cmd
    except ImportError:
        return {"online": False, "latency_ms": None, "error": "Install pysnmp for SNMP monitoring"}

    async def read_metrics():
        started = time.perf_counter()
        engine = SnmpEngine()
        target = await UdpTransportTarget.create((device["target"], int(device.get("port", 161))), timeout=2, retries=0)
        metric_oids = device.get("oids", {})
        oids = [ObjectType(ObjectIdentity(oid)) for oid in metric_oids.values()]
        if not oids:
            oids = [ObjectType(ObjectIdentity("1.3.6.1.2.1.1.3.0"))]
        error_indication, error_status, _, values = await get_cmd(engine, CommunityData(device.get("community", "public")), target, ContextData(), *oids)
        if error_indication or error_status:
            return {"online": False, "latency_ms": None, "error": str(error_indication or error_status)}
        metric_values = {name: float(value) for name, value in zip(metric_oids, values) if str(value).replace(".", "", 1).isdigit()}
        return {"online": True, "latency_ms": round((time.perf_counter() - started) * 1000, 1), "cpu_percent": metric_values.get("cpu"), "memory_percent": metric_values.get("memory"), "bandwidth_percent": metric_values.get("bandwidth"), "error": None}

    try:
        import asyncio
        return asyncio.run(read_metrics())
    except Exception as error:
        return {"online": False, "latency_ms": None, "error": str(error)}


def _collect_device(device: dict[str, Any]) -> dict[str, Any]:
    protocol = device.get("protocol", "ping").lower()
    target = str(device.get("target", ""))
    if protocol in ("icmp", "ping"):
        result = _ping(target)
    elif protocol == "http":
        result = _http_check(target)
    elif protocol == "snmp":
        result = _snmp_check(device)
    else:
        result = {"online": False, "latency_ms": None, "error": f"Unsupported protocol: {protocol}"}
    result.update({
        "recorded_at": _utc_now(),
        "device_name": device.get("name", target),
        "target": target,
        "device_type": device.get("type", "other"),
        "protocol": protocol,
        "packet_loss": 0 if result["online"] else 100,
        "cpu_percent": result.get("cpu_percent"),
        "memory_percent": result.get("memory_percent"),
        "bandwidth_percent": result.get("bandwidth_percent"),
    })
    return result


def _classify(sample: dict[str, Any]) -> tuple[str, float, str]:
    if not sample["online"]:
        return "Device unreachable", 0.99, "Flagged"
    if sample.get("latency_ms") and sample["latency_ms"] > 150:
        return "High latency", 0.92, "Flagged"
    return "Normal connectivity", 0.96, "Normal"


def poll_once() -> list[dict[str, Any]]:
    initialize_database()
    throughput = get_throughput()
    samples = [_collect_device(device) for device in _load_devices()]
    for sample in samples:
        sample.update(throughput)
    with _db_lock, _connect() as connection:
        for sample in samples:
            connection.execute(
                "INSERT INTO telemetry (recorded_at, device_name, target, device_type, protocol, online, latency_ms, packet_loss, cpu_percent, memory_percent, bandwidth_percent, send_kbps, receive_kbps, throughput_kbps, error) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sample["recorded_at"], sample["device_name"], sample["target"], sample["device_type"], sample["protocol"], int(sample["online"]), sample["latency_ms"], sample["packet_loss"], sample["cpu_percent"], sample["memory_percent"], sample["bandwidth_percent"], sample["send_kbps"], sample["receive_kbps"], sample["throughput_kbps"], sample["error"]),
            )
            result, confidence, status = _classify(sample)
            connection.execute(
                "INSERT INTO ml_records (recorded_at, device_name, model_version, result, confidence, status) VALUES (?, ?, ?, ?, ?, ?)",
                (sample["recorded_at"], sample["device_name"], "connectivity-v1", result, confidence, status),
            )
            if status == "Flagged":
                connection.execute(
                    "INSERT INTO alerts (recorded_at, device_name, message, severity) VALUES (?, ?, ?, ?)",
                    (sample["recorded_at"], sample["device_name"], result, "high" if not sample["online"] else "medium"),
                )
    return samples


def _poll_loop() -> None:
    while not _stop_event.is_set():
        try:
            poll_once()
        except Exception:
            pass
        _stop_event.wait(POLL_INTERVAL_SECONDS)


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


def get_monitoring_data() -> dict[str, Any]:
    initialize_database()
    with _db_lock, _connect() as connection:
        telemetry = [_row_dict(row) for row in connection.execute("SELECT * FROM telemetry ORDER BY id DESC LIMIT 100")]
        ml_records = [_row_dict(row) for row in connection.execute("SELECT * FROM ml_records ORDER BY id DESC LIMIT 50")]
        alerts = [_row_dict(row) for row in connection.execute("SELECT * FROM alerts WHERE open = 1 ORDER BY id DESC LIMIT 20")]
    return {"devices": _load_devices(), "telemetry": telemetry, "ml_records": ml_records, "alerts": alerts}
