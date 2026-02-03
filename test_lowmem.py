#!/usr/bin/env python3
"""Test Low Memory Mode"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix Windows encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

from core.low_memory_mode import (
    get_low_memory_manager, 
    check_startup_memory, 
    MemoryMode,
    MODE_CONFIGS
)
import time

print("=" * 60)
print("LOW MEMORY MODE TEST")
print("=" * 60)

# Check startup conditions
print("\n--- Startup Memory Check ---")
startup = check_startup_memory()
print(f"Total RAM:        {startup['total_gb']} GB")
print(f"Used:             {startup['used_gb']} GB ({startup['percent_used']}%)")
print(f"Free:             {startup['free_gb']} GB")
print(f"Recommended Mode: {startup['recommended_mode'].value}")
if startup['warning']:
    print(f"Warning:          {startup['warning']}")

# Initialize manager
print("\n--- Manager Test ---")
mgr = get_low_memory_manager()
mgr.start()
time.sleep(1)

status = mgr.get_status()
print(f"Current Mode:     {status['mode']}")
print(f"Auto-Detect:      {status['auto_detect']}")
print(f"Memory Used:      {status['last_memory_percent']}%")
print(f"Memory Free:      {status['last_free_gb']} GB")

# Get settings
settings = mgr.get_settings()
print(f"\n--- Current Mode Settings ---")
print(f"Resource Poll:    {settings.resource_poll_interval}s")
print(f"UI Update:        {settings.ui_update_interval}ms")
print(f"Security:         {'Enabled' if settings.enable_security_monitor else 'Disabled'}")
print(f"Synthesis:        {'Enabled' if settings.enable_synthesis_engine else 'Disabled'}")
print(f"Quantum:          {'Enabled' if settings.enable_quantum_mode else 'Disabled'}")
print(f"Max Output:       {settings.max_output_lines} lines")

# Get recommendations
recs = mgr.get_recommendations()
if recs:
    print(f"\n--- Recommendations ---")
    for i, r in enumerate(recs, 1):
        print(f"  {i}. {r}")

# Test mode switching
print(f"\n--- Mode Switching Test ---")
print(f"Before: {mgr.get_mode().value}")
mgr.set_mode(MemoryMode.LOW_MEMORY)
print(f"After set_mode(LOW_MEMORY): {mgr.get_mode().value}")
mgr.clear_override()
time.sleep(0.5)
print(f"After clear_override(): {mgr.get_mode().value}")

mgr.stop()

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
