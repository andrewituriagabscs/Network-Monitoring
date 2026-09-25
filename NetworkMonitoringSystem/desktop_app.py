import threading
import time
import urllib.request
import os
import logging

from flask import Flask, jsonify, render_template
from flask import cli as flask_cli
from dashboard import get_dashboard_data
from monitoring import get_monitoring_data, get_throughput, poll_once, start_monitoring

try:
    import webview
except ImportError:
    webview = None

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


def run_flask_app():
    # Prefer a quiet production-ready WSGI server (waitress) to avoid console banner/logs.
    try:
        from waitress import serve

        # waitress does not print the Flask/Werkzeug startup banner
        logging.getLogger("waitress.queue").setLevel(logging.ERROR)
        serve(app, host="127.0.0.1", port=5000, threads=8)
        return
    except Exception:
        # If waitress is not available, fall back to Flask's server but suppress logs
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        logging.getLogger('flask.app').setLevel(logging.ERROR)
        app.logger.disabled = True
        try:
            flask_cli.show_server_banner = lambda *args, **kwargs: None
        except Exception:
            pass

        # Redirect stdout/stderr to null while starting the server to hide startup messages
        devnull = open(os.devnull, 'w')
        _stdout = os.dup(1)
        _stderr = os.dup(2)
        try:
            os.dup2(devnull.fileno(), 1)
            os.dup2(devnull.fileno(), 2)
            app.run(debug=False, port=5000, use_reloader=False)
        finally:
            os.dup2(_stdout, 1)
            os.dup2(_stderr, 2)
            devnull.close()


def wait_for_server(url, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def main():
    url = "http://127.0.0.1:5000/"
    thread = threading.Thread(target=run_flask_app, daemon=True)
    thread.start()

    if not wait_for_server(url, timeout=10):
        print("Failed to start the local server.")
        return

    if webview is None:
        raise RuntimeError("pywebview is required for the Windows desktop app. Install it with 'pip install pywebview'.")

    webview.create_window("Network Monitoring Dashboard", url, width=1100, height=800)
    webview.start()


if __name__ == "__main__":
    main()
