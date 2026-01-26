"""
FRANKENSTEIN 1.0 - Main Entry Point
The Ultimate Scientific & Engineering Desktop Assistant

Usage:
    python frankenstein.py          # Launch with widget
    python frankenstein.py --cli    # CLI mode only (no widget)
    
"It's alive... and ready to serve science." ⚡
"""

import sys
import argparse
from core import get_governor, SAFETY, get_constraints_dict


def print_banner():
    """Print startup banner"""
    banner = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║     ███████╗██████╗  █████╗ ███╗   ██╗██╗  ██╗               ║
    ║     ██╔════╝██╔══██╗██╔══██╗████╗  ██║██║ ██╔╝               ║
    ║     █████╗  ██████╔╝███████║██╔██╗ ██║█████╔╝                ║
    ║     ██╔══╝  ██╔══██╗██╔══██║██║╚██╗██║██╔═██╗                ║
    ║     ██║     ██║  ██║██║  ██║██║ ╚████║██║  ██╗               ║
    ║     ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝               ║
    ║                                                               ║
    ║              ⚡ FRANKENSTEIN 1.0 ⚡                            ║
    ║        Physics-Grounded AI Desktop Assistant                  ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def run_cli_mode():
    """Run in CLI mode without widget"""
    print_banner()
    print()
    
    # Display safety constraints
    print("🛡️  Safety Constraints Active:")
    constraints = get_constraints_dict()
    print(f"    CPU Limit:      {constraints['max_cpu_percent']}%")
    print(f"    Memory Limit:   {constraints['max_memory_percent']}%")
    print(f"    GPU Limit:      {constraints['max_gpu_percent']}%")
    print(f"    Auto-Throttle:  {'Enabled' if constraints['auto_throttle'] else 'Disabled'}")
    print(f"    Emergency Stop: {'Enabled' if constraints['emergency_stop'] else 'Disabled'}")
    print()
    
    # Start resource governor
    governor = get_governor()
    governor.start()
    print("📊 Resource Governor: ACTIVE")
    
    # Get initial status
    status = governor.get_status()
    print(f"    Current CPU:    {status['cpu_percent']:.1f}%")
    print(f"    Current Memory: {status['memory_percent']:.1f}%")
    print(f"    System Safe:    {'✅ YES' if status['safe'] else '❌ NO'}")
    print()
    
    print("=" * 60)
    print("  CLI Mode - Press Ctrl+C to exit")
    print("  For GUI widget, run without --cli flag")
    print("=" * 60)
    print()
    
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\n\n⚡ FRANKENSTEIN shutting down...")
        governor.stop()
        print("Goodbye!")
        sys.exit(0)


def run_widget_mode():
    """Run with GUI widget"""
    print_banner()
    print()
    print("🚀 Launching FRANKENSTEIN Widget...")
    print()
    
    # Start resource governor in background
    governor = get_governor()
    governor.start()
    print("📊 Resource Governor: ACTIVE")
    
    # Import and launch widget
    try:
        from widget.overlay import launch_widget
        print("🖥️  Starting Widget Interface...")
        print()
        launch_widget()
    except ImportError as e:
        print(f"\n❌ Widget launch failed: {e}")
        print("\nRequired package missing. Install with:")
        print("    pip install customtkinter")
        print("\nFalling back to CLI mode...\n")
        run_cli_mode()
    except Exception as e:
        print(f"\n❌ Widget error: {e}")
        print("\nFalling back to CLI mode...\n")
        run_cli_mode()
    finally:
        governor.stop()
        print("\n⚡ FRANKENSTEIN shut down complete.")


def main():
    """Main entry point for FRANKENSTEIN"""
    parser = argparse.ArgumentParser(
        description="FRANKENSTEIN 1.0 - Physics-Grounded AI Desktop Assistant"
    )
    parser.add_argument(
        "--cli", 
        action="store_true",
        help="Run in CLI mode without GUI widget"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="FRANKENSTEIN 1.0.0 - Phase 1 Core Engine"
    )
    
    args = parser.parse_args()
    
    if args.cli:
        run_cli_mode()
    else:
        run_widget_mode()


if __name__ == "__main__":
    main()
