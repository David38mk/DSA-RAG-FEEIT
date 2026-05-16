"""
Query logger - SQLite-backed observability for the DSA-RAG pipeline.

Records sessions, queries, responses, and timing metrics so the thesis
Results section can be populated from real usage data.

Tables: sessions, queries, responses, metrics. See SCHEMA below.
"""

import csv
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    started_at REAL NOT NULL,
    ended_at REAL,
    app_version TEXT,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS queries (
    query_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    question TEXT NOT NULL,
    enhanced_question TEXT,
    language TEXT,
    intent TEXT,
    intent_confidence REAL,
    routing_method TEXT,
    n_results INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE TABLE IF NOT EXISTS responses (
    response_id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    answer TEXT,
    sources TEXT,
    num_sources INTEGER,
    model TEXT,
    success INTEGER NOT NULL,
    error TEXT,
    FOREIGN KEY (query_id) REFERENCES queries(query_id)
);

CREATE TABLE IF NOT EXISTS metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id TEXT NOT NULL,
    retrieval_time_ms INTEGER,
    generation_time_ms INTEGER,
    total_time_ms INTEGER,
    tokens_used INTEGER,
    FOREIGN KEY (query_id) REFERENCES queries(query_id)
);

CREATE INDEX IF NOT EXISTS idx_queries_session ON queries(session_id);
CREATE INDEX IF NOT EXISTS idx_queries_timestamp ON queries(timestamp);
CREATE INDEX IF NOT EXISTS idx_responses_query ON responses(query_id);
CREATE INDEX IF NOT EXISTS idx_metrics_query ON metrics(query_id);
"""


class QueryLogger:
    """SQLite-backed logger for the RAG pipeline."""

    def __init__(
        self,
        db_path: str = "data/logs/queries.db",
        app_version: str = "1.0",
    ):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.app_version = app_version
        self._session_id: Optional[str] = None
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def start_session(self, metadata: Optional[dict] = None) -> str:
        session_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, started_at, app_version, metadata) "
                "VALUES (?, ?, ?, ?)",
                (
                    session_id,
                    time.time(),
                    self.app_version,
                    json.dumps(metadata or {}),
                ),
            )
        self._session_id = session_id
        return session_id

    def end_session(self, session_id: Optional[str] = None) -> None:
        sid = session_id or self._session_id
        if not sid:
            return
        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions SET ended_at = ? WHERE session_id = ?",
                (time.time(), sid),
            )

    def log_query(
        self,
        question: str,
        language: Optional[str] = None,
        intent: Optional[str] = None,
        intent_confidence: Optional[float] = None,
        routing_method: Optional[str] = None,
        n_results: Optional[int] = None,
        enhanced_question: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        sid = session_id or self._session_id or self.start_session()
        query_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO queries
                (query_id, session_id, timestamp, question, enhanced_question,
                 language, intent, intent_confidence, routing_method, n_results)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    query_id,
                    sid,
                    time.time(),
                    question,
                    enhanced_question,
                    language,
                    intent,
                    intent_confidence,
                    routing_method,
                    n_results,
                ),
            )
        return query_id

    def log_response(
        self,
        query_id: str,
        answer: Optional[str],
        sources: Optional[list] = None,
        model: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO responses
                (query_id, timestamp, answer, sources, num_sources, model, success, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    query_id,
                    time.time(),
                    answer,
                    json.dumps(sources or []),
                    len(sources) if sources else 0,
                    model,
                    1 if success else 0,
                    error,
                ),
            )

    def log_metrics(
        self,
        query_id: str,
        retrieval_time_ms: Optional[int] = None,
        generation_time_ms: Optional[int] = None,
        total_time_ms: Optional[int] = None,
        tokens_used: Optional[int] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO metrics
                (query_id, retrieval_time_ms, generation_time_ms, total_time_ms, tokens_used)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    query_id,
                    retrieval_time_ms,
                    generation_time_ms,
                    total_time_ms,
                    tokens_used,
                ),
            )

    def summary_stats(self) -> dict:
        """Aggregate stats for dashboards or thesis Results section."""
        with self._connect() as conn:
            cur = conn.cursor()
            total = cur.execute("SELECT COUNT(*) FROM queries").fetchone()[0]
            by_language = dict(
                cur.execute(
                    "SELECT language, COUNT(*) FROM queries GROUP BY language"
                ).fetchall()
            )
            by_intent = dict(
                cur.execute(
                    "SELECT intent, COUNT(*) FROM queries GROUP BY intent"
                ).fetchall()
            )
            avg_retrieval, avg_generation, avg_total = cur.execute(
                "SELECT AVG(retrieval_time_ms), AVG(generation_time_ms), "
                "AVG(total_time_ms) FROM metrics"
            ).fetchone()
            success_rate = cur.execute(
                "SELECT AVG(success) FROM responses"
            ).fetchone()[0]
            sessions = cur.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        return {
            "total_queries": total,
            "total_sessions": sessions,
            "by_language": by_language,
            "by_intent": by_intent,
            "avg_retrieval_ms": avg_retrieval,
            "avg_generation_ms": avg_generation,
            "avg_total_ms": avg_total,
            "success_rate": success_rate,
        }

    def export_csv(self, output_dir: str = "data/logs/exports") -> Path:
        """Dump all tables as CSV for offline analysis."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            for table in ("sessions", "queries", "responses", "metrics"):
                cur = conn.execute(f"SELECT * FROM {table}")
                cols = [d[0] for d in cur.description]
                rows = cur.fetchall()
                with open(out / f"{table}.csv", "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(cols)
                    writer.writerows(rows)
        return out


if __name__ == "__main__":
    logger = QueryLogger(db_path="data/logs/queries.db")
    sid = logger.start_session(metadata={"source": "manual_test"})
    qid = logger.log_query(
        question="Test query",
        language="mk",
        intent="support",
        intent_confidence=0.9,
        routing_method="rules_only",
        n_results=15,
    )
    logger.log_response(qid, answer="Test answer", sources=["doc1.pdf"], model="llama-3.3-70b-versatile")
    logger.log_metrics(qid, retrieval_time_ms=87, generation_time_ms=746, total_time_ms=833)
    logger.end_session()
    print(json.dumps(logger.summary_stats(), indent=2))
