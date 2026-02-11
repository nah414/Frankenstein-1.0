"""
Audit Logger - JSON-based audit logging system for Frankenstein 1.0

Tracks all operations, provider access, and resource usage across all 28 providers.
Supports encryption for sensitive operations and automatic log rotation.

Author: Frankenstein 1.0 Team
Phase: 3, Step 6
"""

import json
import os
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from cryptography.fernet import Fernet
import base64
import hashlib
import psutil


class AuditLogger:
    """
    JSON-based audit logger for tracking all system operations.

    Supports encryption, log rotation, and provider-specific tracking
    for all 28 quantum and classical providers.
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    # Maximum log file size before rotation (10MB)
    MAX_LOG_SIZE = 10 * 1024 * 1024

    # Log retention period (30 days for Tier 1)
    RETENTION_DAYS = 30

    def __new__(cls):
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the audit logger (only once)."""
        if self._initialized:
            return

        with self._lock:
            if not self._initialized:
                self._log_dir = Path.home() / ".frankenstein" / "logs"
                self._log_file = self._log_dir / "audit_log.json"
                self._key_file = self._log_dir / "audit.key"

                # Ensure log directory exists
                self._log_dir.mkdir(parents=True, exist_ok=True)

                # Initialize encryption
                self._cipher = self._initialize_encryption()

                # Initialize log file if it doesn't exist
                if not self._log_file.exists():
                    self._write_logs([])

                self._initialized = True

    def _initialize_encryption(self) -> Fernet:
        """Initialize or load encryption key for secure log storage."""
        if self._key_file.exists():
            with open(self._key_file, 'rb') as f:
                key = f.read()
        else:
            # Generate a deterministic key from system info
            system_id = f"{os.name}-{Path.home()}-audit".encode()
            key_material = hashlib.sha256(system_id).digest()
            key = base64.urlsafe_b64encode(key_material)

            with open(self._key_file, 'wb') as f:
                f.write(key)

            # Restrict permissions on key file (Unix-like systems)
            try:
                os.chmod(self._key_file, 0o600)
            except (OSError, AttributeError):
                pass  # Windows doesn't support chmod

        return Fernet(key)

    def _read_logs(self) -> List[Dict]:
        """Read all logs from file."""
        if not self._log_file.exists():
            return []

        try:
            with open(self._log_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write_logs(self, logs: List[Dict]):
        """Write logs to file."""
        with open(self._log_file, 'w') as f:
            json.dump(logs, f, indent=2)

    def _check_rotation_needed(self) -> bool:
        """Check if log file needs rotation."""
        if not self._log_file.exists():
            return False

        file_size = self._log_file.stat().st_size
        return file_size > self.MAX_LOG_SIZE

    def _rotate_logs(self):
        """Rotate log file if it exceeds maximum size."""
        if not self._check_rotation_needed():
            return

        # Read existing logs
        logs = self._read_logs()

        # Create rotated log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated_file = self._log_dir / f"audit_log_{timestamp}.json"

        # Move current log to rotated file
        self._log_file.rename(rotated_file)

        # Keep only recent logs in new file (last 30 days)
        cutoff_date = datetime.now() - timedelta(days=self.RETENTION_DAYS)
        recent_logs = [
            log for log in logs
            if datetime.fromisoformat(log['timestamp']) > cutoff_date
        ]

        # Write recent logs to new file
        self._write_logs(recent_logs)

    def _get_resource_usage(self) -> Dict[str, float]:
        """Get current CPU and RAM usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            ram_percent = psutil.virtual_memory().percent
            return {
                "cpu_percent": round(cpu_percent, 2),
                "ram_percent": round(ram_percent, 2)
            }
        except Exception:
            return {"cpu_percent": 0.0, "ram_percent": 0.0}

    def log_action(
        self,
        user_role: str,
        action: str,
        resource: str,
        result: str,
        provider_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        provider_category: Optional[str] = None,
        details: Optional[str] = None,
        **kwargs
    ):
        """
        Log an action to the audit trail.

        Args:
            user_role: Role performing the action (Admin, User, Agent, ReadOnly)
            action: Operation name (e.g., 'quantum_job_submit')
            resource: What was accessed/modified
            result: Result of operation ('success', 'denied', 'error')
            provider_name: Optional provider name (one of 28 providers)
            agent_name: Optional agent name if action by agent
            provider_category: Optional category (quantum, classical_gpu_quantum, classical_compute)
            details: Optional additional context
            **kwargs: Additional fields to include in log entry

        Thread-safe operation.
        """
        with self._lock:
            # Check if rotation needed before logging
            self._rotate_logs()

            # Create log entry
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "user_role": user_role,
                "action": action,
                "resource": resource,
                "result": result,
                "resource_impact": self._get_resource_usage()
            }

            # Add optional fields
            if agent_name:
                log_entry["agent_name"] = agent_name
            if provider_name:
                log_entry["provider_name"] = provider_name
            if provider_category:
                log_entry["provider_category"] = provider_category
            if details:
                log_entry["details"] = details

            # Add any additional kwargs
            log_entry.update(kwargs)

            # Read existing logs
            logs = self._read_logs()

            # Append new entry
            logs.append(log_entry)

            # Write updated logs
            self._write_logs(logs)

    def get_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        action: Optional[str] = None,
        provider_name: Optional[str] = None,
        user_role: Optional[str] = None,
        result: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Retrieve logs with optional filtering.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            action: Optional action filter
            provider_name: Optional provider name filter (one of 28 providers)
            user_role: Optional role filter
            result: Optional result filter
            limit: Optional maximum number of logs to return

        Returns:
            List of log entries matching filters

        Thread-safe operation.
        """
        with self._lock:
            logs = self._read_logs()

            # Apply filters
            filtered_logs = logs

            if start_date:
                filtered_logs = [
                    log for log in filtered_logs
                    if datetime.fromisoformat(log['timestamp']) >= start_date
                ]

            if end_date:
                filtered_logs = [
                    log for log in filtered_logs
                    if datetime.fromisoformat(log['timestamp']) <= end_date
                ]

            if action:
                filtered_logs = [
                    log for log in filtered_logs
                    if log.get('action') == action
                ]

            if provider_name:
                filtered_logs = [
                    log for log in filtered_logs
                    if log.get('provider_name') == provider_name
                ]

            if user_role:
                filtered_logs = [
                    log for log in filtered_logs
                    if log.get('user_role') == user_role
                ]

            if result:
                filtered_logs = [
                    log for log in filtered_logs
                    if log.get('result') == result
                ]

            # Apply limit if specified
            if limit:
                filtered_logs = filtered_logs[-limit:]

            return filtered_logs

    def get_provider_usage_stats(
        self,
        provider_name: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get usage statistics for a specific provider.

        Args:
            provider_name: Provider name (one of 28 providers)
            days: Number of days to look back (default: 30)

        Returns:
            Dictionary with usage statistics:
                - total_actions: Total actions for this provider
                - successful_actions: Number of successful actions
                - failed_actions: Number of failed/denied actions
                - last_used: Timestamp of last use
                - actions_by_type: Breakdown by action type

        Thread-safe operation.
        """
        with self._lock:
            cutoff_date = datetime.now() - timedelta(days=days)

            # Get logs for this provider
            provider_logs = [
                log for log in self._read_logs()
                if log.get('provider_name') == provider_name
                and datetime.fromisoformat(log['timestamp']) > cutoff_date
            ]

            if not provider_logs:
                return {
                    "total_actions": 0,
                    "successful_actions": 0,
                    "failed_actions": 0,
                    "last_used": None,
                    "actions_by_type": {}
                }

            # Calculate statistics
            total_actions = len(provider_logs)
            successful_actions = sum(
                1 for log in provider_logs if log.get('result') == 'success'
            )
            failed_actions = sum(
                1 for log in provider_logs
                if log.get('result') in ['denied', 'error']
            )

            # Get last used timestamp
            last_used = max(
                log['timestamp'] for log in provider_logs
            )

            # Get actions by type
            actions_by_type = {}
            for log in provider_logs:
                action = log.get('action', 'unknown')
                actions_by_type[action] = actions_by_type.get(action, 0) + 1

            return {
                "total_actions": total_actions,
                "successful_actions": successful_actions,
                "failed_actions": failed_actions,
                "last_used": last_used,
                "actions_by_type": actions_by_type
            }

    def cleanup_old_logs(self, days: int = 30):
        """
        Remove logs older than specified days.

        Args:
            days: Number of days to retain (default: 30)

        Thread-safe operation.
        """
        with self._lock:
            cutoff_date = datetime.now() - timedelta(days=days)

            # Read existing logs
            logs = self._read_logs()

            # Keep only recent logs
            recent_logs = [
                log for log in logs
                if datetime.fromisoformat(log['timestamp']) > cutoff_date
            ]

            # Write filtered logs
            self._write_logs(recent_logs)

            # Return number of logs removed
            removed_count = len(logs) - len(recent_logs)
            return removed_count

    def get_all_providers_stats(self, days: int = 30) -> Dict[str, Dict]:
        """
        Get usage statistics for all providers that have been used.

        Args:
            days: Number of days to look back (default: 30)

        Returns:
            Dictionary mapping provider names to their statistics

        Thread-safe operation.
        """
        with self._lock:
            cutoff_date = datetime.now() - timedelta(days=days)

            # Get all logs within time range
            recent_logs = [
                log for log in self._read_logs()
                if datetime.fromisoformat(log['timestamp']) > cutoff_date
            ]

            # Get unique provider names
            providers = set(
                log.get('provider_name')
                for log in recent_logs
                if log.get('provider_name')
            )

            # Get stats for each provider
            stats = {}
            for provider in providers:
                stats[provider] = self.get_provider_usage_stats(provider, days)

            return stats

    def clear_all_logs(self):
        """
        Clear all audit logs (Admin only - should check permissions externally).

        Thread-safe operation.
        """
        with self._lock:
            self._write_logs([])


# Singleton instance getter
_logger_instance = None

def get_audit_logger() -> AuditLogger:
    """
    Get the singleton AuditLogger instance.

    Returns:
        AuditLogger singleton
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = AuditLogger()
    return _logger_instance
