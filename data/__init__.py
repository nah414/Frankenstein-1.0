#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Data Pipeline & Telemetry Module
Phase 2, Step 7: Data Pipeline + Telemetry

Purpose: Unified data flow, metrics collection, and event management
Author: Frankenstein Project

Components:
- DataPipeline: Unified data flow management
- TelemetryCollector: Always-on metrics gathering
- EventBus: Pub/sub messaging system
- MetricsAggregator: Statistics computation
- TelemetryStorage: File-based JSON persistence
"""

from .events import EventBus, Event, EventType
from .telemetry import TelemetryCollector, MetricType
from .metrics import MetricsAggregator, MetricSnapshot
from .storage import TelemetryStorage
from .pipeline import DataPipeline, DataPacket, PipelineStage

__all__ = [
    # Events
    'EventBus',
    'Event', 
    'EventType',
    # Telemetry
    'TelemetryCollector',
    'MetricType',
    # Metrics
    'MetricsAggregator',
    'MetricSnapshot',
    # Storage
    'TelemetryStorage',
    # Pipeline
    'DataPipeline',
    'DataPacket',
    'PipelineStage',
]

__version__ = "1.0.0"
