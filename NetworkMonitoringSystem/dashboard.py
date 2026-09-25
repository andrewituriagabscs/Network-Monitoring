from datetime import datetime

from monitoring import get_connection_info, get_monitoring_data


def _display_time(timestamp):
    if not timestamp:
        return "-"
    return timestamp[11:16] if len(timestamp) >= 16 else timestamp


def get_dashboard_data():
    """Build dashboard views from the latest persisted monitoring records."""
    monitoring = get_monitoring_data()
    devices = monitoring["devices"]
    telemetry = monitoring["telemetry"]
    ml_records = monitoring["ml_records"]
    alerts = monitoring["alerts"]
    latest_by_device = {}
    for sample in telemetry:
        latest_by_device.setdefault(sample["device_name"], sample)

    online_devices = [sample for sample in latest_by_device.values() if sample["online"]]
    latencies = [sample["latency_ms"] for sample in online_devices if sample["latency_ms"] is not None]
    average_latency = round(sum(latencies) / len(latencies), 1) if latencies else None
    health = "Good" if len(online_devices) == len(devices) else "Degraded" if online_devices else "Offline"
    latest_sample = telemetry[0] if telemetry else None

    display_records = [
        {"time": _display_time(row["recorded_at"]), "recorded_at": row["recorded_at"], "device": row["device_name"], "model": row["model_version"], "result": row["result"], "confidence": f"{round(row['confidence'] * 100)}%", "status": row["status"]}
        for row in ml_records[:20]
    ]
    display_alerts = [{"time": _display_time(row["recorded_at"]), "device": row["device_name"], "message": row["message"]} for row in alerts]
    anomalies = [{"device": row["device_name"], "type": row["result"], "confidence": f"{round(row['confidence'] * 100)}%", "time": _display_time(row["recorded_at"])} for row in ml_records if row["status"] == "Flagged"][:20]
    predictions = []
    for sample in latest_by_device.values():
        if sample["protocol"] == "snmp":
            metric = "CPU load" if sample.get("cpu_percent") is not None else "SNMP availability"
            confidence = "82%" if sample["online"] else "97%"
        else:
            metric = "ICMP latency" if sample["online"] else "ICMP reachability"
            confidence = "80%" if sample["online"] else "99%"
        predictions.append({"device": sample["device_name"], "protocol": sample["protocol"].upper(), "forecast": metric, "when": "Ping", "confidence": confidence})
    recommendations = [{"priority": "High", "action": f"Check {row['device_name']}", "reason": row["message"]} for row in alerts[:10]]
    if not recommendations:
        recommendations = [{"priority": "Low", "action": "Continue monitoring", "reason": "No active issues detected"}]
    monitor_devices = [
        {
            "device": sample["device_name"],
            "target": sample["target"],
            "protocol": sample["protocol"].upper(),
            "status": "Online" if sample["online"] else "Offline",
            "latency": f"{sample['latency_ms']} ms" if sample["latency_ms"] is not None else "-",
            "last_check": _display_time(sample["recorded_at"]),
        }
        for sample in latest_by_device.values()
    ]
    monitor_history = [
        {"time": sample["recorded_at"], "latency": sample["latency_ms"], "throughput": sample["throughput_kbps"], "send": sample["send_kbps"], "receive": sample["receive_kbps"], "online": bool(sample["online"]), "packet_loss": sample["packet_loss"]}
        for sample in reversed(telemetry)
    ]

    return {
        "title": "Network Monitoring Dashboard",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {"total_devices": len(devices), "active_alerts": len(alerts), "network_health": health, "bandwidth_usage": "N/A"},
        "metrics": [
            {"label": "Average Latency", "value": f"{average_latency} ms" if average_latency is not None else "N/A", "trend": "Live ping"},
            {"label": "Packet Loss", "value": f"{round(100 - (len(online_devices) / len(devices) * 100)) if devices else 0}%", "trend": "Latest poll"},
            {"label": "CPU Usage", "value": "N/A", "trend": "SNMP not configured"},
            {"label": "Memory Usage", "value": "N/A", "trend": "SNMP not configured"},
        ],
        "alerts": display_alerts,
        "ml_summary": {"model": "Connectivity Classifier", "version": "connectivity-v1", "accuracy": "Rule-based", "last_run": _display_time(latest_sample["recorded_at"]) if latest_sample else "-", "records_today": len(ml_records)},
        "ml_records": display_records,
        "anomalies": anomalies,
        "predictions": predictions,
        "root_causes": [{"incident": row["result"], "cause": "Device unreachable" if row["result"] == "Device unreachable" else "Connectivity or latency issue", "device": row["device_name"], "confidence": f"{round(row['confidence'] * 100)}%"} for row in ml_records if row["status"] == "Flagged"][:20],
        "recommendations": recommendations,
        "monitor_summary": {
            "online": len(online_devices),
            "total": len(devices),
            "events": len(telemetry),
            "status": "Connected" if telemetry else "Waiting for data",
            "last_check": _display_time(latest_sample["recorded_at"]) if latest_sample else "-",
            "devices": monitor_devices,
            "history": monitor_history,
            "connection": get_connection_info(),
        },
    }
