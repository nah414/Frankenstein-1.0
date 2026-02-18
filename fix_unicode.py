#!/usr/bin/env python3
"""Fix all Unicode special characters in terminal.py help text."""

filepath = "widget/terminal.py"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all problematic Unicode characters
replacements = {
    '═': '=',     # Box drawing
    '⟩': '>',     # Angle bracket
    '⟨': '<',     # Angle bracket  
    '│': '|',     # Vertical line
    '┌': '+',     # Corner
    '└': '+',     # Corner
    '┐': '+',     # Corner
    '┘': '+',     # Corner
    '─': '-',     # Horizontal line
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("[OK] Fixed all Unicode characters in widget/terminal.py")
