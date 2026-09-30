"""Train and persist ICMP anomaly, forecasting, and condition models."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
STATUS_PATH = MODEL_DIR / "training_status.json"
FEATURE_COLUMNS = (
    "online",
    "latency_min_ms",
    "latency_median_ms",
    "latency_max_ms",
    "packet_loss",
    "ping_received_ratio",
    "latency_jitter_ms",
    "latency_delta_ms",
    "packet_loss_delta_percent",
    "latency_trend_ms_per_minute",
    "failure_streak",
    "elapsed_seconds",
)
CONDITION_LABELS = ("Normal", "High Latency", "Packet Loss", "Unreachable")
SEQUENCE_LENGTH = 12
MIN_NORMAL_SAMPLES = 20
MIN_SAMPLES_PER_CLASS = 5
MIN_GRU_WINDOWS = 30


def _dependencies() -> dict[str, bool]:
    from importlib.util import find_spec

    return {
        "scikit-learn": find_spec("sklearn") is not None,
        "xgboost": find_spec("xgboost") is not None,
        "torch": find_spec("torch") is not None,
    }


def _features(sample: dict[str, Any], history: list[dict[str, Any]] | None = None):
    import numpy as np

    history = history or []
    sent = max(int(sample.get("ping_sent") or 5), 1)
    current_latency = sample.get("latency_median_ms") or sample.get("latency_ms")
    current_loss = float(sample.get("packet_loss") or 0)
    recent = history[-5:]
    prior_latencies = [
        float(row.get("latency_median_ms") or row.get("latency_ms"))
        for row in recent
        if row.get("latency_median_ms") is not None or row.get("latency_ms") is not None
    ]
    previous_latency = prior_latencies[-1] if prior_latencies else None
    previous_loss = float(recent[-1].get("packet_loss") or 0) if recent else None
    trend_rows = [
        row
        for row in recent + [sample]
        if row.get("latency_median_ms") is not None or row.get("latency_ms") is not None
    ]
    latency_trend = 0.0
    if len(trend_rows) >= 2:
        elapsed_minutes = _elapsed_seconds(
            trend_rows[0].get("recorded_at"), trend_rows[-1].get("recorded_at")
        ) / 60
        if elapsed_minutes > 0:
            first_latency = float(trend_rows[0].get("latency_median_ms") or trend_rows[0].get("latency_ms") or 0)
            last_latency = float(trend_rows[-1].get("latency_median_ms") or trend_rows[-1].get("latency_ms") or 0)
            latency_trend = (last_latency - first_latency) / elapsed_minutes
    failure_streak = 0
    if not bool(sample.get("online")):
        failure_streak = 1
        for row in reversed(history):
            if row.get("online"):
                break
            failure_streak += 1
    return np.asarray(
        [
            float(bool(sample.get("online"))),
            float(sample.get("latency_min_ms") or 0),
            float(sample.get("latency_median_ms") or sample.get("latency_ms") or 0),
            float(sample.get("latency_max_ms") or 0),
            current_loss,
            float(sample.get("ping_received") or 0) / sent,
            max(0.0, float(sample.get("latency_max_ms") or 0) - float(sample.get("latency_min_ms") or 0)),
            float(current_latency or 0) - previous_latency if previous_latency is not None else 0.0,
            current_loss - previous_loss if previous_loss is not None else 0.0,
            latency_trend,
            float(failure_streak),
            _elapsed_seconds(history[-1].get("recorded_at"), sample.get("recorded_at")) if history else 0.0,
        ],
        dtype="float32",
    )


def is_valid_ping_sample(sample: dict[str, Any]) -> bool:
    sent = int(sample.get("ping_sent") or 0)
    received = int(sample.get("ping_received") or 0)
    if sent < 1 or received < 0 or received > sent:
        return False
    if bool(sample.get("online")):
        return received > 0 and (sample.get("latency_median_ms") is not None or sample.get("latency_ms") is not None)
    return received == 0


def _save_status(results: dict[str, dict[str, Any]]) -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    previous = get_model_status()
    previous.update(results)
    STATUS_PATH.write_text(json.dumps(previous, indent=2), encoding="utf-8")


def get_model_status() -> dict[str, dict[str, Any]]:
    if not STATUS_PATH.exists():
        return {}
    try:
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def get_training_readiness(
    samples: list[dict[str, Any]], labels: dict[int, str]
) -> dict[str, Any]:
    samples = [sample for sample in samples if is_valid_ping_sample(sample)]
    valid_ids = {int(sample["id"]) for sample in samples}
    label_counts = Counter(label for sample_id, label in labels.items() if sample_id in valid_ids)
    normal_count = label_counts["Normal"]
    class_counts = {label: label_counts[label] for label in CONDITION_LABELS if label_counts[label]}
    sequence_windows = sum(
        max(0, len(rows) - SEQUENCE_LENGTH)
        for rows in _samples_by_device(samples).values()
    )
    return {
        "telemetry_samples": len(samples),
        "labeled_samples": sum(label_counts.values()),
        "label_counts": class_counts,
        "isolation_forest": {
            "ready": normal_count >= MIN_NORMAL_SAMPLES,
            "normal_samples": normal_count,
            "required_normal_samples": MIN_NORMAL_SAMPLES,
        },
        "xgboost": {
            "ready": len(class_counts) >= 2
            and min(class_counts.values(), default=0) >= MIN_SAMPLES_PER_CLASS,
            "required_classes": 2,
            "required_samples_per_class": MIN_SAMPLES_PER_CLASS,
        },
        "gru": {
            "ready": sequence_windows >= MIN_GRU_WINDOWS,
            "sequence_windows": sequence_windows,
            "required_sequence_windows": MIN_GRU_WINDOWS,
            "sequence_length": SEQUENCE_LENGTH,
        },
        "dependencies": _dependencies(),
        "models": get_model_status(),
    }


def _samples_by_device(samples: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in samples:
        grouped[str(sample.get("target") or sample.get("device_name") or "unknown")].append(sample)
    for rows in grouped.values():
        rows.sort(key=lambda row: (row.get("recorded_at") or "", int(row.get("id") or 0)))
    return grouped


def _feature_map(samples: list[dict[str, Any]]):
    import numpy as np

    vectors = {}
    for rows in _samples_by_device(samples).values():
        for index, row in enumerate(rows):
            vectors[int(row["id"])] = _features(row, rows[:index])
    return {sample_id: np.asarray(vector, dtype="float32") for sample_id, vector in vectors.items()}


def _result(state: str, **details: Any) -> dict[str, Any]:
    return {"state": state, **details}


def _train_isolation_forest(samples: list[dict[str, Any]], labels: dict[int, str]):
    baseline = [sample for sample in samples if labels.get(int(sample["id"])) == "Normal"]
    if len(baseline) < MIN_NORMAL_SAMPLES:
        return _result(
            "not_ready",
            reason=f"Label at least {MIN_NORMAL_SAMPLES} normal ping samples to build a baseline.",
            samples=len(baseline),
        )

    import joblib
    import numpy as np
    from sklearn.ensemble import IsolationForest

    feature_vectors = _feature_map(samples)
    features = np.vstack([feature_vectors[int(sample["id"])] for sample in baseline])
    model = IsolationForest(
        n_estimators=200,
        contamination="auto",
        random_state=42,
    )
    model.fit(features)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"model": model, "features": FEATURE_COLUMNS, "version": "isolation-forest-v2"},
        MODEL_DIR / "isolation_forest.joblib",
    )
    return _result("trained", samples=len(baseline), method="normal-baseline anomaly detection")


def _train_xgboost(samples: list[dict[str, Any]], labels: dict[int, str]):
    rows = [sample for sample in samples if int(sample["id"]) in labels]
    counts = Counter(labels[int(sample["id"])] for sample in rows)
    if len(counts) < 2 or min(counts.values(), default=0) < MIN_SAMPLES_PER_CLASS:
        return _result(
            "not_ready",
            reason=f"Provide at least {MIN_SAMPLES_PER_CLASS} reviewed examples in each of two or more conditions.",
            class_counts=dict(counts),
        )

    import joblib
    import numpy as np
    from sklearn.metrics import f1_score
    from xgboost import XGBClassifier

    feature_vectors = _feature_map(samples)
    rows.sort(key=lambda row: (row.get("recorded_at") or "", int(row.get("id") or 0)))
    classes = sorted(counts)
    class_to_id = {label: index for index, label in enumerate(classes)}
    split_at = max(1, int(len(rows) * 0.8))
    test_start = rows[split_at].get("recorded_at") or ""
    train_rows = [row for row in rows if (row.get("recorded_at") or "") < test_start]
    test_rows = [row for row in rows if (row.get("recorded_at") or "") >= test_start]
    train_classes = {labels[int(row["id"])] for row in train_rows}
    if len(train_classes) < 2 or not test_rows:
        return _result(
            "not_ready",
            reason="Need at least two conditions in the earlier training period and later test samples.",
            class_counts=dict(counts),
        )

    def make_estimator():
        return XGBClassifier(
            n_estimators=120,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="multi:softprob",
            num_class=len(classes),
            eval_metric="mlogloss",
            random_state=42,
            n_jobs=1,
        )

    train_x = np.vstack([feature_vectors[int(row["id"])] for row in train_rows])
    train_y = np.asarray([class_to_id[labels[int(row["id"])]] for row in train_rows])
    test_x = np.vstack([feature_vectors[int(row["id"])] for row in test_rows])
    test_y = np.asarray([class_to_id[labels[int(row["id"])]] for row in test_rows])
    evaluation_model = make_estimator()
    evaluation_model.fit(train_x, train_y)
    predictions = evaluation_model.predict(test_x)
    macro_f1 = float(f1_score(test_y, predictions, average="macro", zero_division=0))

    final_model = make_estimator()
    all_x = np.vstack([feature_vectors[int(row["id"])] for row in rows])
    all_y = np.asarray([class_to_id[labels[int(row["id"])]] for row in rows])
    final_model.fit(all_x, all_y)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": final_model,
            "features": FEATURE_COLUMNS,
            "classes": classes,
            "version": "xgboost-condition-v2",
        },
        MODEL_DIR / "xgboost_condition.joblib",
    )
    return _result(
        "trained",
        samples=len(rows),
        class_counts=dict(counts),
        temporal_test_samples=len(test_rows),
        temporal_test_start=test_start,
        temporal_test_macro_f1=round(macro_f1, 4),
    )


def _build_gru(torch, input_size: int, hidden_size: int = 24):
    from torch import nn

    class PingGRU(nn.Module):
        def __init__(self):
            super().__init__()
            self.recurrent = nn.GRU(input_size, hidden_size, batch_first=True)
            self.output = nn.Linear(hidden_size, 3)

        def forward(self, values):
            sequence, _ = self.recurrent(values)
            return self.output(sequence[:, -1, :])

    return PingGRU()


def _elapsed_seconds(previous: str | None, current: str | None) -> float:
    if not previous or not current:
        return 0.0
    try:
        first = datetime.fromisoformat(previous.replace("Z", "+00:00"))
        second = datetime.fromisoformat(current.replace("Z", "+00:00"))
        return max(0.0, min((second - first).total_seconds(), 3600.0))
    except ValueError:
        return 0.0


def _suggestions(item: dict[str, Any]) -> list[dict[str, Any]]:
    action_text = {
        "check_endpoint": "Check that the PC is powered on and connected to the network.",
        "check_gateway": "Ping the local gateway and compare its result with other monitored PCs.",
        "check_icmp_policy": "Verify that the PC and its firewall allow ICMP echo replies.",
        "compare_latency": "Compare this PC's recent latency with its baseline and the gateway.",
        "compare_packet_loss": "Repeat pings to this PC and the gateway, then compare packet loss across PCs.",
        "inspect_shared_path": "Check the shared router or network path if several PCs show the same degradation.",
        "continue_monitoring": "No strong anomaly signal is present; continue monitoring for a change.",
    }
    suggestions: dict[str, dict[str, Any]] = {}

    def add(action_id: str, model: str, evidence: str) -> None:
        suggestion = suggestions.setdefault(
            action_id,
            {
                "id": action_id,
                "action": action_text[action_id],
                "model_sources": [],
                "evidence": [],
            },
        )
        if model not in suggestion["model_sources"]:
            suggestion["model_sources"].append(model)
        if evidence not in suggestion["evidence"]:
            suggestion["evidence"].append(evidence)

    current = item["current"]
    if not current["online"]:
        add("check_endpoint", "ICMP observation", "The latest sample received no ping replies.")
        add("check_gateway", "ICMP observation", "Compare endpoint reachability with the local gateway.")
        add("check_icmp_policy", "ICMP observation", "A host or firewall may suppress ping replies.")

    anomaly = item.get("isolation_forest", {})
    if anomaly.get("state") == "ready" and anomaly.get("result") == "Anomaly":
        add("compare_latency", "Isolation Forest", "The ping feature pattern differs from the learned normal baseline.")

    condition = item.get("xgboost", {})
    if condition.get("state") == "ready":
        condition_name = condition.get("condition")
        if condition_name == "High Latency":
            add("compare_latency", "XGBoost", "The classifier predicts the High Latency condition.")
        elif condition_name == "Packet Loss":
            add("compare_packet_loss", "XGBoost", "The classifier predicts the Packet Loss condition.")
        elif condition_name == "Unreachable":
            add("check_endpoint", "XGBoost", "The classifier predicts the Unreachable condition.")
            add("check_gateway", "XGBoost", "Compare endpoint reachability with the local gateway.")

    forecast = item.get("gru", {})
    risks = forecast.get("risk_indicators", {}) if forecast.get("state") == "ready" else {}
    if risks.get("bottleneck") in ("High", "Watch"):
        add("compare_latency", "GRU", f"Forecast bottleneck risk is {risks['bottleneck']}.")
    if risks.get("congestion") in ("High", "Watch"):
        add("compare_packet_loss", "GRU", f"Forecast congestion-like risk is {risks['congestion']}.")
        add("inspect_shared_path", "GRU", "Compare other PCs before investigating a shared path.")
    if risks.get("failure") in ("High", "Watch"):
        add("check_gateway", "GRU", f"Forecast reachability/failure risk is {risks['failure']}.")
        add("check_endpoint", "GRU", "Confirm the PC remains powered on and connected.")

    if not suggestions:
        add("continue_monitoring", "System", "No trained model or current ping signal indicates an action is needed.")
    return list(suggestions.values())


def _train_gru(samples: list[dict[str, Any]]):
    import numpy as np

    sequences = []
    targets = []
    window_times = []
    for rows in _samples_by_device(samples).values():
        if len(rows) <= SEQUENCE_LENGTH:
            continue
        vectors = []
        for index, row in enumerate(rows):
            vectors.append(_features(row, rows[:index]))
        for index in range(SEQUENCE_LENGTH, len(rows)):
            sequences.append(vectors[index - SEQUENCE_LENGTH : index])
            target = rows[index]
            targets.append(
                [
                    float(target.get("latency_median_ms") or target.get("latency_ms") or 0),
                    float(target.get("packet_loss") or 0),
                    float(bool(target.get("online"))),
                ]
            )
            window_times.append(target.get("recorded_at") or "")

    if len(sequences) < MIN_GRU_WINDOWS:
        return _result(
            "not_ready",
            reason=f"Need at least {MIN_GRU_WINDOWS} chronological training windows; each window uses {SEQUENCE_LENGTH} prior samples from one PC.",
            sequence_windows=len(sequences),
        )

    import joblib
    import torch
    from sklearn.preprocessing import StandardScaler
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset

    order = sorted(range(len(sequences)), key=lambda index: (window_times[index], index))
    split_at = max(1, int(len(sequences) * 0.8))
    test_start = window_times[order[split_at]]
    train_indices = [index for index in order if window_times[index] < test_start]
    test_indices = [index for index in order if window_times[index] >= test_start]
    sequences = np.asarray(sequences, dtype="float32")
    targets = np.asarray(targets, dtype="float32")
    if not train_indices or not test_indices:
        return _result("not_ready", reason="Need later samples for a chronological test set.")

    train_x, test_x = sequences[train_indices], sequences[test_indices]
    train_y, test_y = targets[train_indices], targets[test_indices]
    input_scaler = StandardScaler().fit(train_x.reshape(-1, train_x.shape[-1]))
    target_scaler = StandardScaler().fit(train_y[:, :2])
    train_x = input_scaler.transform(train_x.reshape(-1, train_x.shape[-1])).reshape(train_x.shape)
    test_x_scaled = input_scaler.transform(test_x.reshape(-1, test_x.shape[-1])).reshape(test_x.shape)
    train_y_scaled = target_scaler.transform(train_y[:, :2])
    train_reachability = train_y[:, 2:3]

    torch.manual_seed(42)
    torch.set_num_threads(1)
    model = _build_gru(torch, train_x.shape[-1])
    optimizer = torch.optim.Adam(model.parameters(), lr=0.005)
    loss_function = nn.MSELoss()
    reachability_loss = nn.BCEWithLogitsLoss()
    dataset = TensorDataset(
        torch.from_numpy(train_x),
        torch.from_numpy(train_y_scaled.astype("float32")),
        torch.from_numpy(train_reachability.astype("float32")),
    )
    loader = DataLoader(dataset, batch_size=min(16, len(dataset)), shuffle=True)
    model.train()
    for _ in range(40):
        for batch_x, batch_y, batch_reachability in loader:
            optimizer.zero_grad()
            prediction = model(batch_x)
            loss = loss_function(prediction[:, :2], batch_y) + reachability_loss(
                prediction[:, 2:3], batch_reachability
            )
            loss.backward()
            optimizer.step()

    model.eval()
    with torch.no_grad():
        test_output = model(torch.from_numpy(test_x_scaled)).cpu().numpy()
    predicted = target_scaler.inverse_transform(test_output[:, :2])
    mae = np.mean(np.abs(predicted - test_y[:, :2]), axis=0)
    rmse = np.sqrt(np.mean(np.square(predicted - test_y[:, :2]), axis=0))
    reachability_probability = 1 / (1 + np.exp(-test_output[:, 2]))
    reachability_accuracy = float(
        np.mean((reachability_probability >= 0.5) == (test_y[:, 2] >= 0.5))
    )
    state = {key: value.detach().cpu() for key, value in model.state_dict().items()}
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "state_dict": state,
            "input_scaler": input_scaler,
            "target_scaler": target_scaler,
            "features": FEATURE_COLUMNS,
            "sequence_length": SEQUENCE_LENGTH,
            "hidden_size": 24,
            "version": "gru-ping-forecast-v3",
        },
        MODEL_DIR / "gru_forecast.joblib",
    )
    return _result(
        "trained",
        sequence_windows=len(sequences),
        temporal_test_windows=len(test_x),
        temporal_test_start=test_start,
        latency_mae_ms=round(float(mae[0]), 4),
        packet_loss_mae_percent=round(float(mae[1]), 4),
        latency_rmse_ms=round(float(rmse[0]), 4),
        packet_loss_rmse_percent=round(float(rmse[1]), 4),
        reachability_accuracy=round(reachability_accuracy, 4),
    )


def train_models(
    samples: list[dict[str, Any]], labels: dict[int, str]
) -> dict[str, dict[str, Any]]:
    samples = [sample for sample in samples if is_valid_ping_sample(sample)]
    valid_ids = {int(sample["id"]) for sample in samples}
    labels = {sample_id: label for sample_id, label in labels.items() if sample_id in valid_ids}
    dependencies = _dependencies()
    results: dict[str, dict[str, Any]] = {}
    trainers = {
        "isolation_forest": (_train_isolation_forest, ("scikit-learn",)),
        "gru": (_train_gru, ("scikit-learn", "torch")),
        "xgboost": (_train_xgboost, ("scikit-learn", "xgboost")),
    }
    for name, (trainer, required) in trainers.items():
        missing = [package for package in required if not dependencies[package]]
        if missing:
            results[name] = _result("dependency_missing", packages=missing)
            continue
        try:
            results[name] = trainer(samples, labels) if name != "gru" else trainer(samples)
        except Exception as error:
            results[name] = _result("failed", reason=f"{type(error).__name__}: {error}")
    _save_status(results)
    return results


def get_ml_insights(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    valid_samples = [sample for sample in samples if is_valid_ping_sample(sample)]
    devices = _samples_by_device(valid_samples)
    artifacts = {
        "isolation_forest": MODEL_DIR / "isolation_forest.joblib",
        "xgboost": MODEL_DIR / "xgboost_condition.joblib",
        "gru": MODEL_DIR / "gru_forecast.joblib",
    }
    results = []
    for target, rows in devices.items():
        latest = rows[-1]
        item: dict[str, Any] = {
            "telemetry_id": int(latest["id"]),
            "target": target,
            "device_name": latest.get("device_name", target),
            "recorded_at": latest.get("recorded_at"),
            "current": {
                "online": bool(latest.get("online")),
                "latency_median_ms": latest.get("latency_median_ms") or latest.get("latency_ms"),
                "packet_loss": latest.get("packet_loss", 0),
            },
            "isolation_forest": {"state": "not_trained"},
            "xgboost": {"state": "not_trained"},
            "gru": {"state": "not_trained"},
        }
        if artifacts["isolation_forest"].exists():
            try:
                import joblib

                artifact = joblib.load(artifacts["isolation_forest"])
                if artifact.get("version") != "isolation-forest-v2":
                    item["isolation_forest"] = {"state": "retrain_required"}
                else:
                    features = _features(latest, rows[:-1]).reshape(1, -1)
                    score = float(artifact["model"].decision_function(features)[0])
                    item["isolation_forest"] = {
                        "state": "ready",
                        "result": "Anomaly" if score < 0 else "Normal",
                        "anomaly_score": round(-score, 5),
                    }
            except Exception as error:
                item["isolation_forest"] = {"state": "error", "reason": str(error)}
        if artifacts["xgboost"].exists():
            try:
                import joblib

                artifact = joblib.load(artifacts["xgboost"])
                if artifact.get("version") != "xgboost-condition-v2":
                    item["xgboost"] = {"state": "retrain_required"}
                else:
                    features = _features(latest, rows[:-1]).reshape(1, -1)
                    probabilities = artifact["model"].predict_proba(features)[0]
                    class_index = int(probabilities.argmax())
                    item["xgboost"] = {
                        "state": "ready",
                        "condition": artifact["classes"][class_index],
                        "confidence": round(float(probabilities[class_index]), 4),
                    }
            except Exception as error:
                item["xgboost"] = {"state": "error", "reason": str(error)}
        if artifacts["gru"].exists():
            try:
                import joblib
                import numpy as np
                import torch

                artifact = joblib.load(artifacts["gru"])
                if artifact.get("version") != "gru-ping-forecast-v3":
                    item["gru"] = {"state": "retrain_required"}
                    sequence_length = 0
                else:
                    sequence_length = int(artifact["sequence_length"])
                if item["gru"].get("state") == "retrain_required":
                    pass
                elif len(rows) < sequence_length:
                    item["gru"] = {
                        "state": "not_enough_history",
                        "required_samples": sequence_length,
                    }
                else:
                    first_index = len(rows) - sequence_length
                    vectors = [
                        _features(row, rows[:index])
                        for index, row in enumerate(rows[first_index:], start=first_index)
                    ]
                    values = np.asarray(vectors, dtype="float32")
                    scaled = artifact["input_scaler"].transform(values)[None, :, :]
                    model = _build_gru(torch, scaled.shape[-1], int(artifact["hidden_size"]))
                    model.load_state_dict(artifact["state_dict"])
                    model.eval()
                    with torch.no_grad():
                        prediction = model(torch.from_numpy(scaled)).cpu().numpy()
                    forecast = artifact["target_scaler"].inverse_transform(prediction[:, :2])[0]
                    reachability_probability = float(
                        1 / (1 + np.exp(-np.clip(prediction[0, 2], -60, 60)))
                    )
                    next_latency = round(max(0.0, float(forecast[0])), 3)
                    next_packet_loss = round(min(100.0, max(0.0, float(forecast[1]))), 2)
                    recent_latencies = [
                        float(row.get("latency_median_ms") or row.get("latency_ms"))
                        for row in rows[-5:]
                        if row.get("latency_median_ms") is not None or row.get("latency_ms") is not None
                    ]
                    sustained_high_latency = sum(value >= 150 for value in recent_latencies) >= 3
                    bottleneck_level = (
                        "High" if next_latency >= 150 and sustained_high_latency
                        else "Watch" if next_latency >= 150 or sustained_high_latency
                        else "Low"
                    )
                    congestion_level = (
                        "High" if next_latency >= 150 and next_packet_loss >= 20
                        else "Watch" if next_latency >= 100 or next_packet_loss >= 10
                        else "Low"
                    )
                    failure_level = (
                        "High" if reachability_probability < 0.5 or next_packet_loss >= 80
                        else "Watch" if reachability_probability < 0.8 or next_packet_loss >= 40
                        else "Low"
                    )
                    item["gru"] = {
                        "state": "ready",
                        "next_latency_ms": next_latency,
                        "next_packet_loss_percent": next_packet_loss,
                        "next_reachability_probability": round(reachability_probability, 4),
                        "risk_indicators": {
                            "bottleneck": bottleneck_level,
                            "congestion": congestion_level,
                            "failure": failure_level,
                        },
                    }
            except Exception as error:
                item["gru"] = {"state": "error", "reason": str(error)}
        item["suggestions"] = _suggestions(item)
        results.append(item)
    return results