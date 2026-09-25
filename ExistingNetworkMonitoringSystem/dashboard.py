from datetime import datetime

from ml_models import get_training_readiness
from monitoring import get_ml_training_data, get_monitoring_data


def _display_time(timestamp):
    if not timestamp:
        return "-"
    return timestamp[11:16] if len(timestamp) >= 16 else timestamp


def get_dashboard_data():
    """Build the ping-only dashboard from persisted reachability samples."""
    monitoring = get_monitoring_data()
    devices = monitoring["devices"]
    telemetry = [sample for sample in monitoring["telemetry"] if sample["protocol"] == "icmp"]
    ml_records = monitoring["ml_records"]
    alerts = monitoring["alerts"]
    training_samples, training_labels = get_ml_training_data()
    training_readiness = get_training_readiness(training_samples, training_labels)
    trained_models = sum(
        model.get("state") == "trained"
        for model in training_readiness["models"].values()
    )
    latest_by_device = {}
    for sample in telemetry:
        latest_by_device.setdefault(sample["target"], sample)

    online_devices = [sample for sample in latest_by_device.values() if sample["online"]]
    latencies = [sample["latency_ms"] for sample in latest_by_device.values() if sample["latency_ms"] is not None]
    average_latency = round(sum(latencies) / len(latencies), 1) if latencies else None
    active_devices = [device for device in devices if device["active"]]
    health = "Waiting" if not active_devices else "Good" if len(online_devices) == len(active_devices) else "Degraded" if online_devices else "Offline"
    latest_sample = telemetry[0] if telemetry else None

    display_records = [
        {"time": _display_time(row["recorded_at"]), "recorded_at": row["recorded_at"], "device": row["device_name"], "model": row["model_version"], "result": row["result"], "confidence": f"{round(row['confidence'] * 100)}%", "status": row["status"]}
        for row in ml_records if row["model_version"] == "icmp-ping-v1"
    ]
    display_alerts = [{"time": _display_time(row["recorded_at"]), "device": row["device_name"], "message": row["message"]} for row in alerts]
    anomalies = [{"device": row["device_name"], "type": row["result"], "confidence": f"{round(row['confidence'] * 100)}%", "time": _display_time(row["recorded_at"])} for row in ml_records if row["model_version"] == "icmp-ping-v1" and row["status"] == "Flagged"][:20]
    monitor_devices = [
        {
            "id": device["id"],
            "device": sample["device_name"],
            "target": device["target"],
            "status": "Online" if sample["online"] else "Offline",
            "latency": sample.get("latency_median_display", "-"),
            "latency_min": sample.get("latency_min_display", "-"),
            "latency_max": sample.get("latency_max_display", "-"),
            "packet_loss": sample.get("packet_loss", 0),
            "ping_received": sample.get("ping_received", 0),
            "ping_sent": sample.get("ping_sent", 5),
            "last_check": _display_time(sample["recorded_at"]),
            "active": bool(device["active"]),
            "interval_seconds": device["interval_seconds"],
        }
        for device in devices
        for sample in [latest_by_device.get(device["target"], {"device_name": device["name"], "online": False, "latency_ms": None, "recorded_at": None})]
    ]
    monitor_history = [
        {"time": sample["recorded_at"], "device": sample["device_name"], "target": sample["target"], "latency": sample["latency_median_ms"] if sample["latency_median_ms"] is not None else sample["latency_ms"], "latency_min_display": sample["latency_min_display"], "latency_median_display": sample["latency_median_display"], "latency_max_display": sample["latency_max_display"], "ping_received": sample["ping_received"], "ping_sent": sample["ping_sent"], "online": bool(sample["online"]), "packet_loss": sample["packet_loss"]}
        for sample in reversed(telemetry)
    ]

    return {
        "title": "Ping Monitoring System",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {"total_devices": len(devices), "active_devices": len(active_devices), "active_alerts": len(alerts), "network_health": health},
        "metrics": [
            {"label": "Average Latency", "value": f"{average_latency} ms" if average_latency is not None else "N/A", "trend": "Live ping"},
            {"label": "Reachable", "value": f"{len(online_devices)} / {len(latest_by_device)}" if latest_by_device else "0", "trend": "Latest ping per PC"},
            {"label": "Monitoring", "value": str(len(active_devices)), "trend": "Selected PCs"},
            {"label": "Ping Samples", "value": str(len(telemetry)), "trend": "Recent records"},
        ],
        "alerts": display_alerts,
        "ml_summary": {
            "model": "Isolation Forest, GRU, XGBoost",
            "version": f"{trained_models}/3 trained",
            "valid_samples": training_readiness["telemetry_samples"],
            "labeled_samples": training_readiness["labeled_samples"],
        },
        "ml_records": display_records,
        "anomalies": anomalies,
        "monitor_summary": {
            "online": sum(1 for device in active_devices if latest_by_device.get(device["target"], {}).get("online")),
            "total": len(active_devices),
            "events": len(telemetry),
            "status": "Monitoring" if active_devices else "No PCs selected",
            "last_check": _display_time(latest_sample["recorded_at"]) if latest_sample else "-",
            "devices": monitor_devices,
            "history": monitor_history,
            "local_network": monitoring.get("local_network"),
        },
        "discovered_hosts": [],
    }
