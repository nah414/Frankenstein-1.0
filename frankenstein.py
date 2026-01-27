#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Main Entry Point
Phase 1: Core Engine

A quantum-classical hybrid AI system with monster branding.

Usage:
    python frankenstein.py              # Start terminal GUI (recommended)
    python frankenstein.py --console    # Start console-only mode
    python frankenstein.py --status     # Show system status
    python frankenstein.py --test       # Run quick system test
"""

import sys
import os
import time
import argparse
from pathlib import Path

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    os.system('chcp 65001 > nul 2>&1')
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

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
    banner = r"""
    +===========================================================+
    |                                                           |
    |    FRANKENSTEIN 1.0 - Phase 1: Core Engine                |
    |    Quantum-Classical Hybrid AI System                     |
    |    Target: Dell i3 8th Gen (Tier 1)                       |
    |                                                           |
    |    [!] Monster Mode Active                                |
    |                                                           |
    +===========================================================+
    """
    print(banner)


def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def initialize_systems(verbose: bool = True):
    """Initialize all core systems"""
    if verbose:
        print("\n[*] Initializing FRANKENSTEIN systems...")

    # Initialize memory
    memory = get_memory()
    if verbose:
        print("  [+] Memory system initialized")

    # Start governor
    governor = get_governor()
    governor.start()
    if verbose:
        print("  [+] Resource Governor started")

    # Start orchestrator
    orchestrator = get_orchestrator()
    orchestrator.start()
    if verbose:
        print("  [+] Task Orchestrator started")

    if verbose:
        # Verify safety constraints
        constraints = get_constraints_dict()
        print(f"\n[!] Safety Constraints (Tier 1):")
        print(f"    Max CPU: {constraints['max_cpu_percent']}%")
        print(f"    Max Memory: {constraints['max_memory_percent']}%")
        print(f"    Worker Threads: {constraints['max_worker_threads']}")
        print(f"    Auto-Throttle: {'ON' if constraints['auto_throttle'] else 'OFF'}")

    return governor, memory, orchestrator


def shutdown_systems(governor, orchestrator, memory, verbose: bool = True):
    """Shutdown all systems gracefully"""
    if verbose:
        print("\nShutting down FRANKENSTEIN...")
    governor.stop()
    orchestrator.stop()
    memory.shutdown()
    if verbose:
        print("[OK] Shutdown complete.")


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
    print(" FRANKENSTEIN 1.0 - SYSTEM STATUS")
    print("=" * 60)

    safe_indicator = "[SAFE]" if gov_status['safe'] else "[THROTTLED]"
    print(f"\n[HARDWARE RESOURCES] {safe_indicator}")
    print(f"  CPU Usage:      {gov_status['cpu_percent']}%")
    total_ram = gov_status['memory_used_gb'] + gov_status['memory_available_gb']
    print(f"  Memory Usage:   {gov_status['memory_percent']}% ({gov_status['memory_used_gb']:.2f}GB / {total_ram:.2f}GB)")
    print(f"  Throttle Level: {gov_status['throttle_level']}")
    print(f"  Violations:     {gov_status['total_violations']}")

    print(f"\n[SESSION]")
    print(f"  Session ID:     {mem_status.get('session_id', 'N/A')}")
    print(f"  Uptime:         {mem_status.get('uptime_human', 'N/A')}")
    print(f"  Tasks Total:    {mem_status.get('task_count', 0)}")
    print(f"  Success Rate:   {mem_status.get('success_rate_percent', 0):.1f}%")

    print(f"\n[TASK QUEUE]")
    print(f"  Running:        {'Yes' if queue_status['running'] else 'No'}")
    print(f"  Active Tasks:   {queue_status['active_tasks']}")
    print(f"  Max Workers:    {queue_status['max_workers']}")

    print(f"\n[STORAGE]")
    print(f"  Usage:          {storage['total_mb']:.2f}MB / {storage['limit_gb']}GB")

    print("\n" + "=" * 60)
    print()


def run_test():
    """Run a quick system test"""
    print_banner()
    print("\n[*] Running system test...\n")

    governor, memory, orchestrator = initialize_systems()

    print("\n[TEST 1] Submit simple task")
    task_id = orchestrator.submit(
        TaskType.CLASSICAL,
        {"test": "hello", "value": 42},
        TaskPriority.NORMAL
    )
    print(f"  Task submitted: {task_id}")

    time.sleep(2)

    task_status = orchestrator.get_task_status(task_id)
    print(f"  Task status: {task_status['status']}")

    print("\n[TEST 2] Resource monitoring")
    gov_status = governor.get_status()
    print(f"  CPU: {gov_status['cpu_percent']}%")
    print(f"  RAM: {gov_status['memory_percent']}%")
    print(f"  Safe: {'YES' if gov_status['safe'] else 'NO (throttled)'}")

    print("\n[OK] System test complete!")
    shutdown_systems(governor, orchestrator, memory)


def process_command(command: str, governor, memory, orchestrator) -> str:
    """Process a command and return the result"""
    cmd = command.lower().strip()
    
    if cmd in ['help', '?']:
        return '''
Available Commands:
  help        - Show this help
  status      - Show system status
  clear       - Clear screen
  quit/exit   - Exit FRANKENSTEIN
  
Task Commands:
  task <msg>  - Submit a task
  queue       - Show queue status
  
System Commands:
  stop        - Emergency stop all tasks
  cpu         - Show CPU usage
  ram         - Show RAM usage
'''
    
    elif cmd in ['status', 'stats', 's']:
        gov_status = governor.get_status()
        mem_status = memory.get_session_stats()
        return f'''
=== SYSTEM STATUS ===
CPU:      {gov_status['cpu_percent']:.1f}%
RAM:      {gov_status['memory_percent']:.1f}%
Status:   {'SAFE' if gov_status['safe'] else 'THROTTLED'}
Throttle: {gov_status['throttle_level']}
Tasks:    {mem_status.get('task_count', 0)} total
Uptime:   {mem_status.get('uptime_human', 'N/A')}
'''
    
    elif cmd in ['cpu']:
        gov_status = governor.get_status()
        return f"CPU Usage: {gov_status['cpu_percent']:.1f}%"
    
    elif cmd in ['ram', 'mem', 'memory']:
        gov_status = governor.get_status()
        return f"RAM Usage: {gov_status['memory_percent']:.1f}% ({gov_status['memory_used_gb']:.2f}GB used)"
    
    elif cmd in ['queue', 'q']:
        queue_status = orchestrator.get_queue_status()
        return f'''
=== TASK QUEUE ===
Running:   {'Yes' if queue_status['running'] else 'No'}
Active:    {queue_status['active_tasks']}
Queued:    {queue_status['queue_size']}
Completed: {queue_status['completed_tasks']}
Workers:   {queue_status['max_workers']}
'''
    
    elif cmd in ['stop', 'halt', 'emergency']:
        governor.emergency_stop()
        orchestrator.stop(wait=False)
        return "[!] EMERGENCY STOP - All operations halted"
    
    elif cmd.startswith('task '):
        task_data = command[5:].strip()
        task_id = orchestrator.submit(
            TaskType.CLASSICAL,
            {"command": task_data}
        )
        return f"[+] Task submitted: {task_id}"
    
    elif cmd in ['clear', 'cls']:
        return '__CLEAR__'
    
    elif cmd in ['quit', 'exit', 'q!']:
        return '__QUIT__'
    
    else:
        # Submit unknown commands as tasks
        task_id = orchestrator.submit(
            TaskType.CLASSICAL,
            {"command": command}
        )
        return f"[+] Task submitted: {task_id}"


def start_terminal_gui():
    """Start the GUI terminal widget"""
    try:
        from widget.terminal import get_terminal, CTK_AVAILABLE
        
        if not CTK_AVAILABLE:
            print("[ERROR] customtkinter not installed.")
            print("        Install with: pip install customtkinter")
            print("        Falling back to console mode...")
            return start_console()
        
    except ImportError as e:
        print(f"[ERROR] Failed to import terminal widget: {e}")
        print("        Falling back to console mode...")
        return start_console()
    
    # Initialize systems (quiet mode)
    governor, memory, orchestrator = initialize_systems(verbose=False)
    
    # Create terminal
    terminal = get_terminal()
    
    # Set command callback
    def command_handler(cmd):
        result = process_command(cmd, governor, memory, orchestrator)
        if result == '__CLEAR__':
            terminal.clear()
            return None
        elif result == '__QUIT__':
            terminal.stop()
            return None
        return result
    
    terminal.set_command_callback(command_handler)
    
    # Start status update thread
    def update_status():
        while terminal._running:
            try:
                status = governor.get_status()
                terminal.update_status(
                    status['cpu_percent'],
                    status['memory_percent'],
                    status['safe']
                )
            except Exception:
                pass
            time.sleep(1)
    
    status_thread = threading.Thread(target=update_status, daemon=True)
    status_thread.start()
    
    # Start terminal
    if not terminal.start():
        print("[ERROR] Failed to start terminal widget")
        shutdown_systems(governor, orchestrator, memory, verbose=False)
        return
    
    # Wait for terminal to close
    while terminal._running:
        time.sleep(0.5)
    
    # Shutdown
    shutdown_systems(governor, orchestrator, memory, verbose=False)


def start_console():
    """Start console/REPL mode (no GUI)"""
    clear_screen()
    print_banner()
    
    governor, memory, orchestrator = initialize_systems()

    print("\n[OK] FRANKENSTEIN 1.0 Ready!")
    print("Type 'help' for commands, 'quit' to exit.\n")

    try:
        while True:
            try:
                command = input("frankenstein> ").strip()
            except EOFError:
                break

            if not command:
                continue

            result = process_command(command, governor, memory, orchestrator)
            
            if result == '__CLEAR__':
                clear_screen()
                print_banner()
            elif result == '__QUIT__':
                break
            elif result:
                print(result)

    except KeyboardInterrupt:
        print("\n\n[!] Interrupted by user")

    shutdown_systems(governor, orchestrator, memory)


# Import threading for status updates
import threading


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="FRANKENSTEIN 1.0 - Quantum-Classical Hybrid AI System"
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="Start in console mode (no GUI)"
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
    elif args.console:
        start_console()
    else:
        # Default: GUI terminal
        start_terminal_gui()


if __name__ == "__main__":
    main()
