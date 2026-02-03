#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Terminal Launcher
Phase 1: Core Engine

Double-click this file or run: python launch_terminal.py

This launches the Git Bash-style terminal widget standalone.
Includes automatic Low Memory Mode detection.
"""

import sys
import os

# Ensure we can find our modules
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# Fix Windows encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def check_memory_conditions():
    """
    Check memory before launching and warn user if low.
    Returns: (can_start: bool, mode_name: str, message: str)
    """
    try:
        from core.low_memory_mode import check_startup_memory, MemoryMode
        
        startup = check_startup_memory()
        
        print("\n📊 MEMORY CHECK:")
        print(f"   Total RAM:  {startup['total_gb']:.1f} GB")
        print(f"   Used:       {startup['used_gb']:.1f} GB ({startup['percent_used']:.0f}%)")
        print(f"   Free:       {startup['free_gb']:.1f} GB")
        
        mode = startup['recommended_mode']
        can_start = startup['can_start']
        warning = startup.get('warning')
        
        # Mode-specific messages
        if mode == MemoryMode.CRITICAL:
            print("\n⚠️  CRITICAL MEMORY WARNING!")
            print("   Your system has very little free RAM.")
            print("   Frankenstein will run in CRITICAL (survival) mode.")
            print("\n   Recommendations:")
            print("   • Close Claude Desktop app (~1.6 GB RAM)")
            print("   • Close browser tabs")
            print("   • Close other applications")
            if not can_start:
                print("\n❌ Cannot start - less than 500MB free RAM!")
                print("   Please free up memory and try again.")
                return False, mode.value, warning
                
        elif mode == MemoryMode.LOW_MEMORY:
            print("\n🟠 LOW MEMORY MODE")
            print("   Running with minimal features to conserve RAM.")
            print("   • Security monitor: DISABLED")
            print("   • Polling interval: 15 seconds")
            print("   Use 'lowmem status' for details.")
            
        elif mode == MemoryMode.CONSERVATIVE:
            print("\n🟡 CONSERVATIVE MODE")
            print("   Running with reduced features.")
            print("   Use 'lowmem normal' if you free up RAM.")
            
        else:  # NORMAL
            print("\n🟢 NORMAL MODE")
            print("   Full features enabled.")
        
        return can_start, mode.value, warning
        
    except ImportError as e:
        # Low memory module not available - continue anyway
        print(f"\n⚠️  Memory check unavailable: {e}")
        print("   Continuing with default settings...")
        return True, "unknown", None
    except Exception as e:
        print(f"\n⚠️  Memory check error: {e}")
        return True, "unknown", None


def show_top_memory_consumers():
    """Show what's using the most RAM"""
    try:
        import psutil
        
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                mem_mb = proc.info['memory_info'].rss / (1024 * 1024)
                if mem_mb > 50:  # Only show processes using > 50MB
                    processes.append((proc.info['name'], mem_mb))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Sort by memory and show top 5
        processes.sort(key=lambda x: x[1], reverse=True)
        
        if processes:
            print("\n📈 TOP MEMORY CONSUMERS:")
            for name, mem in processes[:5]:
                print(f"   {name:<25} {mem:>7.0f} MB")
                
    except ImportError:
        pass  # psutil not available
    except Exception:
        pass  # Ignore errors


def main():
    print("=" * 55)
    print("  ⚡ FRANKENSTEIN 1.0 - Terminal Launcher ⚡")
    print("=" * 55)
    
    # Check for customtkinter first
    try:
        import customtkinter
        print("✓ customtkinter found")
    except ImportError:
        print("❌ customtkinter not found!")
        print("\nInstall it with: pip install customtkinter")
        input("\nPress Enter to exit...")
        return 1
    
    # Check for psutil (needed for memory monitoring)
    try:
        import psutil
        print("✓ psutil found")
    except ImportError:
        print("⚠️ psutil not found - memory monitoring disabled")
        print("  Install it with: pip install psutil")
    
    # Check memory conditions BEFORE launching
    can_start, mode, warning = check_memory_conditions()
    
    if not can_start:
        print("\n" + "=" * 55)
        show_top_memory_consumers()
        print("\n" + "=" * 55)
        input("\nPress Enter to exit...")
        return 1
    
    # Show top memory consumers if in low memory mode
    if mode in ('low_memory', 'critical'):
        show_top_memory_consumers()
    
    print("\n" + "-" * 55)
    
    # Launch terminal
    try:
        from terminal import FrankensteinTerminal, launch_terminal
        print("✓ Terminal module loaded")
        print(f"✓ Memory mode: {mode.upper()}")
        print("\n🚀 Launching terminal window...")
        print("(Close this console or press Ctrl+C to exit)\n")
        
        terminal = launch_terminal()
        
        # Keep main thread alive
        import time
        while terminal._running:
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
