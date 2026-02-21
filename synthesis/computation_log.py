"""
FRANKENSTEIN 1.0 — Computation Logger
"Show your work" logging for quantum computations.

Every gate, every evolution step, every measurement is logged
to append-only JSONL files in ~/.frankenstein/synthesis_data/logs/

This is what makes Frankenstein a scientific instrument:
- Full audit trail of every computation
- Reproducible: log includes seeds, parameters, initial states
- Inspectable: user can review step-by-step what happened
- Persistent: survives session restart

Lazy-loaded: Only instantiated when quantum operations begin.

Log format (one JSON object per line in .jsonl file):
{
    "timestamp": "2026-02-20T14:30:00.123456",
    "event": "gate_applied",
    "seq": 3,
    "data": {
        "gate": "h",
        "targets": [0],
        "controls": [],
        "params": {},
        "state_norm_after": 1.0
    }
}
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger("frankenstein.computation_log")


class ComputationLogger:
    """
    Append-only computation logger for quantum operations.

    Creates one .jsonl file per session.
    Each line is a self-contained JSON event.

    Events logged:
    - session_start: Session metadata (hardware, config)
    - qubits_initialized: Number of qubits, initial state
    - gate_applied: Gate name, targets, controls, parameters
    - evolution_step: Hamiltonian info, time step, method
    - measurement: Probabilities, collapsed state, shots
    - state_saved: Where state was saved
    - state_loaded: Where state was loaded from
    - circuit_saved: Circuit name, gate count
    - error: Any errors during computation
    - session_end: Summary statistics
    """

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or (Path.home() / ".frankenstein" / "synthesis_data" / "logs")
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Current session log file
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._log_file = self.base_path / f"session_{session_id}.jsonl"
        self._event_count = 0
        self._session_start = time.time()

        # Log session start
        self._write_event("session_start", {
            "session_id": session_id,
            "engine_version": "2.0",
            "timestamp": datetime.now().isoformat(),
        })

    def _write_event(self, event_type: str, data: Dict[str, Any]):
        """Write a single event to the log file."""
        try:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "event": event_type,
                "seq": self._event_count,
                "data": data,
            }
            with open(self._log_file, 'a') as f:
                f.write(json.dumps(entry, default=str) + "\n")
            self._event_count += 1
        except Exception as e:
            logger.error(f"Failed to write computation log: {e}")

    def log_init(self, n_qubits: int, initial_state: str):
        """Log qubit initialization."""
        self._write_event("qubits_initialized", {
            "n_qubits": n_qubits,
            "initial_state": initial_state,
            "dimension": 2 ** n_qubits,
            "memory_bytes": (2 ** n_qubits) * 16,  # complex128
        })

    def log_gate(self, gate: str, targets: List[int],
                 controls: Optional[List[int]] = None,
                 params: Optional[Dict[str, float]] = None,
                 state_norm_after: float = 1.0):
        """Log gate application."""
        self._write_event("gate_applied", {
            "gate": gate,
            "targets": targets,
            "controls": controls or [],
            "params": params or {},
            "state_norm_after": round(state_norm_after, 10),
        })

    def log_evolution(self, hamiltonian_type: str, time_val: float,
                      n_steps: int, method: str, computation_time_sec: float):
        """Log Schrödinger evolution step."""
        self._write_event("evolution_step", {
            "hamiltonian": hamiltonian_type,
            "evolution_time": time_val,
            "steps": n_steps,
            "method": method,
            "wall_time_sec": round(computation_time_sec, 4),
        })

    def log_measurement(self, n_qubits: int, shots: int,
                        top_results: List[Dict[str, Any]],
                        collapsed_to: Optional[str] = None):
        """Log measurement with Born rule probabilities."""
        self._write_event("measurement", {
            "n_qubits": n_qubits,
            "shots": shots,
            "top_results": top_results[:10],  # Top 10 outcomes
            "collapsed_to": collapsed_to,
        })

    def log_state_saved(self, name: str, filepath: str):
        """Log state save."""
        self._write_event("state_saved", {"name": name, "path": filepath})

    def log_state_loaded(self, name: str, filepath: str):
        """Log state load."""
        self._write_event("state_loaded", {"name": name, "path": filepath})

    def log_circuit_saved(self, name: str, n_gates: int, n_qubits: int):
        """Log circuit save."""
        self._write_event("circuit_saved", {
            "name": name, "gates": n_gates, "n_qubits": n_qubits
        })

    def log_error(self, error_type: str, message: str):
        """Log computation error."""
        self._write_event("error", {"type": error_type, "message": message})

    def end_session(self):
        """Log session end with summary."""
        elapsed = time.time() - self._session_start
        self._write_event("session_end", {
            "total_events": self._event_count,
            "session_duration_sec": round(elapsed, 2),
        })

    # ==================== LOG INSPECTION (for 'memory view' commands) ====================

    def get_recent_events(self, n: int = 20) -> List[Dict[str, Any]]:
        """Read the last N events from current session log."""
        events = []
        if self._log_file.exists():
            with open(self._log_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        return events[-n:]

    def get_session_summary(self) -> Dict[str, Any]:
        """Summarize current session log."""
        events = []
        if self._log_file.exists():
            with open(self._log_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

        event_types: Dict[str, int] = {}
        for e in events:
            t = e.get("event", "unknown")
            event_types[t] = event_types.get(t, 0) + 1

        return {
            "log_file": str(self._log_file),
            "total_events": len(events),
            "event_breakdown": event_types,
            "session_duration_sec": round(time.time() - self._session_start, 2),
        }

    @staticmethod
    def list_session_logs(base_path: Optional[Path] = None) -> List[Dict[str, Any]]:
        """List all session log files with metadata."""
        log_dir = base_path or (Path.home() / ".frankenstein" / "synthesis_data" / "logs")
        logs = []
        if log_dir.exists():
            for f in sorted(log_dir.glob("session_*.jsonl"), reverse=True):
                line_count = 0
                with open(f, 'r') as fh:
                    for _ in fh:
                        line_count += 1
                logs.append({
                    "filename": f.name,
                    "events": line_count,
                    "size_bytes": f.stat().st_size,
                    "size_kb": round(f.stat().st_size / 1024, 1),
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                })
        return logs

    @staticmethod
    def clear_old_logs(base_path: Optional[Path] = None, keep_last: int = 10) -> Dict[str, Any]:
        """Delete old session logs, keeping the most recent N."""
        log_dir = base_path or (Path.home() / ".frankenstein" / "synthesis_data" / "logs")
        logs = sorted(log_dir.glob("session_*.jsonl"), reverse=True)

        deleted = 0
        freed_bytes = 0
        for f in logs[keep_last:]:
            freed_bytes += f.stat().st_size
            f.unlink()
            deleted += 1

        return {
            "deleted_files": deleted,
            "freed_bytes": freed_bytes,
            "freed_kb": round(freed_bytes / 1024, 1),
            "remaining_logs": min(len(logs), keep_last),
        }


# ==================== SINGLETON (LAZY-LOADED) ====================

_comp_logger: Optional[ComputationLogger] = None


def get_computation_logger() -> ComputationLogger:
    """Get or create the global ComputationLogger instance. Lazy-loaded."""
    global _comp_logger
    if _comp_logger is None:
        _comp_logger = ComputationLogger()
    return _comp_logger
