"""Export ICMP ping samples, reviewed conditions, and ping-rule records."""

import csv
import sqlite3
from pathlib import Path

from monitoring import initialize_database


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "monitoring.db"
DATASET_DIR = BASE_DIR / "datasets"


def export_table(connection: sqlite3.Connection, query: str, destination: Path) -> int:
    cursor = connection.execute(query)
    columns = [item[0] for item in cursor.description]
    rows = cursor.fetchall()
    with destination.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(columns)
        writer.writerows(rows)
    return len(rows)


def main() -> None:
    DATASET_DIR.mkdir(exist_ok=True)
    initialize_database()
    with sqlite3.connect(DATABASE_PATH) as connection:
        telemetry_count = export_table(
            connection,
            "SELECT telemetry.id, telemetry.recorded_at, telemetry.device_name, telemetry.target, telemetry.online, telemetry.ping_sent, telemetry.ping_received, telemetry.packet_loss, telemetry.latency_min_ms, telemetry.latency_median_ms, telemetry.latency_max_ms, telemetry.latency_readings, telemetry.anomaly_score, telemetry.anomaly_label, condition_labels.label AS reviewed_condition_label, telemetry.error FROM telemetry LEFT JOIN condition_labels ON condition_labels.telemetry_id = telemetry.id WHERE telemetry.protocol = 'icmp' AND ((telemetry.online = 1 AND telemetry.ping_received > 0 AND COALESCE(telemetry.latency_median_ms, telemetry.latency_ms) IS NOT NULL) OR (telemetry.online = 0 AND telemetry.ping_received = 0)) ORDER BY telemetry.id",
            DATASET_DIR / "ping_dataset.csv",
        )
        records_count = export_table(
            connection,
            "SELECT id, recorded_at, device_name, model_version, result, confidence, status FROM ml_records WHERE model_version = 'icmp-ping-v1' ORDER BY id",
            DATASET_DIR / "ping_model_records.csv",
        )
    print(f"Exported {telemetry_count} ping samples and {records_count} ping model records")


if __name__ == "__main__":
    main()