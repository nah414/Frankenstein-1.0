#!/usr/bin/env python3
"""
Tests for Data Pipeline & Telemetry Module
Phase 2, Step 7
"""

import pytest
import time
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil


class TestEventBus:
    """Tests for EventBus pub/sub system"""
    
    def test_singleton(self):
        """EventBus should be singleton"""
        from data import EventBus
        bus1 = EventBus()
        bus2 = EventBus()
        assert bus1 is bus2
    
    def test_publish_subscribe(self):
        """Events should reach subscribers"""
        from data import EventBus, Event, EventType
        
        bus = EventBus()
        received = []
        
        def handler(event):
            received.append(event)
        
        bus.subscribe(EventType.SYSTEM_START, handler)
        event = Event(event_type=EventType.SYSTEM_START, source="test")
        bus.publish_sync(event)
        
        assert len(received) == 1
        assert received[0].event_type == EventType.SYSTEM_START

    
    def test_emit_convenience(self):
        """emit() should create and publish events"""
        from data import EventBus, EventType
        
        bus = EventBus()
        bus.clear_history()
        
        bus.emit(EventType.COMMAND_EXECUTED, source="terminal", command="ls")
        
        history = bus.get_history(limit=1)
        assert len(history) == 1
        assert history[0].data.get('command') == 'ls'


class TestTelemetryCollector:
    """Tests for TelemetryCollector"""
    
    def test_singleton(self):
        """TelemetryCollector should be singleton"""
        from data import TelemetryCollector
        t1 = TelemetryCollector()
        t2 = TelemetryCollector()
        assert t1 is t2
    
    def test_record_metric(self):
        """Should record and retrieve metrics"""
        from data import TelemetryCollector, MetricType
        
        telemetry = TelemetryCollector()
        telemetry.record(MetricType.CPU_PERCENT, 45.5)
        
        latest = telemetry.get_latest(MetricType.CPU_PERCENT)
        assert latest is not None
        assert latest.value == 45.5
    
    def test_counters(self):
        """Should track counters"""
        from data import TelemetryCollector
        
        telemetry = TelemetryCollector()
        telemetry.increment("test_counter", 5)
        telemetry.increment("test_counter", 3)
        
        assert telemetry.get_counter("test_counter") == 8
    
    def test_statistics(self):
        """Should compute statistics over window"""
        from data import TelemetryCollector, MetricType
        
        telemetry = TelemetryCollector()
        
        # Record multiple samples
        for v in [10, 20, 30, 40, 50]:
            telemetry.record(MetricType.MEMORY_PERCENT, v)
        
        stats = telemetry.get_stats(MetricType.MEMORY_PERCENT, window_seconds=60)
        assert stats['count'] >= 5
        assert stats['min'] <= 10
        assert stats['max'] >= 50


class TestMetricsAggregator:
    """Tests for MetricsAggregator"""
    
    def test_take_snapshot(self):
        """Should capture metric snapshot"""
        from data import TelemetryCollector, MetricsAggregator
        
        telemetry = TelemetryCollector()
        aggregator = MetricsAggregator(telemetry)
        
        snapshot = aggregator.take_snapshot()
        
        assert snapshot.timestamp is not None
        assert 'cpu_percent' in snapshot.system
        assert 'memory_percent' in snapshot.system
    
    def test_health_calculation(self):
        """Should calculate health score"""
        from data import TelemetryCollector, MetricsAggregator
        
        telemetry = TelemetryCollector()
        aggregator = MetricsAggregator(telemetry)
        
        summary = aggregator.get_summary()
        health = summary.get('health', {})
        
        assert 'score' in health
        assert 'status' in health
        assert health['score'] >= 0 and health['score'] <= 100



class TestTelemetryStorage:
    """Tests for TelemetryStorage file persistence"""
    
    def test_save_and_load_events(self):
        """Should persist and retrieve events"""
        from data import TelemetryStorage
        
        # Use temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = TelemetryStorage(base_dir=tmpdir)
            
            event_dict = {
                'event_id': 'test123',
                'event_type': 'SYSTEM_START',
                'timestamp': datetime.now().isoformat(),
                'source': 'test',
                'data': {'key': 'value'}
            }
            
            storage.save_event(event_dict)
            events = storage.load_events(days_back=1)
            
            assert len(events) >= 1
            assert events[-1]['event_id'] == 'test123'
    
    def test_export_import(self):
        """Should export and import data"""
        from data import TelemetryStorage
        
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = TelemetryStorage(base_dir=tmpdir)
            
            # Save some data
            storage.save_event({'event_type': 'TEST', 'timestamp': datetime.now().isoformat()})
            storage.save_metric({'metric': 'CPU', 'value': 50, 'timestamp': datetime.now().isoformat()})
            
            # Export
            export_path = storage.export_all(days_back=1, compress=False)
            assert Path(export_path).exists()
            
            # Create new storage and import
            storage2 = TelemetryStorage(base_dir=tmpdir + "_new")
            counts = storage2.import_data(export_path)
            
            assert counts['events'] >= 1
            assert counts['metrics'] >= 1


class TestDataPipeline:
    """Tests for DataPipeline"""
    
    def test_singleton(self):
        """DataPipeline should be singleton"""
        from data import DataPipeline
        p1 = DataPipeline()
        p2 = DataPipeline()
        assert p1 is p2
    
    def test_create_packet(self):
        """Should create data packets"""
        from data import DataPipeline, PipelineStage
        
        pipeline = DataPipeline()
        packet = pipeline.create_packet(
            payload="test data",
            source="test",
            destination="synthesis"
        )
        
        assert packet.payload == "test data"
        assert packet.source == "test"
        assert packet.stage == PipelineStage.INPUT
    
    def test_sync_processing(self):
        """Should process packets synchronously"""
        from data import DataPipeline, PipelineStage
        
        pipeline = DataPipeline()
        
        # Register a simple processor
        def upper_transform(packet):
            if isinstance(packet.payload, str):
                packet.payload = packet.payload.upper()
            return packet
        
        pipeline.register_processor(PipelineStage.TRANSFORM, upper_transform)
        
        packet = pipeline.create_packet("hello world")
        result = pipeline.process_sync(packet)
        
        assert result.payload == "HELLO WORLD"
        assert not result.has_errors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
