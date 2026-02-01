#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Telemetry Storage
Phase 2, Step 7: File-Based JSON Persistence

Purpose: Persist telemetry data for analysis and portability
"""

import json
import os
import threading
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import shutil


class TelemetryStorage:
    """
    File-based JSON storage for telemetry data
    
    Features:
    - JSON file storage (human-readable)
    - Optional gzip compression
    - Automatic rotation by date
    - Export/import capabilities
    - Thread-safe writes
    """
    
    def __init__(self, base_dir: Optional[str] = None):
        if base_dir:
            self._base_dir = Path(base_dir)
        else:
            # Default to user's .frankenstein directory
            self._base_dir = Path.home() / ".frankenstein" / "telemetry"
        
        self._base_dir.mkdir(parents=True, exist_ok=True)
        
        # Subdirectories
        self._events_dir = self._base_dir / "events"
        self._metrics_dir = self._base_dir / "metrics"
        self._snapshots_dir = self._base_dir / "snapshots"
        self._exports_dir = self._base_dir / "exports"
        
        for d in [self._events_dir, self._metrics_dir, 
                  self._snapshots_dir, self._exports_dir]:
            d.mkdir(exist_ok=True)
        
        self._lock = threading.Lock()
        self._write_buffer: List[Dict] = []
        self._buffer_limit = 100
    
    def _get_date_file(self, directory: Path, prefix: str, 
                       compress: bool = False) -> Path:
        """Get filename for today's data"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        ext = ".json.gz" if compress else ".json"
        return directory / f"{prefix}_{date_str}{ext}"
    
    def save_event(self, event_dict: Dict[str, Any]):
        """Save an event to storage"""
        with self._lock:
            self._append_to_file(
                self._get_date_file(self._events_dir, "events"),
                event_dict
            )
    
    def save_events(self, events: List[Dict[str, Any]]):
        """Save multiple events"""
        with self._lock:
            filepath = self._get_date_file(self._events_dir, "events")
            for event in events:
                self._append_to_file(filepath, event)

    
    def save_metric(self, metric_dict: Dict[str, Any]):
        """Save a metric sample to storage"""
        with self._lock:
            self._append_to_file(
                self._get_date_file(self._metrics_dir, "metrics"),
                metric_dict
            )
    
    def save_snapshot(self, snapshot_dict: Dict[str, Any]):
        """Save a metrics snapshot"""
        with self._lock:
            self._append_to_file(
                self._get_date_file(self._snapshots_dir, "snapshots"),
                snapshot_dict
            )
    
    def _append_to_file(self, filepath: Path, data: Dict):
        """Append JSON object to file (one per line - JSONL format)"""
        try:
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data) + '\n')
        except Exception as e:
            print(f"Storage write error: {e}")
    
    def load_events(self, date: Optional[datetime] = None,
                    days_back: int = 1) -> List[Dict[str, Any]]:
        """Load events from storage"""
        events = []
        
        if date:
            dates = [date]
        else:
            dates = [datetime.now() - timedelta(days=i) for i in range(days_back)]
        
        for d in dates:
            date_str = d.strftime("%Y-%m-%d")
            filepath = self._events_dir / f"events_{date_str}.json"
            if filepath.exists():
                events.extend(self._load_jsonl(filepath))
        
        return events
    
    def load_metrics(self, date: Optional[datetime] = None,
                     days_back: int = 1) -> List[Dict[str, Any]]:
        """Load metrics from storage"""
        metrics = []
        
        if date:
            dates = [date]
        else:
            dates = [datetime.now() - timedelta(days=i) for i in range(days_back)]
        
        for d in dates:
            date_str = d.strftime("%Y-%m-%d")
            filepath = self._metrics_dir / f"metrics_{date_str}.json"
            if filepath.exists():
                metrics.extend(self._load_jsonl(filepath))
        
        return metrics

    
    def load_snapshots(self, date: Optional[datetime] = None,
                       days_back: int = 1) -> List[Dict[str, Any]]:
        """Load snapshots from storage"""
        snapshots = []
        
        if date:
            dates = [date]
        else:
            dates = [datetime.now() - timedelta(days=i) for i in range(days_back)]
        
        for d in dates:
            date_str = d.strftime("%Y-%m-%d")
            filepath = self._snapshots_dir / f"snapshots_{date_str}.json"
            if filepath.exists():
                snapshots.extend(self._load_jsonl(filepath))
        
        return snapshots
    
    def _load_jsonl(self, filepath: Path) -> List[Dict]:
        """Load JSONL file (one JSON object per line)"""
        items = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        items.append(json.loads(line))
        except Exception as e:
            print(f"Storage read error: {e}")
        return items
    
    def export_all(self, output_file: Optional[str] = None,
                   days_back: int = 7,
                   compress: bool = True) -> str:
        """Export all telemetry data to a single file"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = ".json.gz" if compress else ".json"
            output_file = str(self._exports_dir / f"export_{timestamp}{ext}")
        
        data = {
            'export_timestamp': datetime.now().isoformat(),
            'days_included': days_back,
            'events': self.load_events(days_back=days_back),
            'metrics': self.load_metrics(days_back=days_back),
            'snapshots': self.load_snapshots(days_back=days_back)
        }
        
        if compress:
            with gzip.open(output_file, 'wt', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        else:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        
        return output_file

    
    def import_data(self, filepath: str) -> Dict[str, int]:
        """Import telemetry data from export file"""
        if filepath.endswith('.gz'):
            with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                data = json.load(f)
        else:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        counts = {'events': 0, 'metrics': 0, 'snapshots': 0}
        
        for event in data.get('events', []):
            self.save_event(event)
            counts['events'] += 1
        
        for metric in data.get('metrics', []):
            self.save_metric(metric)
            counts['metrics'] += 1
        
        for snapshot in data.get('snapshots', []):
            self.save_snapshot(snapshot)
            counts['snapshots'] += 1
        
        return counts
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        def dir_size(path: Path) -> int:
            return sum(f.stat().st_size for f in path.glob('*') if f.is_file())
        
        def file_count(path: Path) -> int:
            return len(list(path.glob('*.json')))
        
        return {
            'base_dir': str(self._base_dir),
            'events': {
                'files': file_count(self._events_dir),
                'size_bytes': dir_size(self._events_dir)
            },
            'metrics': {
                'files': file_count(self._metrics_dir),
                'size_bytes': dir_size(self._metrics_dir)
            },
            'snapshots': {
                'files': file_count(self._snapshots_dir),
                'size_bytes': dir_size(self._snapshots_dir)
            },
            'exports': {
                'files': len(list(self._exports_dir.glob('*'))),
                'size_bytes': dir_size(self._exports_dir)
            },
            'total_size_bytes': sum([
                dir_size(self._events_dir),
                dir_size(self._metrics_dir),
                dir_size(self._snapshots_dir),
                dir_size(self._exports_dir)
            ])
        }
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Remove data older than specified days"""
        cutoff = datetime.now() - timedelta(days=days_to_keep)
        removed = 0
        
        for directory in [self._events_dir, self._metrics_dir, self._snapshots_dir]:
            for filepath in directory.glob('*.json'):
                try:
                    # Extract date from filename
                    date_str = filepath.stem.split('_')[-1]
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if file_date < cutoff:
                        filepath.unlink()
                        removed += 1
                except Exception:
                    continue
        
        return removed
