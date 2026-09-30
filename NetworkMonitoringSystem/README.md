# Ping Monitoring System

ICMP-only PC reachability and latency monitor built with Python, Flask, and PyWebView.

This sibling project does not modify or share a database with `NetworkMonitoringSystem`.

The system sends five ICMP echo requests per check and records reachability, packet loss, and minimum/median/maximum round-trip latency. It does not poll SNMP or HTTP and does not collect CPU, memory, or bandwidth metrics. Discovered hosts are not monitored until selected and added; monitoring is also inactive until started for that PC.

The monitoring worker also pings the detected local IPv4 gateway and a configurable external IPv4 reference (default `1.1.1.1`) on the monitoring cadence. ML Insights compares each PC with the gateway and external reference using rolling summaries of up to five samples (up to 25 echo requests): packet loss, median latency, and median absolute change between latency samples. The external target can be changed in Settings. ICMP comparisons help distinguish possible endpoint, local-path, and upstream patterns, but they cannot prove a cause; external hosts or firewalls may filter ping.

Reference samples are stored separately from monitored PCs and can be exported from `/api/network-references.csv`.

Windows may report sub-millisecond replies as `time<1ms`. These remain labeled `<1 ms`; numeric aggregates use the reported 1 ms upper bound, and the original reply strings are retained in the dataset.

## Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run the browser dashboard:

```powershell
python app.py
```

Open `http://127.0.0.1:5000`, choose **Monitor PCs**, and discover the suggested local subnet. Select responding PCs, add them, then start monitoring per PC. Discovery is restricted to a subnet within the active local IPv4 network and up to 256 addresses. Per-PC polling intervals are at least 5 seconds because each check sends five requests.

Ping records are available at `http://127.0.0.1:5000/api/dataset.csv`; model/rule decisions are at `http://127.0.0.1:5000/api/model-records.csv`.

The current database snapshot is also stored in `datasets/ping_dataset.csv` and `datasets/ping_model_records.csv`. Regenerate both files after collecting new observations:

```powershell
python export_dataset.py
```

The ping dataset contains target, timestamp, reachability, latency, packet loss, the legacy ping-rule result, and a separate `reviewed_condition_label` column for human-verified training labels.

## Machine-learning models

The **ML Insights** sidebar view includes three ICMP-only models:

- **Isolation Forest** learns a baseline from reviewed `Normal` samples and scores later samples for unusual ping behavior.
- **GRU** replaces LSTM and forecasts the next sample's median latency, packet loss, and reachability from the preceding 12 samples for the same PC. Its inputs include latency jitter and recent latency/loss trends, failure streak, and elapsed time because PC polling intervals can vary.
- **XGBoost** classifies reviewed ping conditions: `Normal`, `High Latency`, `Packet Loss`, and `Unreachable`. These are observed conditions, not inferred physical root causes.

Select **ML Insights** to review samples and save their condition labels. Labels are stored separately from the old rule-generated anomaly text. Use **Train models** to fit any model that meets its data threshold. Current minimums are 20 reviewed normal samples for Isolation Forest, 5 samples in each of at least two XGBoost classes, and 30 GRU sequence windows. These are startup gates, not guarantees of statistically strong models; collect more representative data for thesis evaluation.

Training evaluates XGBoost and GRU on later, time-ordered samples before saving final artifacts under `models/`. The UI reports XGBoost macro-F1 and GRU MAE/RMSE. Isolation Forest is trained only on reviewed normal samples; assess it against separately reviewed anomalies. Model artifacts and training status are local generated files and are not included in source control.

The ML Insights view provides advisory next-step checks with their model source and ping evidence. Selecting a check records the choice as pending; it does not execute network changes or retrain a model. After the administrator performs the check, record `Resolved`, `Not resolved`, or `Unknown`, plus any verified finding and notes. Review/export this feedback at `/api/ml/recommendation-feedback.csv`; feedback is not automatically used as a model label.

The GRU also produces forecast-derived risk indicators. **Bottleneck** is High when forecast latency is at least 150 ms and at least 3 of the last 5 latency samples meet that threshold; **congestion** is High when forecast latency is at least 150 ms and forecast packet loss is at least 20%; **failure** is High when forecast reachability is below 50% or forecast packet loss is at least 80%. Lower warning thresholds appear as Watch. These are transparent ping-based risk heuristics, not proof of a physical bottleneck or its cause.

This app does not collect bandwidth telemetry, so the GRU predicts ping latency, packet loss, and reachability, not bandwidth exhaustion. Start the app with the documented environment and open the ML Insights view after enough valid ping history has accumulated.