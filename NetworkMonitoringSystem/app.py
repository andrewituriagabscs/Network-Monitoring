from flask import Flask, jsonify, render_template
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
