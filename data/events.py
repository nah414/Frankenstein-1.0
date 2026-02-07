#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Event Bus System
Phase 2, Step 7: Pub/Sub Messaging

Purpose: Decoupled component communication via events
"""

import threading
import time
from datetime import datetime
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional
from queue import Queue, Empty
import uuid


class EventType(Enum):
    """All trackable event types in Frankenstein"""
    # System Events
    SYSTEM_START = auto()
    SYSTEM_STOP = auto()
    SYSTEM_ERROR = auto()
    SYSTEM_WARNING = auto()
    
    # Resource Events
    CPU_THRESHOLD = auto()
    MEMORY_THRESHOLD = auto()
    THROTTLE_ACTIVATED = auto()
    THROTTLE_DEACTIVATED = auto()
    
    # Security Events
    SECURITY_THREAT = auto()
    SECURITY_BLOCKED = auto()
    SECURITY_SCAN = auto()
    PROMPT_INJECTION = auto()
    
    # Synthesis Events
    SYNTHESIS_START = auto()
    SYNTHESIS_COMPLETE = auto()
    SYNTHESIS_ERROR = auto()
    WAVE_FUNCTION_CREATED = auto()
    WAVE_FUNCTION_EVOLVED = auto()
    WAVE_FUNCTION_COLLAPSED = auto()
    
    # Quantum Events
    QUANTUM_CIRCUIT_CREATED = auto()
    QUANTUM_GATE_APPLIED = auto()
    QUANTUM_MEASUREMENT = auto()
    BLOCH_SPHERE_RENDERED = auto()
    
    # Agent Events
    AGENT_STARTED = auto()
    AGENT_COMPLETED = auto()
    AGENT_ERROR = auto()
    SWARM_CREATED = auto()
    SWARM_TASK_DISTRIBUTED = auto()
    
    # Pipeline Events
    PIPELINE_DATA_IN = auto()
    PIPELINE_DATA_OUT = auto()
    PIPELINE_STAGE_COMPLETE = auto()
    PIPELINE_ERROR = auto()
    
    # Terminal Events
    COMMAND_EXECUTED = auto()
    COMMAND_ERROR = auto()
    MODE_CHANGED = auto()
    
    # Telemetry Events
    METRICS_SNAPSHOT = auto()
    TELEMETRY_EXPORT = auto()


@dataclass
class Event:
    """Immutable event record"""
    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source: str = "system"
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.name,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'data': self.data
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'Event':
        """Create from dictionary"""
        return cls(
            event_id=d.get('event_id', str(uuid.uuid4())[:8]),
            event_type=EventType[d['event_type']],
            timestamp=datetime.fromisoformat(d['timestamp']),
            source=d.get('source', 'system'),
            data=d.get('data', {})
        )


class EventBus:
    """
    Central pub/sub event bus for Frankenstein
    
    Features:
    - Async event dispatch
    - Multiple subscribers per event type
    - Event history for replay/debugging
    - Thread-safe operation
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern for global event bus"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._subscribers: Dict[EventType, List[Callable[[Event], None]]] = {}
        self._history: List[Event] = []
        self._history_limit = 10000
        self._event_queue: Queue = Queue()
        self._running = False
        self._dispatch_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._initialized = True
    
    def start(self):
        """Start the event dispatch thread"""
        if self._running:
            return
        self._running = True
        self._dispatch_thread = threading.Thread(
            target=self._dispatch_loop,
            daemon=True,
            name="EventBus-Dispatch"
        )
        self._dispatch_thread.start()
    
    def stop(self):
        """Stop the event dispatch thread"""
        self._running = False
        if self._dispatch_thread:
            self._dispatch_thread.join(timeout=1.0)
    
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """Subscribe to an event type"""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """Unsubscribe from an event type"""
        with self._lock:
            if event_type in self._subscribers:
                if callback in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(callback)

    
    def publish(self, event: Event):
        """Publish an event (async via queue)"""
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._history_limit:
                self._history = self._history[-self._history_limit:]
        self._event_queue.put(event)
    
    def publish_sync(self, event: Event):
        """Publish and dispatch immediately (synchronous)"""
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._history_limit:
                self._history = self._history[-self._history_limit:]
        self._dispatch_event(event)
    
    def emit(self, event_type: EventType, source: str = "system", **data):
        """Convenience method to create and publish an event"""
        event = Event(
            event_type=event_type,
            source=source,
            data=data
        )
        self.publish(event)
        return event
    
    def _dispatch_loop(self):
        """Background thread for async event dispatch"""
        while self._running:
            try:
                event = self._event_queue.get(timeout=0.1)
                self._dispatch_event(event)
            except Empty:
                continue
            except Exception as e:
                print(f"EventBus dispatch error: {e}")
    
    def _dispatch_event(self, event: Event):
        """Dispatch event to all subscribers"""
        with self._lock:
            subscribers = self._subscribers.get(event.event_type, []).copy()
        
        for callback in subscribers:
            try:
                callback(event)
            except Exception as e:
                print(f"EventBus subscriber error: {e}")
    
    def get_history(self, 
                    event_type: Optional[EventType] = None,
                    limit: int = 100,
                    since: Optional[datetime] = None) -> List[Event]:
        """Get event history with optional filters"""
        with self._lock:
            events = self._history.copy()
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        return events[-limit:]
    
    def clear_history(self):
        """Clear event history"""
        with self._lock:
            self._history.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        with self._lock:
            event_counts = {}
            for event in self._history:
                name = event.event_type.name
                event_counts[name] = event_counts.get(name, 0) + 1
        
        return {
            'total_events': len(self._history),
            'subscriber_count': sum(len(s) for s in self._subscribers.values()),
            'event_types_active': len(self._subscribers),
            'queue_size': self._event_queue.qsize(),
            'event_counts': event_counts
        }
