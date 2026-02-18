#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Terminal Launcher

Double-click this file or run: python launch_terminal.py

This launches the Git Bash-style terminal widget standalone.
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

def main():
    print("🧟 FRANKENSTEIN 1.0 - Terminal Launcher")
    print("=" * 50)
    
    # Check for customtkinter
    try:
        import customtkinter
        print("✓ customtkinter found")
    except ImportError:
        print("❌ customtkinter not found!")
        print("\nInstall it with: pip install customtkinter")
        input("\nPress Enter to exit...")
        return 1
    
    # Launch terminal
    try:
        # Start resource governor first (critical safety monitor)
        from core import get_governor
        governor = get_governor()
        governor.start()
        print("✓ Resource Governor started")

        from widget.terminal import launch_terminal
        print("✓ Terminal module loaded")
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
