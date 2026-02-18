#!/usr/bin/env python3
"""
Quick test to verify Git enhancements are active in terminal.py
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("FRANKENSTEIN GIT ENHANCEMENTS - VERIFICATION TEST")
print("=" * 60)

try:
    from widget.terminal import FrankensteinTerminal
    print("\n✓ Terminal module imported successfully")

    # Create instance
    term = FrankensteinTerminal()
    print("✓ Terminal instance created")

    # Check for Git enhancement methods
    print("\n📊 Checking for Git enhancement methods:")
    methods = ['_git_clone', '_git_status', '_git_log', '_git_branch', '_git_remote', '_git_progress']

    all_present = True
    for method in methods:
        has_method = hasattr(term, method)
        status = "✅" if has_method else "❌"
        print(f"  {status} {method}: {'Present' if has_method else 'MISSING'}")
        if not has_method:
            all_present = False

    # Check for 're' import
    print("\n📊 Checking for required imports:")
    import widget.terminal as terminal_module
    has_re = 're' in dir(terminal_module)
    print(f"  {'✅' if has_re else '❌'} 're' module imported: {'Yes' if has_re else 'NO'}")

    # Summary
    print("\n" + "=" * 60)
    if all_present and has_re:
        print("✅ ALL GIT ENHANCEMENTS ARE ACTIVE!")
        print("\nYou should see:")
        print("  - Enhanced 'git' command with progress bars")
        print("  - Color-coded 'git status' with icons")
        print("  - Visual 'git log --graph'")
        print("  - Updated help menu with 'GIT (ENHANCED)'")
        print("\nTry running: python launch_terminal.py")
        print("Then in the terminal type: help")
    else:
        print("❌ SOME ENHANCEMENTS ARE MISSING!")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

input("\nPress Enter to exit...")
