"""Repeatable local benchmark for Phase 9 indexed incident list/detail queries."""

from __future__ import annotations

import sqlite3
from statistics import median
from time import perf_counter_ns


def measure(row_count: int, iterations: int = 500) -> tuple[float, float]:
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE incidents (
          incident_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, status TEXT NOT NULL,
          severity TEXT NOT NULL, created_at INTEGER NOT NULL, title TEXT NOT NULL
        );
        CREATE INDEX ix_incidents_org_status_created
          ON incidents (organization_id, status, created_at);
        CREATE TABLE timeline (
          entry_id TEXT PRIMARY KEY, incident_id TEXT NOT NULL, created_at INTEGER NOT NULL,
          safe_summary TEXT NOT NULL
        );
        CREATE INDEX ix_timeline_incident_created ON timeline (incident_id, created_at);
        """
    )
    incidents = [
        (
            f"incident-{index:05d}",
            "org-benchmark",
            "open" if index % 2 else "resolved",
            "high" if index % 3 else "medium",
            index,
            f"Safe incident {index}",
        )
        for index in range(row_count)
    ]
    connection.executemany("INSERT INTO incidents VALUES (?, ?, ?, ?, ?, ?)", incidents)
    connection.executemany(
        "INSERT INTO timeline VALUES (?, ?, ?, ?)",
        [
            (f"entry-{index:05d}", incident[0], index, "Safe timeline fact")
            for index, incident in enumerate(incidents)
        ],
    )
    list_samples: list[int] = []
    detail_samples: list[int] = []
    for index in range(iterations):
        started = perf_counter_ns()
        connection.execute(
            "SELECT * FROM incidents WHERE organization_id=? AND status=? "
            "ORDER BY created_at DESC LIMIT 51",
            ("org-benchmark", "open"),
        ).fetchall()
        list_samples.append(perf_counter_ns() - started)
        incident_id = f"incident-{index % row_count:05d}"
        started = perf_counter_ns()
        connection.execute("SELECT * FROM incidents WHERE incident_id=?", (incident_id,)).fetchone()
        connection.execute(
            "SELECT * FROM timeline WHERE incident_id=? ORDER BY created_at", (incident_id,)
        ).fetchall()
        detail_samples.append(perf_counter_ns() - started)
    connection.close()
    return median(list_samples) / 1_000_000, median(detail_samples) / 1_000_000


def main() -> None:
    print("scope: local SQLite indexed query comparison; not a production SLA")
    for rows in (100, 1_000):
        list_ms, detail_ms = measure(rows)
        print(f"rows={rows} list_median_ms={list_ms:.4f} detail_median_ms={detail_ms:.4f}")


if __name__ == "__main__":
    main()
