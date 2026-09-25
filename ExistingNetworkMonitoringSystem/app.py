import csv
import io

from flask import Flask, jsonify, make_response, render_template
from dashboard import get_dashboard_data
from monitoring import get_monitoring_data, get_throughput, poll_once, start_monitoring

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


@app.get("/api/throughput")
def throughput():
    return jsonify(get_throughput())


@app.get("/api/dataset.csv")
def dataset_csv():
    """Export persisted SNMP-MIB and ICMP observations for thesis analysis."""
    rows = get_monitoring_data()["telemetry"]
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=snmp_mib_monitoring_dataset.csv"
    return response


@app.get("/api/model-records.csv")
def model_records_csv():
    """Export the anomaly model's inference history separately from features."""
    rows = get_monitoring_data()["ml_records"]
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=model_records.csv"
    return response


if __name__ == "__main__":
    app.run(debug=True, port=5000)
