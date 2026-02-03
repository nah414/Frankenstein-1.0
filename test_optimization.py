#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Resource Optimization Test
Run this to verify the optimizations are working.
"""

import sys
import os

# Fix Windows encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_resource_manager():
    """Test the optimized resource manager"""
    print("\n=== Testing Resource Manager ===")
    try:
        from core.resource_manager import (
            get_resource_manager, 
            MonitorState,
            AdaptiveResourceManager
        )
        
        # Check intervals
        print(f"  IDLE interval:     {AdaptiveResourceManager.INTERVALS[MonitorState.IDLE]}s (expect 8.0)")
        print(f"  ACTIVE interval:   {AdaptiveResourceManager.INTERVALS[MonitorState.ACTIVE]}s (expect 4.0)")
        print(f"  ALERT interval:    {AdaptiveResourceManager.INTERVALS[MonitorState.ALERT]}s (expect 2.0)")
        print(f"  CRITICAL interval: {AdaptiveResourceManager.INTERVALS[MonitorState.CRITICAL]}s (expect 1.0)")
        
        # Test instance
        manager = get_resource_manager()
        print(f"  Cache TTL:         {manager._cache_ttl}s (expect 1.0)")
        print(f"  Max CPU:           {manager.MAX_CPU}%")
        print(f"  Max Memory:        {manager.MAX_MEMORY}%")
        
        # Start and get sample
        manager.start()
        import time
        time.sleep(0.5)
        
        sample = manager.get_sample()
        if sample:
            print(f"  Current CPU:       {sample.cpu_percent:.1f}%")
            print(f"  Current Memory:    {sample.memory_percent:.1f}%")
            print(f"  Is Safe:           {manager.is_safe()}")
        
        manager.stop()
        print("  ✅ Resource Manager OK")
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_agent_scheduler():
    """Test the new agent scheduler"""
    print("\n=== Testing Agent Scheduler ===")
    try:
        from core.agent_scheduler import (
            get_scheduler,
            AgentScheduler,
            AgentPriority
        )
        
        # Check limits
        print(f"  Max Concurrent:    {AgentScheduler.MAX_CONCURRENT_AGENTS}")
        print(f"  Throttle CPU:      {AgentScheduler.THROTTLE_CPU_THRESHOLD}%")
        print(f"  Throttle Memory:   {AgentScheduler.THROTTLE_MEM_THRESHOLD}%")
        print(f"  Critical CPU:      {AgentScheduler.CRITICAL_CPU_THRESHOLD}%")
        print(f"  Critical Memory:   {AgentScheduler.CRITICAL_MEM_THRESHOLD}%")
        
        # Test instance
        scheduler = get_scheduler()
        scheduler.start()
        
        import time
        time.sleep(0.5)
        
        status = scheduler.get_status()
        print(f"  Running:           {status['running']}")
        print(f"  Throttle Level:    {status['throttle_level']} ({status['throttle_desc']})")
        print(f"  Active Tasks:      {status['active_tasks']}")
        
        # Test scheduling a simple task
        def dummy_task():
            pass
        
        success = scheduler.schedule(
            "test_task",
            dummy_task,
            priority=AgentPriority.LOW,
            estimated_cpu=5.0,
            estimated_memory=2.0
        )
        print(f"  Schedule Task:     {'✅' if success else '❌'}")
        
        scheduler.stop()
        print("  ✅ Agent Scheduler OK")
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_terminal_imports():
    """Test that terminal imports work"""
    print("\n=== Testing Terminal Imports ===")
    try:
        from terminal import FrankensteinTerminal
        
        terminal = FrankensteinTerminal()
        print(f"  Terminal created:  ✅")
        print(f"  Commands:          {len(terminal._commands)}")
        print(f"  Has 'resources':   {'resources' in terminal._commands}")
        print(f"  Has 'res':         {'res' in terminal._commands}")
        print("  ✅ Terminal Imports OK")
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("FRANKENSTEIN 1.0 - Resource Optimization Test")
    print("=" * 60)
    
    results = []
    results.append(("Resource Manager", test_resource_manager()))
    results.append(("Agent Scheduler", test_agent_scheduler()))
    results.append(("Terminal Imports", test_terminal_imports()))
    
    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + ("✅ All tests passed!" if all_passed else "❌ Some tests failed"))
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
