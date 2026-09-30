import csv
import io
import json

import ipaddress

from flask import Flask, jsonify, make_response, render_template, request
from dashboard import get_dashboard_data
from ml_models import CONDITION_LABELS, get_ml_insights, get_training_readiness, is_valid_ping_sample, train_models
from monitoring import add_monitored_device, discover_hosts, get_local_network, get_ml_labeling_samples, get_ml_training_data, get_monitoring_data, get_network_reference_samples, get_network_reference_status, get_recommendation_feedback, poll_network_references, poll_once, remove_monitored_device, save_condition_label, save_external_reference_target, save_recommendation_outcome, save_recommendation_selection, start_monitoring, update_monitored_device

app = Flask(__name__, static_folder="static", template_folder="templates")
start_monitoring()


@app.route("/")
def index():
    data = get_dashboard_data()
    return render_template("dashboard.html", **data)


@app.post("/api/monitor-now")
def monitor_now():
    return jsonify({"samples": poll_once()})


@app.get("/api/status")
def status():
    return jsonify(get_monitoring_data())


@app.get("/api/ml/status")
def ml_status():
    samples, labels = get_ml_training_data()
    return jsonify(get_training_readiness(samples, labels))


@app.get("/api/network-references")
def network_references():
    return jsonify(get_network_reference_status())


@app.post("/api/network-references/poll")
def poll_network_reference_targets():
    poll_network_references()
    return jsonify(get_network_reference_status())


@app.get("/api/network-references.csv")
def network_reference_csv():
    rows = get_network_reference_samples()
    output = io.StringIO()
    fields = (
        "id", "recorded_at", "reference_kind", "reference_name", "target", "online",
        "latency_ms", "latency_min_ms", "latency_median_ms", "latency_max_ms",
        "packet_loss", "ping_sent", "ping_received", "latency_readings",
    )
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    if rows:
        writer.writerows(rows)
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=network_reference_ping_data.csv"
    return response


@app.patch("/api/settings/external-reference")
def update_external_reference():
    payload = request.get_json(silent=True) or {}
    try:
        target = save_external_reference_target(payload.get("target"))
    except (AttributeError, TypeError, ValueError) as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"ok": True, "target": target})


@app.get("/api/ml/insights")
def ml_insights():
    samples, _ = get_ml_training_data()
    return jsonify({"devices": get_ml_insights(samples)})


@app.get("/api/ml/labels")
def ml_labels():
    return jsonify({"labels": list(CONDITION_LABELS), "samples": get_ml_labeling_samples()})


@app.put("/api/ml/labels/<int:telemetry_id>")
def ml_label(telemetry_id: int):
    payload = request.get_json(silent=True) or {}
    label = payload.get("label")
    if label not in CONDITION_LABELS:
        return jsonify({"error": "Choose Normal, High Latency, Packet Loss, or Unreachable"}), 400
    if not save_condition_label(telemetry_id, label):
        return jsonify({"error": "Valid ICMP sample not found"}), 404
    return jsonify({"ok": True, "telemetry_id": telemetry_id, "label": label})


@app.post("/api/ml/train")
def train_ml_models():
    samples, labels = get_ml_training_data()
    results = train_models(samples, labels)
    return jsonify({"models": results, "readiness": get_training_readiness(samples, labels)})


@app.get("/api/ml/recommendation-feedback")
def ml_recommendation_feedback():
    return jsonify({"feedback": get_recommendation_feedback()})


@app.post("/api/ml/recommendation-feedback/<int:telemetry_id>")
def select_ml_recommendation(telemetry_id: int):
    payload = request.get_json(silent=True) or {}
    suggestion_id = payload.get("suggestion_id")
    samples, _ = get_ml_training_data()
    insight = next(
        (item for item in get_ml_insights(samples) if item["telemetry_id"] == telemetry_id),
        None,
    )
    if not insight:
        return jsonify({"error": "Current valid ICMP sample not found"}), 404
    suggestion = next(
        (item for item in insight["suggestions"] if item["id"] == suggestion_id),
        None,
    )
    if not suggestion:
        return jsonify({"error": "That suggestion is not available for this sample"}), 400
    feedback_id = save_recommendation_selection(
        telemetry_id, insight["target"], suggestion
    )
    if feedback_id is None:
        return jsonify({"error": "ICMP sample is no longer available"}), 404
    return jsonify({"ok": True, "feedback_id": feedback_id, "outcome": "pending"}), 201


