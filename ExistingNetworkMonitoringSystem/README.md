# Existing Network Monitoring System

Paper-inspired SNMP-MIB anomaly monitoring application built with Python, Flask, and PyWebView.

This is a separate comparison system. It does not modify or share the database with `NetworkMonitoringSystem`.

The system collects active ICMP reachability and latency, polls standard IF-MIB counters through SNMP, converts octet counters into rates, stores feature rows in SQLite, and records anomaly decisions as `mib-anomaly-v1`. The implementation is a reproducible feature-based baseline inspired by the 2021 paper; it is not a claim to reproduce the paper's private training dataset or stacked autoencoder.

## Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy `devices.example.json` to `devices.json` and configure the devices to monitor.

Run the browser dashboard:

```powershell
python app.py
```

Open `http://127.0.0.1:5000`. Download the persisted dataset from `http://127.0.0.1:5000/api/dataset.csv`.

The current database snapshot is also stored in `datasets/snmp_mib_dataset.csv` and `datasets/model_records.csv`. Regenerate both files after collecting new observations:

```powershell
python export_dataset.py
```

The feature dataset contains telemetry and anomaly labels. The model-record dataset contains each inference timestamp, model version, result, confidence, and status.

For SNMP devices, replace the target, community, and interface index in `devices.json`. The example uses IF-MIB counters for interface index `1`; use the index that exists on your device.