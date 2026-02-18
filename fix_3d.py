#!/usr/bin/env python3
"""Fix 3D literal issues in terminal.py."""

filepath = "widget/terminal.py"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace 3D with three-dimensional
content = content.replace('3D', 'three-dimensional')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("[OK] Fixed 3D literals in widget/terminal.py")