@app.patch("/api/ml/recommendation-feedback/<int:feedback_id>")
def update_ml_recommendation_feedback(feedback_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        updated = save_recommendation_outcome(
            feedback_id,
            payload.get("outcome", ""),
            payload.get("verified_finding", ""),
            payload.get("notes", ""),
        )
    except (AttributeError, TypeError, ValueError) as error:
        return jsonify({"error": str(error)}), 400
    if not updated:
        return jsonify({"error": "Selected recommendation not found"}), 404
    return jsonify({"ok": True, "feedback_id": feedback_id})


@app.get("/api/ml/recommendation-feedback.csv")
def ml_recommendation_feedback_csv():
    rows = get_recommendation_feedback()
    output = io.StringIO()
    fields = (
        "id", "telemetry_id", "recorded_at", "selected_at", "outcome_at",
        "device_name", "target", "model_sources", "evidence", "suggestion_id",
        "suggested_action", "outcome", "verified_finding", "notes",
    )
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({
            **row,
            "model_sources": json.dumps(row["model_sources"]),
            "evidence": json.dumps(row["evidence"]),
        })
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=recommendation_feedback.csv"
    return response


@app.get("/api/devices")
def devices():
    return jsonify({"devices": get_monitoring_data()["devices"], "local_network": get_local_network()})


@app.post("/api/discover")
def discover():
    payload = request.get_json(silent=True) or {}
    try:
        subnet = payload.get("subnet") or get_local_network()["subnet"]
        return jsonify({"hosts": discover_hosts(subnet)})
    except (ValueError, ipaddress.AddressValueError) as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/devices")
def add_devices():
    payload = request.get_json(silent=True) or {}
    selected = payload.get("devices", [])
    if not isinstance(selected, list):
        return jsonify({"error": "devices must be a list"}), 400
    try:
        local_network = ipaddress.ip_network(get_local_network()["subnet"], strict=False)
        added = []
        for device in selected[:256]:
            address = ipaddress.ip_address(device["target"])
            if address not in local_network:
                raise ValueError(f"{address} is outside the active local network")
            added.append(add_monitored_device(str(device.get("name", address)), str(address)))
        return jsonify({"devices": added}), 201
    except (KeyError, TypeError, ValueError) as error:
        return jsonify({"error": str(error)}), 400


@app.patch("/api/devices/<int:device_id>")
def update_device(device_id):
    payload = request.get_json(silent=True) or {}
    if "active" not in payload and "interval_seconds" not in payload:
        return jsonify({"error": "provide active or interval_seconds"}), 400
    try:
        updated = update_monitored_device(device_id, active=payload.get("active"), interval_seconds=payload.get("interval_seconds"))
    except (TypeError, ValueError) as error:
        return jsonify({"error": str(error)}), 400
    return (jsonify({"ok": True}) if updated else (jsonify({"error": "device not found"}), 404))


@app.delete("/api/devices/<int:device_id>")
def delete_device(device_id):
    removed = remove_monitored_device(device_id)
    return (jsonify({"ok": True}) if removed else (jsonify({"error": "device not found"}), 404))


@app.get("/api/dataset.csv")
def dataset_csv():
    """Export persisted ICMP ping observations for thesis analysis."""
    samples, labels = get_ml_training_data()
    rows = [
        {**sample, "reviewed_condition_label": labels.get(int(sample["id"]), "")}
        for sample in samples
        if is_valid_ping_sample(sample)
    ]
    output = io.StringIO()
    fields = ("id", "recorded_at", "device_name", "target", "online", "ping_sent", "ping_received", "packet_loss", "latency_min_ms", "latency_median_ms", "latency_max_ms", "latency_readings", "latency_min_display", "latency_median_display", "latency_max_display", "anomaly_score", "anomaly_label", "reviewed_condition_label", "error")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    if rows:
        writer.writerows(rows)
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=ping_dataset.csv"
    return response


@app.get("/api/model-records.csv")
def model_records_csv():
    """Export the anomaly model's inference history separately from features."""
    rows = get_monitoring_data()["ml_records"]
    output = io.StringIO()
    fields = ("id", "recorded_at", "device_name", "model_version", "result", "confidence", "status")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    if rows:
        writer.writerows(rows)
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=ping_model_records.csv"
    return response


if __name__ == "__main__":
    app.run(debug=True, port=5000)
