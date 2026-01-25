#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Main Entry Point
Phase 1: Core Engine

Usage:
    python frankenstein.py              # Start with default config
    python frankenstein.py --widget     # Start with widget overlay
    python frankenstein.py --status     # Show system status
    python frankenstein.py --test       # Run quick system test
"""

import sys
import time
import argparse
from pathlib import Path

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core import (
    get_governor,
    get_memory,
    get_orchestrator,
    TaskType,
    TaskPriority,
    SAFETY,
    get_constraints_dict
)


def print_banner():
    """Print FRANKENSTEIN banner"""
    banner = """
    ⚡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━⚡

         ███████╗██████╗  █████╗ ███╗   ██╗██╗  ██╗
         ██╔════╝██╔══██╗██╔══██╗████╗  ██║██║ ██╔╝
         █████╗  ██████╔╝███████║██╔██╗ ██║█████╔╝
         ██╔══╝  ██╔══██╗██╔══██║██║╚██╗██║██╔═██╗
         ██║     ██║  ██║██║  ██║██║ ╚████║██║  ██╗
         ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝

              FRANKENSTEIN 1.0 - Phase 1: Core Engine
           Quantum-Classical Hybrid AI System
           Optimized for Dell i3 8th Gen (Tier 1)

    ⚡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━⚡
    """
    print(banner)


def initialize_systems():
    """Initialize all core systems"""
    print("\n🔧 Initializing FRANKENSTEIN systems...")

    # Initialize memory
    memory = get_memory()
    print("  ✓ Memory system initialized")

    # Start governor
    governor = get_governor()
    governor.start()
    print("  ✓ Resource Governor started")

    # Start orchestrator
    orchestrator = get_orchestrator()
    orchestrator.start()
    print("  ✓ Task Orchestrator started")

    # Verify safety constraints
    constraints = get_constraints_dict()
    print(f"\n🛡️  Safety Constraints (Tier 1):")
    print(f"  • Max CPU: {constraints['max_cpu_percent']}%")
    print(f"  • Max Memory: {constraints['max_memory_percent']}%")
    print(f"  • Worker Threads: {constraints['max_worker_threads']}")
    print(f"  • Storage Budget: {constraints['max_storage_use_gb']}GB")
    print(f"  • Auto-Throttle: {constraints['auto_throttle']}")

    return governor, memory, orchestrator


def show_status():
    """Show detailed system status"""
    print_banner()

    governor = get_governor()
    memory = get_memory()
    orchestrator = get_orchestrator()

    # Start systems if not running
    if not governor._running:
        governor.start()
    if not orchestrator._running:
        orchestrator.start()

    time.sleep(1)  # Allow initial readings

    # Get status
    gov_status = governor.get_status()
    mem_status = memory.get_session_stats()
    queue_status = orchestrator.get_queue_status()
    storage = memory.get_storage_usage()

    print("\n" + "=" * 60)
    print("⚡ FRANKENSTEIN 1.0 - SYSTEM STATUS")
    print("=" * 60)

    print(f"\n🖥️  HARDWARE RESOURCES:")
    print(f"  CPU Usage:      {gov_status['cpu_percent']}%")
    print(f"  Memory Usage:   {gov_status['memory_percent']}% ({gov_status['memory_used_gb']:.2f}GB / {gov_status['memory_used_gb'] + gov_status['memory_available_gb']:.2f}GB)")
    print(f"  Memory Free:    {gov_status['memory_available_gb']:.2f}GB")
    print(f"  Disk I/O:       {gov_status['disk_io_mbps']:.1f} MB/s")
    print(f"  Status:         {'🟢 SAFE' if gov_status['safe'] else '🟡 THROTTLED'}")
    print(f"  Throttle Level: {gov_status['throttle_level']}")
    print(f"  Violations:     {gov_status['total_violations']}")

    print(f"\n📊 SESSION:")
    print(f"  Session ID:     {mem_status.get('session_id', 'N/A')}")
    print(f"  Uptime:         {mem_status.get('uptime_human', 'N/A')}")
    print(f"  Tasks Total:    {mem_status.get('task_count', 0)}")
    print(f"  Tasks Success:  {mem_status.get('successful_tasks', 0)}")
    print(f"  Tasks Failed:   {mem_status.get('failed_tasks', 0)}")
    print(f"  Success Rate:   {mem_status.get('success_rate_percent', 0):.1f}%")
    print(f"  Compute Time:   {mem_status.get('total_compute_time_sec', 0):.1f}s")

    print(f"\n⚙️  TASK QUEUE:")
    print(f"  Running:        {'Yes' if queue_status['running'] else 'No'}")
    print(f"  Active Tasks:   {queue_status['active_tasks']}")
    print(f"  Queued Tasks:   {queue_status['queue_size']}")
    print(f"  Completed:      {queue_status['completed_tasks']}")
    print(f"  Max Workers:    {queue_status['max_workers']}")

    print(f"\n💾 STORAGE:")
    print(f"  Memory Usage:   {storage['total_mb']:.2f}MB ({storage['total_gb']:.3f}GB)")
    print(f"  Storage Limit:  {storage['limit_gb']}GB")
    print(f"  Usage:          {storage['usage_percent']:.1f}%")

    print("\n" + "=" * 60)
    print()


def run_test():
    """Run a quick system test"""
    print_banner()
    print("\n🧪 Running system test...\n")

    governor, memory, orchestrator = initialize_systems()

    print("\n📝 Test 1: Submit simple task")
    task_id = orchestrator.submit(
        TaskType.CLASSICAL,
        {"test": "hello", "value": 42},
        TaskPriority.NORMAL
    )
    print(f"  Task submitted: {task_id}")

    # Wait for completion
    time.sleep(2)

    task_status = orchestrator.get_task_status(task_id)
    print(f"  Task status: {task_status['status']}")
    print(f"  Task result: {task_status.get('result', 'N/A')}")

    print("\n📝 Test 2: System health check")
    health_task_id = orchestrator.submit(
        TaskType.SYSTEM,
        {"action": "health_check"},
        TaskPriority.HIGH
    )

    time.sleep(2)
    health_status = orchestrator.get_task_status(health_task_id)
    print(f"  Health check: {health_status['status']}")

    print("\n📝 Test 3: Resource monitoring")
    gov_status = governor.get_status()
    print(f"  CPU: {gov_status['cpu_percent']}%")
    print(f"  RAM: {gov_status['memory_percent']}%")
    print(f"  Safe: {gov_status['safe']}")

    print("\n✅ System test complete!")
    print("\nShutting down...")
    governor.stop()
    orchestrator.stop()
    memory.shutdown()


def start_interactive():
    """Start interactive mode"""
    print_banner()
    governor, memory, orchestrator = initialize_systems()

    print("\n✅ FRANKENSTEIN 1.0 is ready!")
    print("\nCommands:")
    print("  status  - Show system status")
    print("  quit    - Shutdown and exit")
    print()

    try:
        while True:
            command = input("frankenstein> ").strip().lower()

            if command in ['quit', 'exit', 'q']:
                break
            elif command in ['status', 'stats']:
                show_status()
            elif command:
                # Submit as task
                task_id = orchestrator.submit(
                    TaskType.CLASSICAL,
                    {"command": command}
                )
                print(f"Task submitted: {task_id}")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")

    print("\nShutting down...")
    governor.stop()
    orchestrator.stop()
    memory.shutdown()
    print("✓ Shutdown complete")


def start_with_widget():
    """Start with widget overlay"""
    try:
        from widget.overlay import get_widget
    except ImportError:
        print("❌ Widget not available. Install customtkinter:")
        print("   pip install customtkinter")
        return

    print_banner()
    governor, memory, orchestrator = initialize_systems()

    print("\n🎮 Starting widget overlay...")
    widget = get_widget()

    if not widget.start():
        print("❌ Failed to start widget")
        return

    print("✅ Widget started! (Always-on-top window)")
    print("\nPress Ctrl+C to exit\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down...")

    widget.stop()
    governor.stop()
    orchestrator.stop()
    memory.shutdown()
    print("✓ Shutdown complete")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="FRANKENSTEIN 1.0 - Quantum-Classical Hybrid AI System"
    )
    parser.add_argument(
        "--widget",
        action="store_true",
        help="Start with widget overlay"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show system status and exit"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run quick system test"
    )

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.test:
        run_test()
    elif args.widget:
        start_with_widget()
    else:
        start_interactive()


if __name__ == "__main__":
    main()
