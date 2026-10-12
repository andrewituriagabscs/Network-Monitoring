import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import ml_models


class ClassifierComparisonTest(unittest.TestCase):
    def test_compares_three_classifiers_on_the_same_temporal_holdout(self):
        samples = []
        labels = {}
        conditions = (
            ("Normal", True, 5, 0.0, 12.0),
            ("High Latency", True, 5, 0.0, 220.0),
            ("Packet Loss", True, 2, 60.0, 80.0),
            ("Unreachable", False, 0, 100.0, None),
        )
        record_id = 1
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)

        for step in range(20):
            recorded_at = (start + timedelta(minutes=step)).isoformat()
            for label, online, received, loss, latency in conditions:
                samples.append(
                    {
                        "id": record_id,
                        "recorded_at": recorded_at,
                        "device_name": label,
                        "target": label,
                        "online": online,
                        "ping_sent": 5,
                        "ping_received": received,
                        "packet_loss": loss,
                        "latency_ms": latency,
                        "latency_min_ms": latency,
                        "latency_median_ms": latency,
                        "latency_max_ms": latency,
                    }
                )
                labels[record_id] = label
                record_id += 1

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(ml_models, "MODEL_DIR", Path(directory)):
                result = ml_models._train_xgboost(samples, labels)

            self.assertEqual(result["state"], "trained")
            comparison = result["classifier_comparison"]
            self.assertEqual(comparison["train_samples"], 64)
            self.assertEqual(comparison["test_samples"], 16)
            self.assertEqual(
                set(comparison["models"]),
                {"xgboost", "logistic_regression", "random_forest"},
            )
            self.assertEqual(
                set(comparison["models"]["xgboost"]["per_class"]),
                {condition[0] for condition in conditions},
            )
            self.assertEqual(
                {path.name for path in Path(directory).iterdir()},
                {"xgboost_condition.joblib"},
            )


if __name__ == "__main__":
    unittest.main()