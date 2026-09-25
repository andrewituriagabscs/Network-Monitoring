import threading
import time
import urllib.request
import os
import logging

from flask import cli as flask_cli
from app import app

try:
    import webview
except ImportError:
    webview = None

def run_flask_app(port):
    # Prefer a quiet production-ready WSGI server (waitress) to avoid console banner/logs.
    try:
        from waitress import serve

        # waitress does not print the Flask/Werkzeug startup banner
        logging.getLogger("waitress.queue").setLevel(logging.ERROR)
        serve(app, host="127.0.0.1", port=port, threads=8)
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
            app.run(debug=False, port=port, use_reloader=False)
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
    port = int(os.getenv("NETWORK_MONITOR_PORT", "5000"))
    url = f"http://127.0.0.1:{port}/"
    thread = threading.Thread(target=run_flask_app, args=(port,), daemon=True)
    thread.start()

    if not wait_for_server(url, timeout=10):
        print("Failed to start the local server.")
        return

    if webview is None:
        raise RuntimeError("pywebview is required for the Windows desktop app. Install it with 'pip install pywebview'.")

    webview.create_window("Ping Monitoring Dashboard", url, width=1100, height=800)
    webview.start()


if __name__ == "__main__":
    main()
