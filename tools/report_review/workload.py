"""Deterministic ClickHouse activity for data-rich snapshot review reports."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, Iterator

from clickhouse_driver import Client

from .config import ReviewConfig


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class WorkloadError(RuntimeError):
    """The disposable review workload could not be prepared or executed."""


class ReviewWorkload:
    """Own a dedicated database and generate activity during snapshot cases."""

    def __init__(self, config: ReviewConfig) -> None:
        self.config = config
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._run_summary: dict[str, Any] | None = None
        self._log_path: Path | None = None
        for label, value in (
            ("workload.database", config.workload.database),
            ("database.cluster_name", config.database.cluster_name),
        ):
            if not _IDENTIFIER.fullmatch(value):
                raise WorkloadError(f"{label} must be a simple ClickHouse identifier")

    def _client(self, *, name: str) -> Client:
        database = self.config.database
        return Client(
            host=database.host,
            port=database.port,
            database="default",
            user=database.user,
            password=os.environ.get(database.password_env, ""),
            client_name=name,
            connect_timeout=5,
            send_receive_timeout=30,
            settings={
                "log_queries": 1,
                "log_query_threads": 1,
                "max_threads": 2,
            },
        )

    def prepare(self) -> dict[str, Any]:
        """Recreate and seed the dedicated database before the matrix starts."""
        if not self.config.workload.enabled:
            return {"enabled": False, "prepared": False}
        name = self.config.workload.database
        cluster = self.config.database.cluster_name
        client = self._client(name="ch_diag report review setup")
        started = time.monotonic()
        try:
            client.execute(f"DROP DATABASE IF EXISTS {name} ON CLUSTER {cluster} SYNC")
            client.execute(f"CREATE DATABASE {name} ON CLUSTER {cluster}")
            client.execute(
                f"""
                CREATE TABLE {name}.events ON CLUSTER {cluster}
                (
                    id UInt64,
                    event_time DateTime,
                    category LowCardinality(String),
                    payload String,
                    value Float64
                )
                ENGINE = ReplicatedMergeTree(
                    '/clickhouse/tables/{{shard}}/{name}/events',
                    '{{replica}}'
                )
                PARTITION BY toDate(event_time)
                ORDER BY (category, event_time, id)
                """
            )
            client.execute(
                f"""
                CREATE TABLE {name}.distributed_events ON CLUSTER {cluster}
                AS {name}.events
                ENGINE = Distributed({cluster}, {name}, events, cityHash64(id))
                """
            )
            client.execute(
                self._insert_query(name),
                {"offset": 0, "rows": self.config.workload.seed_rows},
            )
            client.execute(f"SYSTEM FLUSH DISTRIBUTED {name}.distributed_events")
            client.execute("SYSTEM FLUSH LOGS")
            rows = client.execute(f"SELECT count() FROM {name}.distributed_events")[0][0]
        except Exception as exc:
            raise WorkloadError(f"cannot prepare review workload: {exc}") from exc
        finally:
            client.disconnect()
        summary = {
            "enabled": True,
            "prepared": True,
            "database": name,
            "seed_rows_requested": self.config.workload.seed_rows,
            "visible_rows": int(rows),
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
        print(
            f"WORKLOAD READY database={name} rows={summary['visible_rows']}",
            flush=True,
        )
        return summary

    @staticmethod
    def _insert_query(database: str) -> str:
        return f"""
            INSERT INTO {database}.distributed_events
            SELECT
                number + %(offset)s AS id,
                now() - toIntervalSecond(number %% 3600) AS event_time,
                concat('category-', toString(number %% 32)) AS category,
                repeat(hex(cityHash64(number + %(offset)s)), 8) AS payload,
                sin(number + %(offset)s) AS value
            FROM numbers(%(rows)s)
            SETTINGS insert_distributed_sync = 1
        """

    def _write_log(self, message: str) -> None:
        if self._log_path is None:
            return
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with self._log_path.open("a", encoding="utf-8") as stream:
            stream.write(f"{timestamp} {message}\n")

    def _run(self) -> None:
        assert self._run_summary is not None
        workload = self.config.workload
        name = workload.database
        client = self._client(name="ch_diag report review workload")
        iteration = 0
        next_deadline = time.monotonic()
        try:
            while not self._stop.is_set():
                offset = time.time_ns() // 1000 + iteration * workload.insert_rows_per_batch
                try:
                    client.execute(
                        self._insert_query(name),
                        {"offset": offset, "rows": workload.insert_rows_per_batch},
                    )
                    self._run_summary["inserted_rows"] += workload.insert_rows_per_batch
                    client.execute(
                        f"""
                        SELECT
                            sum(cityHash64(payload)),
                            uniqExact(category),
                            avg(value)
                        FROM {name}.distributed_events
                        WHERE id % 7 != 3
                        SETTINGS max_threads = 2
                        """
                    )
                    client.execute(
                        "SELECT sum(cityHash64(number)) FROM numbers(%(rows)s) "
                        "SETTINGS max_threads = 2",
                        {"rows": workload.cpu_numbers_per_query},
                    )
                    self._run_summary["successful_cycles"] += 1
                    if iteration % workload.failed_query_every == 0:
                        try:
                            client.execute(f"SELECT * FROM {name}.expected_missing_table")
                        except Exception:
                            self._run_summary["intentional_failures"] += 1
                except Exception as exc:
                    self._run_summary["errors"] += 1
                    self._run_summary["last_error"] = str(exc)
                    self._write_log(f"ERROR cycle={iteration} {exc}")
                iteration += 1
                next_deadline += workload.interval_seconds
                self._stop.wait(max(next_deadline - time.monotonic(), 0.0))
        finally:
            try:
                client.execute(f"SYSTEM FLUSH DISTRIBUTED {name}.distributed_events")
                client.execute("SYSTEM FLUSH LOGS")
            except Exception as exc:
                self._run_summary["flush_error"] = str(exc)
                self._write_log(f"ERROR final flush {exc}")
            client.disconnect()

    def start(self, log_path: Path) -> dict[str, Any]:
        if not self.config.workload.enabled:
            return {"enabled": False, "started": False}
        if self._thread is not None:
            raise WorkloadError("review workload is already running")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("", encoding="utf-8")
        self._log_path = log_path
        self._stop.clear()
        self._run_summary = {
            "enabled": True,
            "started": True,
            "inserted_rows": 0,
            "successful_cycles": 0,
            "intentional_failures": 0,
            "errors": 0,
            "log": str(log_path.resolve()),
        }
        self._thread = threading.Thread(
            target=self._run,
            name="chdiag-review-workload",
            daemon=True,
        )
        self._thread.start()
        return self._run_summary

    def stop(self) -> None:
        if self._thread is None:
            return
        self._stop.set()
        self._thread.join(timeout=35)
        if self._thread.is_alive():
            raise WorkloadError("review workload did not stop within 35 seconds")
        self._thread = None
        if self._run_summary is not None:
            self._run_summary["stopped"] = True

    @contextmanager
    def running(self, *, enabled: bool, log_path: Path) -> Iterator[dict[str, Any]]:
        summary = (
            self.start(log_path)
            if enabled
            else {"enabled": self.config.workload.enabled, "started": False}
        )
        try:
            yield summary
        finally:
            if enabled:
                self.stop()
