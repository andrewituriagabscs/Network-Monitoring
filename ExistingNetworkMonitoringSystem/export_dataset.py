"""Export the existing SQLite telemetry and model records as thesis datasets."""

import csv
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "monitoring.db"
DATASET_DIR = BASE_DIR / "datasets"


def export_table(connection: sqlite3.Connection, table: str, destination: Path) -> int:
    cursor = connection.execute(f"SELECT * FROM {table} ORDER BY id")
    columns = [item[0] for item in cursor.description]
    rows = cursor.fetchall()
    with destination.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(columns)
        writer.writerows(rows)
    return len(rows)


def main() -> None:
    DATASET_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(DATABASE_PATH) as connection:
        telemetry_count = export_table(connection, "telemetry", DATASET_DIR / "snmp_mib_dataset.csv")
        records_count = export_table(connection, "ml_records", DATASET_DIR / "model_records.csv")
    print(f"Exported {telemetry_count} telemetry rows and {records_count} model records")


if __name__ == "__main__":
    main()