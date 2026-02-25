"""
Metrics Store for Performance Tracking

SQLite-based storage for performance metrics with efficient querying
and data retention management.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import logging
import os

logger = logging.getLogger(__name__)


class MetricsStore:
    """
    SQLite-based storage for performance metrics.

    Provides efficient storage and retrieval of performance data with
    automatic schema management and data retention policies.
    """

    def __init__(self, db_path: str):
        """
        Initialize metrics store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_database_exists()
        self._initialize_schema()
        logger.info(f"MetricsStore initialized at {db_path}")

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def _ensure_database_exists(self):
        """Ensure database directory exists."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def _initialize_schema(self):
        """Create database schema if it doesn't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Main metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    provider_id TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    latency REAL,
                    cpu_usage REAL,
                    ram_usage REAL,
                    throughput REAL,
                    error_rate REAL,
                    queue_depth INTEGER,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Indexes for efficient querying
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_provider_timestamp
                ON metrics(provider_id, timestamp)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_task_timestamp
                ON metrics(task_id, timestamp)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON metrics(timestamp)
            """)

            # Provider summary table (for quick lookups)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS provider_summaries (
                    provider_id TEXT PRIMARY KEY,
                    total_tasks INTEGER DEFAULT 0,
                    avg_latency REAL DEFAULT 0.0,
                    avg_cpu REAL DEFAULT 0.0,
                    avg_ram REAL DEFAULT 0.0,
                    error_rate REAL DEFAULT 0.0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            logger.debug("Database schema initialized")

    def store_metrics(self, metrics_list: List[Dict[str, Any]]):
        """
        Store multiple metrics in batch.

        Args:
            metrics_list: List of metric dictionaries
        """
        if not metrics_list:
            return

        with self._get_connection() as conn:
            cursor = conn.cursor()

            for metrics in metrics_list:
                # Serialize metadata
                metadata = {k: v for k, v in metrics.items()
                           if k not in ['task_id', 'provider_id', 'timestamp',
                                       'latency', 'cpu_usage', 'ram_usage',
                                       'throughput', 'error_rate', 'queue_depth']}

                cursor.execute("""
                    INSERT INTO metrics (
                        task_id, provider_id, timestamp, latency, cpu_usage,
                        ram_usage, throughput, error_rate, queue_depth, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.get('task_id'),
                    metrics.get('provider_id'),
                    metrics.get('timestamp'),
                    metrics.get('latency'),
                    metrics.get('cpu_usage'),
                    metrics.get('ram_usage'),
                    metrics.get('throughput'),
                    metrics.get('error_rate'),
                    metrics.get('queue_depth'),
                    json.dumps(metadata) if metadata else None
                ))

                # Update provider summary
                self._update_provider_summary(cursor, metrics)

        logger.debug(f"Stored {len(metrics_list)} metrics")

    def query_metrics(
        self,
        provider_id: Optional[str] = None,
        task_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Query metrics with filters.

        Args:
            provider_id: Filter by provider
            task_id: Filter by task
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum results

        Returns:
            List of metric dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Build query
            query = "SELECT * FROM metrics WHERE 1=1"
            params = []

            if provider_id:
                query += " AND provider_id = ?"
                params.append(provider_id)

            if task_id:
                query += " AND task_id = ?"
                params.append(task_id)

            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)

            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Convert to dictionaries
            results = []
            for row in rows:
                metrics = dict(row)
                # Deserialize metadata
                if metrics.get('metadata'):
                    try:
                        metadata = json.loads(metrics['metadata'])
                        metrics.update(metadata)
                    except json.JSONDecodeError:
                        pass
                del metrics['metadata']
                results.append(metrics)

            return results

    def get_provider_summary(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """
        Get summary statistics for a provider.

        Args:
            provider_id: Provider to query

        Returns:
            Summary dict or None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM provider_summaries WHERE provider_id = ?
            """, (provider_id,))
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None

    def cleanup_old_metrics(self, days_to_keep: int = 30):
        """
        Remove metrics older than specified days.

        Args:
            days_to_keep: Number of days to retain
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM metrics WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))
            deleted = cursor.rowcount

        logger.info(f"Cleaned up {deleted} old metrics (older than {days_to_keep} days)")

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dict with database stats
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Total metrics
            cursor.execute("SELECT COUNT(*) FROM metrics")
            total_metrics = cursor.fetchone()[0]

            # Unique providers
            cursor.execute("SELECT COUNT(DISTINCT provider_id) FROM metrics")
            unique_providers = cursor.fetchone()[0]

            # Unique tasks
            cursor.execute("SELECT COUNT(DISTINCT task_id) FROM metrics")
            unique_tasks = cursor.fetchone()[0]

            # Date range
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM metrics")
            date_range = cursor.fetchone()

            # Database size
            db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

            return {
                'total_metrics': total_metrics,
                'unique_providers': unique_providers,
                'unique_tasks': unique_tasks,
                'oldest_metric': date_range[0],
                'newest_metric': date_range[1],
                'database_size_bytes': db_size,
                'database_path': self.db_path
            }

    # Private methods

    def _update_provider_summary(self, cursor, metrics: Dict[str, Any]):
        """Update provider summary statistics."""
        provider_id = metrics.get('provider_id')
        if not provider_id:
            return

        # Get current summary
        cursor.execute("""
            SELECT total_tasks, avg_latency, avg_cpu, avg_ram, error_rate
            FROM provider_summaries WHERE provider_id = ?
        """, (provider_id,))
        row = cursor.fetchone()

        if row:
            # Update existing summary (running average)
            total_tasks = row[0]
            avg_latency = row[1]
            avg_cpu = row[2]
            avg_ram = row[3]
            error_rate = row[4]

            # Calculate new averages
            new_total = total_tasks + 1
            new_avg_latency = ((avg_latency * total_tasks) + metrics.get('latency', 0)) / new_total
            new_avg_cpu = ((avg_cpu * total_tasks) + metrics.get('cpu_usage', 0)) / new_total
            new_avg_ram = ((avg_ram * total_tasks) + metrics.get('ram_usage', 0)) / new_total
            new_error_rate = ((error_rate * total_tasks) + metrics.get('error_rate', 0)) / new_total

            cursor.execute("""
                UPDATE provider_summaries
                SET total_tasks = ?, avg_latency = ?, avg_cpu = ?, avg_ram = ?,
                    error_rate = ?, last_updated = ?
                WHERE provider_id = ?
            """, (new_total, new_avg_latency, new_avg_cpu, new_avg_ram,
                  new_error_rate, datetime.now().isoformat(), provider_id))
        else:
            # Create new summary
            cursor.execute("""
                INSERT INTO provider_summaries (
                    provider_id, total_tasks, avg_latency, avg_cpu, avg_ram,
                    error_rate, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                provider_id, 1,
                metrics.get('latency', 0),
                metrics.get('cpu_usage', 0),
                metrics.get('ram_usage', 0),
                metrics.get('error_rate', 0),
                datetime.now().isoformat()
            ))
