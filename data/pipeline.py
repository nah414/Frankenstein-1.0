#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Data Pipeline
Phase 2, Step 7: Unified Data Flow Management

Purpose: Route data between synthesis engine, agents, and UI
"""

import threading
import time
from datetime import datetime
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from queue import Queue, Empty
import uuid


class PipelineStage(Enum):
    """Pipeline processing stages"""
    INPUT = auto()
    VALIDATE = auto()
    TRANSFORM = auto()
    PROCESS = auto()
    SYNTHESIZE = auto()
    OUTPUT = auto()


@dataclass
class DataPacket:
    """Unit of data flowing through pipeline"""
    packet_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: datetime = field(default_factory=datetime.now)
    stage: PipelineStage = PipelineStage.INPUT
    source: str = "unknown"
    destination: str = "unknown"
    data_type: str = "generic"
    payload: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    processing_times: Dict[str, float] = field(default_factory=dict)

    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'packet_id': self.packet_id,
            'created_at': self.created_at.isoformat(),
            'stage': self.stage.name,
            'source': self.source,
            'destination': self.destination,
            'data_type': self.data_type,
            'payload': str(self.payload)[:1000] if self.payload else None,
            'metadata': self.metadata,
            'errors': self.errors,
            'processing_times': self.processing_times
        }
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    @property
    def total_processing_time(self) -> float:
        return sum(self.processing_times.values())


class DataPipeline:
    """
    Central data routing and processing pipeline
    
    Features:
    - Stage-based processing
    - Pluggable processors per stage
    - Async and sync modes
    - Automatic telemetry
    - Error handling and recovery
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton for global pipeline"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Processors for each stage
        self._processors: Dict[PipelineStage, List[Callable]] = {
            stage: [] for stage in PipelineStage
        }
        
        # Queues for async processing
        self._input_queue: Queue = Queue()
        self._output_queue: Queue = Queue()
        
        # Processing thread
        self._running = False
        self._process_thread: Optional[threading.Thread] = None
        
        # Statistics
        self._stats = {
            'packets_processed': 0,
            'packets_failed': 0,
            'bytes_processed': 0,
            'avg_latency_ms': 0
        }
        # CRITICAL BUGFIX: Was unbounded list causing memory leaks
        from collections import deque
        self._latencies: deque = deque(maxlen=100)  # Keep last 100 latency samples
        
        # Callbacks
        self._on_complete: List[Callable[[DataPacket], None]] = []
        self._on_error: List[Callable[[DataPacket, Exception], None]] = []
        
        self._data_lock = threading.Lock()
        self._initialized = True

    
    def start(self):
        """Start async processing"""
        if self._running:
            return
        self._running = True
        self._process_thread = threading.Thread(
            target=self._process_loop,
            daemon=True,
            name="DataPipeline-Process"
        )
        self._process_thread.start()
    
    def stop(self):
        """Stop async processing"""
        self._running = False
        if self._process_thread:
            self._process_thread.join(timeout=2.0)
    
    def register_processor(self, stage: PipelineStage, 
                          processor: Callable[[DataPacket], DataPacket]):
        """Register a processor for a pipeline stage"""
        with self._data_lock:
            if processor not in self._processors[stage]:
                self._processors[stage].append(processor)
    
    def unregister_processor(self, stage: PipelineStage,
                            processor: Callable[[DataPacket], DataPacket]):
        """Remove a processor"""
        with self._data_lock:
            if processor in self._processors[stage]:
                self._processors[stage].remove(processor)
    
    def on_complete(self, callback: Callable[[DataPacket], None]):
        """Register completion callback"""
        self._on_complete.append(callback)
    
    def on_error(self, callback: Callable[[DataPacket, Exception], None]):
        """Register error callback"""
        self._on_error.append(callback)
    
    def submit(self, packet: DataPacket):
        """Submit packet for async processing"""
        self._input_queue.put(packet)
    
    def process_sync(self, packet: DataPacket) -> DataPacket:
        """Process packet synchronously through all stages"""
        start_time = time.time()
        
        try:
            for stage in PipelineStage:
                packet = self._process_stage(packet, stage)
                if packet.has_errors:
                    break
            
            # Record statistics
            latency = (time.time() - start_time) * 1000
            self._record_completion(packet, latency)
            
            # Notify callbacks
            for callback in self._on_complete:
                try:
                    callback(packet)
                except Exception:
                    pass
                    
        except Exception as e:
            packet.errors.append(str(e))
            self._stats['packets_failed'] += 1
            
            for callback in self._on_error:
                try:
                    callback(packet, e)
                except Exception:
                    pass
        
        return packet

    
    def _process_loop(self):
        """Background processing loop"""
        while self._running:
            try:
                packet = self._input_queue.get(timeout=0.1)
                result = self.process_sync(packet)
                self._output_queue.put(result)
            except Empty:
                continue
            except Exception as e:
                print(f"Pipeline error: {e}")
    
    def _process_stage(self, packet: DataPacket, 
                       stage: PipelineStage) -> DataPacket:
        """Process packet through a single stage"""
        stage_start = time.time()
        packet.stage = stage
        
        with self._data_lock:
            processors = self._processors[stage].copy()
        
        for processor in processors:
            try:
                packet = processor(packet)
            except Exception as e:
                packet.errors.append(f"{stage.name}: {str(e)}")
        
        packet.processing_times[stage.name] = (time.time() - stage_start) * 1000
        return packet
    
    def _record_completion(self, packet: DataPacket, latency_ms: float):
        """Record successful completion"""
        with self._data_lock:
            self._stats['packets_processed'] += 1
            
            # Track payload size
            if packet.payload:
                try:
                    size = len(str(packet.payload))
                    self._stats['bytes_processed'] += size
                except Exception:
                    pass
            
            # Track latency
            self._latencies.append(latency_ms)
            if len(self._latencies) > 1000:
                self._latencies = self._latencies[-1000:]
            self._stats['avg_latency_ms'] = sum(self._latencies) / len(self._latencies)
    
    def get_result(self, timeout: float = 1.0) -> Optional[DataPacket]:
        """Get processed result from output queue"""
        try:
            return self._output_queue.get(timeout=timeout)
        except Empty:
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        with self._data_lock:
            return {
                **self._stats,
                'input_queue_size': self._input_queue.qsize(),
                'output_queue_size': self._output_queue.qsize(),
                'processors': {
                    stage.name: len(procs) 
                    for stage, procs in self._processors.items()
                }
            }
    
    def create_packet(self, payload: Any, source: str = "user",
                      destination: str = "synthesis",
                      data_type: str = "generic",
                      **metadata) -> DataPacket:
        """Convenience method to create a data packet"""
        return DataPacket(
            payload=payload,
            source=source,
            destination=destination,
            data_type=data_type,
            metadata=metadata
        )
