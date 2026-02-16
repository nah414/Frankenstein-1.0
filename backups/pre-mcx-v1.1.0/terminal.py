#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Terminal Widget

Purpose: Git Bash-style terminal emulator with local command execution
Platform: Windows 10+ (uses customtkinter)
Author: Frankenstein Project

Features:
- Git Bash-style command set (cd, ls, pwd, cat, echo, mkdir, etc.)
- Right-click context menu for copy/paste
- Proper focus handling (no disappearing on keyboard input)
- Command history with up/down arrows
- Windows 10+ compatibility
"""

import os
import re
import sys
import shutil
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    print("⚠️ customtkinter not installed. Run: pip install customtkinter")


class CommandHistory:
    """Manages command history for up/down arrow navigation"""
    
    def __init__(self, max_size: int = 100):
        self._history: List[str] = []
        self._max_size = max_size
        self._position = 0
    
    def add(self, command: str):
        """Add command to history"""
        if command and (not self._history or self._history[-1] != command):
            self._history.append(command)
            if len(self._history) > self._max_size:
                self._history.pop(0)
        self._position = len(self._history)
    
    def get_previous(self) -> Optional[str]:
        """Get previous command (up arrow)"""
        if self._history and self._position > 0:
            self._position -= 1
            return self._history[self._position]
        return None
    
    def get_next(self) -> Optional[str]:
        """Get next command (down arrow)"""
        if self._position < len(self._history) - 1:
            self._position += 1
            return self._history[self._position]
        elif self._position == len(self._history) - 1:
            self._position = len(self._history)
            return ""
        return None
    
    def reset_position(self):
        """Reset position to end of history"""
        self._position = len(self._history)


class FrankensteinTerminal:
    """
    Git Bash-style terminal emulator for Frankenstein 1.0
    
    Implements core Unix/Bash commands for Windows compatibility:
    - Navigation: cd, pwd, ls
    - File operations: cat, touch, mkdir, rm, cp, mv
    - Utilities: echo, clear, help, history, exit
    """
    
    def __init__(self):
        self._root: Optional[ctk.CTk] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Terminal state
        self._cwd = Path.home()  # Current working directory
        self._history = CommandHistory()
        self._env = os.environ.copy()
        
        # UI elements
        self._output_text: Optional[ctk.CTkTextbox] = None
        self._input_entry: Optional[ctk.CTkEntry] = None
        self._context_menu = None
        
        # Command registry
        self._commands: Dict[str, Callable] = {
            'cd': self._cmd_cd,
            'pwd': self._cmd_pwd,
            'ls': self._cmd_ls,
            'dir': self._cmd_ls,  # Windows alias
            'cat': self._cmd_cat,
            'type': self._cmd_cat,  # Windows alias
            'echo': self._cmd_echo,
            'touch': self._cmd_touch,
            'mkdir': self._cmd_mkdir,
            'rm': self._cmd_rm,
            'del': self._cmd_rm,  # Windows alias
            'rmdir': self._cmd_rmdir,
            'cp': self._cmd_cp,
            'copy': self._cmd_cp,  # Windows alias
            'mv': self._cmd_mv,
            'move': self._cmd_mv,  # Windows alias
            'clear': self._cmd_clear,
            'cls': self._cmd_clear,  # Windows alias
            'help': self._cmd_help,
            'history': self._cmd_history,
            'exit': self._cmd_exit,
            'quit': self._cmd_exit,
            'whoami': self._cmd_whoami,
            'date': self._cmd_date,
            'head': self._cmd_head,
            'tail': self._cmd_tail,
            'wc': self._cmd_wc,
            'grep': self._cmd_grep,
            'find': self._cmd_find,
            'status': self._cmd_status,
            'frank': self._cmd_frank,
            # Git commands
            'git': self._cmd_git,
            # SSH commands
            'ssh': self._cmd_ssh,
            'scp': self._cmd_scp,
            'ssh-keygen': self._cmd_ssh_keygen,
            # Package managers
            'pip': self._cmd_pip,
            'npm': self._cmd_npm,
            'conda': self._cmd_conda,
            # Text editors
            'nano': self._cmd_nano,
            'vim': self._cmd_vim,
            'vi': self._cmd_vim,
            'notepad': self._cmd_notepad,
            'code': self._cmd_code,
            # Environment variables
            'export': self._cmd_export,
            'env': self._cmd_env,
            'set': self._cmd_set,
            'unset': self._cmd_unset,
            'printenv': self._cmd_printenv,
            # Scripting
            'source': self._cmd_source,
            'python': self._cmd_python,
            'node': self._cmd_node,
            # Security
            'security': self._cmd_security,
            # Hardware
            'hardware': self._cmd_hardware,
            # Provider Registry (Phase 3 Step 2)
            'providers': self._cmd_providers,
            'connect': self._cmd_connect,
            'disconnect': self._cmd_disconnect,
            'credentials': self._cmd_credentials,
            # Permissions & Automation (Phase 3 Step 6)
            'permissions': self._cmd_permissions,
            'setup': self._cmd_setup,
            'automation': self._cmd_automation,
            'scheduler': self._cmd_scheduler,
            # System Diagnostics
            'diagnose': self._cmd_diagnose,
            # Quantum Mode
            'quantum': self._cmd_quantum,
            'q': self._cmd_quantum,  # Shortcut
            # Synthesis Engine
            'synthesis': self._cmd_synthesis,
            'synth': self._cmd_synthesis,  # Alias
            'bloch': self._cmd_bloch,      # Quick Bloch sphere
            'qubit': self._cmd_qubit,      # Quick qubit operations
            # Intelligent Router (Phase 3 Step 5)
            'route': self._cmd_route,
            'route-options': self._cmd_route_options,
            'route-test': self._cmd_route_test,
            'route-history': self._cmd_route_history,
        }
        
        # Security monitor integration
        self._security_monitor = None
        self._security_dashboard = None
        
        # Hardware monitor integration
        self._hardware_monitor = None
        
        # Quantum mode integration
        self._quantum_mode = None
        self._in_quantum_mode = False
    
    def start(self) -> bool:
        """Start the terminal in a separate thread"""
        if not CTK_AVAILABLE:
            print("❌ customtkinter not available")
            return False
        
        if self._running:
            return False
        
        self._running = True
        self._thread = threading.Thread(target=self._run_terminal, daemon=True)
        self._thread.start()
        return True
    
    def stop(self):
        """Stop the terminal"""
        self._running = False
        if self._root:
            try:
                self._root.quit()
            except Exception:
                pass

    def _run_terminal(self):
        """Main terminal loop - runs in separate thread"""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self._root = ctk.CTk()
        self._root.title("⚡ FRANKENSTEIN 1.0 ⚡")
        self._root.geometry("750x950+100+50")
        self._root.minsize(650, 600)
        self._root.attributes("-topmost", True)
        
        # Monster Lab color scheme - refined, professional
        self._colors = {
            'bg_dark': "#0a0a0f",           # Deep dark background
            'bg_medium': "#12121a",          # Medium dark panels
            'bg_light': "#1a1a2e",           # Lighter panels
            'electric_green': "#3ddc84",     # Primary accent (softer green)
            'electric_purple': "#7c3aed",    # Secondary accent (deeper purple)
            'electric_blue': "#64b5f6",      # Tertiary accent (softer blue)
            'warning_amber': "#ffb74d",      # Warning state (softer amber)
            'danger_red': "#ef5350",         # Danger state (softer red)
            'text_primary': "#d4d4d4",       # Main text
            'text_secondary': "#888899",     # Muted text
            'border_glow': "#2a3a35",        # Subtle green border
            'bolt_yellow': "#ffd54f",        # Lightning bolt (softer yellow)
        }
        
        # Configure root background
        self._root.configure(fg_color=self._colors['bg_dark'])
        
        # Allow resizing
        self._root.resizable(True, True)
        
        # Prevent accidental closing - confirm first
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Build the UI
        self._build_ui()
        
        # Show welcome message
        self._show_welcome()
        
        # Focus the input
        self._root.after(100, lambda: self._input_entry.focus_force())
        
        self._root.mainloop()
    
    def _build_ui(self):
        """Build the terminal UI - Monster Lab Theme"""
        # Configure grid
        self._root.grid_columnconfigure(0, weight=1)
        self._root.grid_rowconfigure(0, weight=0)  # Header
        self._root.grid_rowconfigure(1, weight=1)  # Output
        self._root.grid_rowconfigure(2, weight=0)  # Input
        
        # ==================== HEADER - THE LAB BANNER ====================
        header = ctk.CTkFrame(
            self._root, 
            height=50, 
            fg_color=self._colors['bg_light'],
            border_width=2,
            border_color=self._colors['border_glow'],
            corner_radius=8
        )
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        header.grid_columnconfigure(1, weight=1)
        
        # Lightning bolt left
        bolt_left = ctk.CTkLabel(
            header,
            text="⚡",
            font=("Segoe UI Emoji", 20),
            text_color=self._colors['bolt_yellow']
        )
        bolt_left.grid(row=0, column=0, padx=(12, 4), pady=8)
        
        # Main title with monster styling
        title = ctk.CTkLabel(
            header,
            text="FRANKENSTEIN 1.0",
            font=("Consolas", 18, "bold"),
            text_color=self._colors['electric_green']
        )
        title.grid(row=0, column=1, padx=5, pady=8, sticky="w")
        
        # Subtitle
        subtitle = ctk.CTkLabel(
            header,
            text="Monster Terminal",
            font=("Consolas", 10),
            text_color=self._colors['electric_purple']
        )
        subtitle.grid(row=0, column=2, padx=5, pady=8)
        
        # Status indicator with pulsing feel
        self._status_frame = ctk.CTkFrame(
            header,
            fg_color=self._colors['bg_medium'],
            corner_radius=12,
            border_width=1,
            border_color=self._colors['electric_green']
        )
        self._status_frame.grid(row=0, column=3, padx=(5, 12), pady=8)
        
        self._status_label = ctk.CTkLabel(
            self._status_frame,
            text="  ● ALIVE  ",
            font=("Consolas", 11, "bold"),
            text_color=self._colors['electric_green']
        )
        self._status_label.pack(padx=8, pady=4)
        
        # Lightning bolt right
        bolt_right = ctk.CTkLabel(
            header,
            text="⚡",
            font=("Segoe UI Emoji", 20),
            text_color=self._colors['bolt_yellow']
        )
        bolt_right.grid(row=0, column=4, padx=(4, 12), pady=8)
        
        # ==================== OUTPUT AREA - THE LAB CONSOLE ====================
        output_frame = ctk.CTkFrame(
            self._root,
            fg_color=self._colors['bg_medium'],
            border_width=2,
            border_color=self._colors['border_glow'],
            corner_radius=8
        )
        output_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        output_frame.grid_columnconfigure(0, weight=1)
        output_frame.grid_rowconfigure(0, weight=1)
        
        self._output_text = ctk.CTkTextbox(
            output_frame,
            font=("Consolas", 11),
            fg_color=self._colors['bg_dark'],
            text_color=self._colors['text_primary'],
            wrap="word",
            state="normal",
            corner_radius=6,
            border_width=0
        )
        self._output_text.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        
        # ==================== LIVE MONITOR PANEL - LAB INSTRUMENTS ====================
        self._monitor_frame = ctk.CTkFrame(
            self._root,
            width=300,
            height=180,
            fg_color=self._colors['bg_light'],
            border_width=2,
            border_color=self._colors['electric_purple'],
            corner_radius=10
        )
        self._monitor_frame.place(relx=1.0, rely=0.0, x=-16, y=65, anchor="ne")
        self._monitor_frame.grid_propagate(False)
        self._monitor_frame.pack_propagate(False)
        
        # Monitor title bar
        monitor_title = ctk.CTkLabel(
            self._monitor_frame,
            text="🔬 LAB MONITORS",
            font=("Consolas", 10, "bold"),
            text_color=self._colors['electric_blue']
        )
        monitor_title.place(x=8, y=4)
        
        # Divider under title
        ctk.CTkLabel(
            self._monitor_frame,
            text="━" * 30,
            font=("Consolas", 6),
            text_color=self._colors['electric_purple']
        ).place(x=4, y=22)
        
        # ===== SECURITY SECTION =====
        security_title = ctk.CTkLabel(
            self._monitor_frame,
            text="🛡️ SHIELD",
            font=("Consolas", 10, "bold"),
            text_color=self._colors['electric_blue'],
            anchor="w"
        )
        security_title.place(x=8, y=28)
        
        self._threat_label = ctk.CTkLabel(
            self._monitor_frame,
            text="● SECURE",
            font=("Consolas", 10, "bold"),
            text_color=self._colors['electric_green'],
            anchor="w"
        )
        self._threat_label.place(x=8, y=46)
        
        self._blocked_label = ctk.CTkLabel(
            self._monitor_frame,
            text="Blocked: 0   Active: 0",
            font=("Consolas", 9),
            text_color=self._colors['text_secondary'],
            anchor="w"
        )
        self._blocked_label.place(x=8, y=64)
        
        # Divider
        ctk.CTkLabel(
            self._monitor_frame,
            text="-" * 30,
            font=("Consolas", 6),
            text_color=self._colors['border_glow']
        ).place(x=4, y=84)
        
        # ===== HARDWARE SECTION =====
        self._health_label = ctk.CTkLabel(
            self._monitor_frame,
            text="● STABLE",
            font=("Consolas", 10, "bold"),
            text_color=self._colors['electric_green'],
            anchor="w"
        )
        self._health_label.place(x=8, y=92)
        
        # CPU with mini bar
        self._cpu_label = ctk.CTkLabel(
            self._monitor_frame,
            text="⚡ CPU: --%",
            font=("Consolas", 9),
            text_color=self._colors['text_secondary'],
            anchor="w"
        )
        self._cpu_label.place(x=8, y=112)
        
        # RAM with mini bar
        self._ram_label = ctk.CTkLabel(
            self._monitor_frame,
            text="🧠 RAM: --%",
            font=("Consolas", 9),
            text_color=self._colors['text_secondary'],
            anchor="w"
        )
        self._ram_label.place(x=115, y=112)
        
        # Diagnosis line
        self._diagnosis_label = ctk.CTkLabel(
            self._monitor_frame,
            text="",
            font=("Consolas", 8),
            text_color=self._colors['warning_amber'],
            anchor="w",
            wraplength=220,
            justify="left"
        )
        self._diagnosis_label.place(x=8, y=132)
        
        # Start live monitor update loop
        self._start_monitor_updates()
        
        # Make output area read-only but allow selection/copy
        self._output_text.bind("<Key>", lambda e: "break" if e.keysym not in ["c", "C"] or not (e.state & 0x4) else None)
        self._output_text.bind("<Button-1>", lambda e: self._output_text.focus_set())
        
        # Enable right-click text selection for output (standard behavior)
        self._output_text.bind("<Button-3>", self._on_output_right_click_start)
        self._output_text.bind("<B3-Motion>", self._on_output_right_click_drag)
        self._output_text.bind("<ButtonRelease-3>", self._on_output_right_click_release)
        
        # Right-click context menu for output
        self._setup_context_menu()
        
        # ==================== INPUT AREA - COMMAND INTERFACE ====================
        input_frame = ctk.CTkFrame(
            self._root, 
            height=130, 
            fg_color=self._colors['bg_light'],
            border_width=2,
            border_color=self._colors['border_glow'],
            corner_radius=8
        )
        input_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(4, 8))
        input_frame.grid_columnconfigure(0, weight=1)
        input_frame.grid_rowconfigure(1, weight=1)
        input_frame.grid_propagate(False)
        
        # Prompt label with monster styling
        self._prompt_label = ctk.CTkLabel(
            input_frame,
            text=self._get_prompt(),
            font=("Consolas", 11, "bold"),
            text_color=self._colors['electric_purple']
        )
        self._prompt_label.grid(row=0, column=0, padx=12, pady=(10, 2), sticky="w")
        
        # Multi-line command input textbox
        self._input_entry = ctk.CTkTextbox(
            input_frame,
            font=("Consolas", 11),
            fg_color=self._colors['bg_dark'],
            text_color=self._colors['electric_green'],
            border_color=self._colors['electric_green'],
            border_width=1,
            height=80,
            wrap="word",
            corner_radius=6
        )
        self._input_entry.grid(row=1, column=0, padx=10, pady=(2, 8), sticky="nsew")
        
        # Bind events for input - adjusted for CTkTextbox
        self._input_entry.bind("<Return>", self._on_enter)
        self._input_entry.bind("<Shift-Return>", self._on_shift_enter)  # New line
        self._input_entry.bind("<Up>", self._on_up_arrow)
        self._input_entry.bind("<Down>", self._on_down_arrow)
        self._input_entry.bind("<Tab>", self._on_tab_complete)
        self._input_entry.bind("<Escape>", lambda e: self._clear_input())
        
        # Enable standard text selection with BOTH mouse buttons
        # Left button: click and drag to select (default behavior)
        # Right button: click and drag to select, then show context menu on release
        self._input_entry.bind("<Button-3>", self._on_right_click_start)
        self._input_entry.bind("<B3-Motion>", self._on_right_click_drag)
        self._input_entry.bind("<ButtonRelease-3>", self._on_right_click_release)
        
        # Robust focus handling to prevent "disappearing" input issue
        self._input_entry.bind("<FocusOut>", self._refocus_input)
        
        # Re-focus input when clicking anywhere in the window
        self._root.bind("<Button-1>", self._on_window_click)
        
        # NOTE: Removed self._root.bind("<Key>", self._on_any_key)
        # This binding caused DOUBLE CHARACTER INPUT because:
        # 1. User types a key -> CTkTextbox's internal widget processes it (first char)
        # 2. Event bubbles to root -> _on_any_key fires
        # 3. Focus check fails (focus_get returns internal tk.Text, not CTkTextbox wrapper)
        # 4. Handler inserts the character again (second char)
        
        # Handle window activation
        self._root.bind("<FocusIn>", lambda e: self._input_entry.focus_set())

    def _setup_context_menu(self):
        """Setup right-click context menu for copy/paste"""
        # Context menu for output text
        self._context_menu = ctk.CTkFrame(self._root)
        
        # We'll use tkinter Menu for proper context menu behavior
        import tkinter as tk
        
        # Output context menu (copy only)
        self._output_menu = tk.Menu(self._root, tearoff=0, bg="#21262d", fg="#c9d1d9",
                                     activebackground="#30363d", activeforeground="#ffffff")
        self._output_menu.add_command(label="📋 Copy", command=self._copy_selection)
        self._output_menu.add_command(label="📑 Select All", command=self._select_all_output)
        self._output_menu.add_separator()
        self._output_menu.add_command(label="🗑️ Clear Terminal", command=self._cmd_clear)
        
        # Note: Button-3 binding for output is done in _build_ui with selection support
        
        # Input context menu (copy, cut, paste)
        self._input_menu = tk.Menu(self._root, tearoff=0, bg="#21262d", fg="#c9d1d9",
                                    activebackground="#30363d", activeforeground="#ffffff")
        self._input_menu.add_command(label="✂️ Cut", command=self._cut_input)
        self._input_menu.add_command(label="📋 Copy", command=self._copy_input)
        self._input_menu.add_command(label="📥 Paste", command=self._paste_input)
        self._input_menu.add_separator()
        self._input_menu.add_command(label="🗑️ Clear", command=self._clear_input)
    
    def _show_output_context_menu(self, event):
        """Show context menu for output text area"""
        try:
            self._output_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._output_menu.grab_release()
    
    def _show_input_context_menu(self, event):
        """Show context menu for input entry"""
        try:
            self._input_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._input_menu.grab_release()
    
    def _copy_selection(self):
        """Copy selected text from output"""
        try:
            # Get selected text from CTkTextbox
            selected = self._output_text.selection_get()
            self._root.clipboard_clear()
            self._root.clipboard_append(selected)
        except Exception:
            pass
    
    def _select_all_output(self):
        """Select all text in output"""
        self._output_text.tag_add("sel", "1.0", "end")
    
    def _cut_input(self):
        """Cut selected text from input"""
        try:
            selected = self._input_entry.get("sel.first", "sel.last")
            if selected:
                self._root.clipboard_clear()
                self._root.clipboard_append(selected)
                self._input_entry.delete("sel.first", "sel.last")
        except Exception:
            pass
    
    def _copy_input(self):
        """Copy selected text from input"""
        try:
            selected = self._input_entry.get("sel.first", "sel.last")
            if selected:
                self._root.clipboard_clear()
                self._root.clipboard_append(selected)
        except Exception:
            pass
    
    def _paste_input(self):
        """Paste text into input - preserves newlines for multi-line input"""
        try:
            text = self._root.clipboard_get()
            self._input_entry.insert("insert", text)
        except Exception:
            pass
    
    def _clear_input(self):
        """Clear all text from input textbox"""
        self._input_entry.delete("1.0", "end")
    
    def _refocus_input(self, event=None):
        """Re-focus input after losing focus (prevents disappearing issue)"""
        if self._running and self._input_entry:
            self._root.after(10, lambda: self._input_entry.focus_set())
    
    def _on_window_click(self, event=None):
        """Handle click anywhere in window - ensure input stays focused"""
        if self._running and self._input_entry:
            # Don't steal focus from output area if user is selecting text
            if event and event.widget == self._output_text._textbox:
                return
            self._input_entry.focus_set()
    
    # ==================== RIGHT-CLICK SELECTION SUPPORT ====================
    def _on_right_click_start(self, event):
        """Start text selection with right mouse button"""
        self._right_click_selecting = True
        # Set the starting position for selection
        self._input_entry.mark_set("insert", f"@{event.x},{event.y}")
        self._input_entry.mark_set("anchor", "insert")
        return "break"
    
    def _on_right_click_drag(self, event):
        """Continue text selection while right button is held"""
        if hasattr(self, '_right_click_selecting') and self._right_click_selecting:
            # Update selection as mouse moves
            current_pos = f"@{event.x},{event.y}"
            self._input_entry.tag_remove("sel", "1.0", "end")
            self._input_entry.tag_add("sel", "anchor", current_pos)
            self._input_entry.mark_set("insert", current_pos)
        return "break"
    
    def _on_right_click_release(self, event):
        """End selection and show context menu"""
        self._right_click_selecting = False
        # Show context menu after selection is complete
        self._show_input_context_menu(event)
        return "break"
    
    def _on_shift_enter(self, event=None):
        """Handle Shift+Enter - insert newline without executing"""
        self._input_entry.insert("insert", "\n")
        return "break"
    
    # ==================== OUTPUT RIGHT-CLICK SELECTION ====================
    def _on_output_right_click_start(self, event):
        """Start text selection in output with right mouse button"""
        self._output_right_click_selecting = True
        self._output_text.focus_set()
        # Set the starting position for selection
        self._output_text.mark_set("insert", f"@{event.x},{event.y}")
        self._output_text.mark_set("anchor", "insert")
        return "break"
    
    def _on_output_right_click_drag(self, event):
        """Continue text selection in output while right button is held"""
        if hasattr(self, '_output_right_click_selecting') and self._output_right_click_selecting:
            # Update selection as mouse moves
            current_pos = f"@{event.x},{event.y}"
            self._output_text.tag_remove("sel", "1.0", "end")
            self._output_text.tag_add("sel", "anchor", current_pos)
            self._output_text.mark_set("insert", current_pos)
        return "break"
    
    def _on_output_right_click_release(self, event):
        """End selection in output and show context menu"""
        self._output_right_click_selecting = False
        # Show context menu after selection is complete
        self._show_output_context_menu(event)
        return "break"
    # ==================== END OUTPUT RIGHT-CLICK SELECTION ====================
    
    def _on_any_key(self, event=None):
        """Handle any key press in window - redirect to input if needed"""
        if self._running and self._input_entry:
            # If focus is not on input, redirect there
            if event and self._root.focus_get() != self._input_entry:
                # Don't redirect if in output area (allow Ctrl+C for copy)
                if event.state & 0x4 and event.keysym in ['c', 'C']:  # Ctrl+C
                    return
                self._input_entry.focus_set()
                # Insert the character if it's a printable key
                if len(event.char) == 1 and event.char.isprintable():
                    self._input_entry.insert("end", event.char)
                    return "break"

    def _on_enter(self, event=None):
        """Handle Enter key - execute command (multi-line supported)"""
        # Get all text from the textbox
        command = self._input_entry.get("1.0", "end-1c").strip()
        self._input_entry.delete("1.0", "end")
        
        if command:
            self._history.add(command)
            self._execute_command(command)
        
        self._update_prompt()
        return "break"
    
    def _on_up_arrow(self, event=None):
        """Handle Up arrow - previous command (only if at first line)"""
        # Check if cursor is on the first line
        cursor_pos = self._input_entry.index("insert")
        if cursor_pos.startswith("1."):
            prev_cmd = self._history.get_previous()
            if prev_cmd is not None:
                self._input_entry.delete("1.0", "end")
                self._input_entry.insert("1.0", prev_cmd)
            return "break"
        # Allow normal up arrow navigation in multi-line text
        return None
    
    def _on_down_arrow(self, event=None):
        """Handle Down arrow - next command (only if at last line)"""
        # Check if cursor is on the last line
        cursor_line = int(self._input_entry.index("insert").split(".")[0])
        last_line = int(self._input_entry.index("end-1c").split(".")[0])
        if cursor_line >= last_line:
            next_cmd = self._history.get_next()
            if next_cmd is not None:
                self._input_entry.delete("1.0", "end")
                self._input_entry.insert("1.0", next_cmd)
            return "break"
        # Allow normal down arrow navigation in multi-line text
        return None
    
    def _on_tab_complete(self, event=None):
        """Handle Tab - basic path completion"""
        current = self._input_entry.get("1.0", "end-1c")
        parts = current.split()
        
        if not parts:
            return "break"
        
        # Complete the last word
        word = parts[-1]
        path = Path(self._cwd) / word
        parent = path.parent
        prefix = path.name
        
        try:
            if parent.exists():
                matches = [f.name for f in parent.iterdir() if f.name.lower().startswith(prefix.lower())]
                if len(matches) == 1:
                    # Single match - complete it
                    completion = matches[0]
                    if (parent / completion).is_dir():
                        completion += "/"
                    parts[-1] = str(parent / completion).replace(str(self._cwd) + os.sep, "")
                    self._input_entry.delete("1.0", "end")
                    self._input_entry.insert("1.0", " ".join(parts))
                elif len(matches) > 1:
                    # Multiple matches - show them
                    self._write_output("\n" + "  ".join(sorted(matches)) + "\n")
        except Exception:
            pass
        
        return "break"
    
    def _on_close(self):
        """Handle window close"""
        self._running = False
        self._root.destroy()
    
    def _get_prompt(self) -> str:
        """Generate Git Bash-style prompt"""
        try:
            user = os.environ.get('USERNAME', os.environ.get('USER', 'frank'))
            # Shorten path like Git Bash
            cwd_str = str(self._cwd)
            home = str(Path.home())
            if cwd_str.startswith(home):
                cwd_str = "~" + cwd_str[len(home):]
            # Use forward slashes like Git Bash
            cwd_str = cwd_str.replace("\\", "/")
            return f"{user}@frankenstein:{cwd_str}$"
        except Exception:
            return "frank$"
    
    def _update_prompt(self):
        """Update the prompt label"""
        self._prompt_label.configure(text=self._get_prompt())
    
    def _start_monitor_updates(self):
        """Start the live monitor update loop"""
        self._update_monitor_panel()
    
    def _update_monitor_panel(self):
        """Update the live security/resource monitor panel.

        LAZY LOADING: Uses lightweight psutil directly for CPU/RAM display.
        Does NOT import core/__init__.py or security/__init__.py at startup
        to avoid pulling in heavyweight modules (orchestrator, memory, etc.).
        Monitors are only started when the user explicitly runs a command.
        """
        if not self._running:
            return

        try:
            # Security stats — only show if monitor was already started by user
            try:
                if self._security_monitor and self._security_monitor._running:
                    from security.monitor import ThreatSeverity
                    stats = self._security_monitor.get_stats()
                    severity = ThreatSeverity[stats['current_severity']]
                    self._threat_label.configure(
                        text=f"{severity.icon} {severity.label}",
                        text_color=severity.color
                    )
                    self._blocked_label.configure(
                        text=f"Blocked: {stats['threats_blocked']}   Active: {stats['active_threats']}"
                    )
                else:
                    self._threat_label.configure(text="● SECURE", text_color=self._colors['electric_green'])
                    self._blocked_label.configure(text="Blocked: 0   Active: 0")
            except Exception:
                self._threat_label.configure(text="● SECURE", text_color=self._colors['electric_green'])
                self._blocked_label.configure(text="Blocked: 0   Active: 0")

            # CPU/RAM — use psutil directly (lightweight, no core/__init__ import chain)
            try:
                import psutil
                cpu = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory().percent
                max_cpu = 80
                max_mem = 70

                # If hardware monitor was started by user, use its richer data
                if self._hardware_monitor and self._hardware_monitor._running:
                    try:
                        from core.hardware_monitor import HealthStatus
                        hw_stats = self._hardware_monitor.get_stats()
                        health = self._hardware_monitor.get_health_status()
                        max_cpu = hw_stats.get('tier_max_cpu', 80)
                        max_mem = hw_stats.get('tier_max_memory', 70)
                        self._health_label.configure(
                            text=f"{health.icon} {health.label}",
                            text_color=health.color
                        )
                        diagnosis = hw_stats.get('diagnosis', {})
                        if health in (HealthStatus.WARNING, HealthStatus.CRITICAL, HealthStatus.OVERLOAD):
                            cause = diagnosis.get('primary_cause', '')
                            if cause:
                                if len(cause) > 35:
                                    cause = cause[:32] + "..."
                                self._diagnosis_label.configure(
                                    text=f"⚠ {cause}",
                                    text_color=health.color
                                )
                        else:
                            self._diagnosis_label.configure(text="")
                    except Exception:
                        self._health_label.configure(text="● STABLE", text_color=self._colors['electric_green'])
                        self._diagnosis_label.configure(text="")
                else:
                    self._health_label.configure(text="● STABLE", text_color=self._colors['electric_green'])
                    self._diagnosis_label.configure(text="")

                # Color code CPU
                if cpu > max_cpu:
                    cpu_color = "#ff4444"
                elif cpu > max_cpu * 0.85:
                    cpu_color = "#ff9900"
                elif cpu > max_cpu * 0.70:
                    cpu_color = "#ffcc00"
                else:
                    cpu_color = "#8b949e"

                # Color code RAM
                if mem > max_mem:
                    mem_color = "#ff4444"
                elif mem > max_mem * 0.85:
                    mem_color = "#ff9900"
                elif mem > max_mem * 0.70:
                    mem_color = "#ffcc00"
                else:
                    mem_color = "#8b949e"

                self._cpu_label.configure(text=f"⚡ CPU: {cpu:.0f}%", text_color=cpu_color)
                self._ram_label.configure(text=f"🧠 RAM: {mem:.0f}%", text_color=mem_color)

            except ImportError:
                self._cpu_label.configure(text="⚡ CPU: --%", text_color=self._colors['text_secondary'])
                self._ram_label.configure(text="🧠 RAM: --%", text_color=self._colors['text_secondary'])
                self._health_label.configure(text="● STABLE", text_color=self._colors['electric_green'])
                self._diagnosis_label.configure(text="")
        except Exception:
            pass

        # Schedule next update (every 3 seconds — lighter than 2s)
        if self._running and self._root:
            self._root.after(3000, self._update_monitor_panel)

    def _show_welcome(self):
        """Display welcome message - Monster Lab Theme"""
        welcome = f"""

        ███████╗██████╗  █████╗ ███╗   ██╗██╗  ██╗
        ██╔====╝██╔==██╗██╔==██╗████╗  ██║██║ ██╔╝
        █████╗  ██████╔╝███████║██╔██╗ ██║█████╔╝ 
        ██╔==╝  ██╔==██╗██╔==██║██║╚██╗██║██╔=██╗ 
        ██║     ██║  ██║██║  ██║██║ ╚████║██║  ██╗
        ╚=╝     ╚=╝  ╚=╝╚=╝  ╚=╝╚=╝  ╚===╝╚=╝  ╚=╝ ENSTEIN 1.0

                 🧟 "Frankenstein, here to serve science." 🧟

    +-----------------------------------------------------------------+
    |  🔬 COMMANDS     help · status · security · hardware · diagnose |
    |  🔌 PROVIDERS    Type 'providers' for quantum & classical compute|
    |  ⚛️  QUANTUM      Type 'q' or 'quantum' to enter quantum mode   |
    |  🧪 SYNTHESIS    Type 'synthesis' for physics simulations       |
    +-----------------------------------------------------------------+

    ⚡ Session: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    📂 Working: {self._cwd}

    ===================================================================
    IT'S ALIVE! Type 'help' to begin your experiment...
    ===================================================================

"""
        self._write_output(welcome, color="#00ff88")

    def _write_output(self, text: str, color: str = None):
        """Write text to output area"""
        if self._output_text:
            self._output_text.insert("end", text)
            self._output_text.see("end")
    
    def _write_error(self, text: str):
        """Write error message to output"""
        self._write_output(f"❌ Error: {text}\n")
    
    def _write_success(self, text: str):
        """Write success message to output"""
        self._write_output(f"✅ {text}\n")
    
    def _execute_command(self, command_line: str):
        """Parse and execute a command"""
        # Check if in quantum mode - route to quantum handler
        if self._in_quantum_mode and self._quantum_mode:
            # Show prompt with command
            self._write_output(f"{self._quantum_mode.get_prompt()} {command_line}\n")
            
            # Handle in quantum mode
            stay_in_mode = self._quantum_mode.handle_command(command_line)
            
            if not stay_in_mode:
                self._in_quantum_mode = False
                self._update_prompt()
            return
        
        # Show the command with prompt
        self._write_output(f"{self._get_prompt()} {command_line}\n")
        
        # Parse command and arguments
        parts = self._parse_command(command_line)
        if not parts:
            return
        
        cmd = parts[0].lower()
        args = parts[1:]
        
        # Commands that need raw command line (to preserve quotes)
        raw_commands = {'python', 'node', 'git', 'pip', 'npm', 'conda', 'ssh', 'scp'}
        
        # Check if it's a built-in command
        if cmd in self._commands:
            try:
                if cmd in raw_commands:
                    # Pass raw command line for these commands
                    self._commands[cmd](args, command_line)
                else:
                    self._commands[cmd](args)
            except TypeError:
                # Fallback if command doesn't accept raw_line
                self._commands[cmd](args)
            except Exception as e:
                self._write_error(str(e))
        else:
            # Try to execute as system command
            self._execute_system_command(command_line)
    
    def _parse_command(self, command_line: str) -> List[str]:
        """Parse command line into parts, respecting quotes"""
        parts = []
        current = ""
        in_quotes = False
        quote_char = None
        
        for char in command_line:
            if char in ('"', "'") and not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
            elif char == " " and not in_quotes:
                if current:
                    parts.append(current)
                    current = ""
            else:
                current += char
        
        if current:
            parts.append(current)
        
        return parts
    
    def _resolve_path(self, path_str: str) -> Path:
        """Resolve a path relative to current directory"""
        if not path_str:
            return self._cwd
        
        path_str = path_str.replace("/", os.sep).replace("\\", os.sep)
        
        # Handle ~ for home directory
        if path_str.startswith("~"):
            path_str = str(Path.home()) + path_str[1:]
        
        path = Path(path_str)
        if not path.is_absolute():
            path = self._cwd / path
        
        return path.resolve()
    
    def _execute_system_command(self, command: str):
        """Execute a system command via subprocess"""
        try:
            self._status_label.configure(text="  ⚡ WORKING  ", text_color=self._colors['warning_amber'])
            self._root.update()
            
            # Run command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(self._cwd),
                timeout=30
            )
            
            if result.stdout:
                self._write_output(result.stdout)
            if result.stderr:
                self._write_output(result.stderr)
            
            if result.returncode != 0 and not result.stdout and not result.stderr:
                self._write_error(f"Command '{command}' returned exit code {result.returncode}")
            
            self._status_label.configure(text="  ● ALIVE  ", text_color=self._colors['electric_green'])
            
        except subprocess.TimeoutExpired:
            self._write_error("Command timed out after 30 seconds")
            self._status_label.configure(text="  ● ALIVE  ", text_color=self._colors['electric_green'])
        except Exception as e:
            self._write_error(f"Failed to execute: {e}")
            self._status_label.configure(text="  ● ALIVE  ", text_color=self._colors['electric_green'])

    # ==================== BUILT-IN COMMANDS ====================
    
    def _cmd_cd(self, args: List[str]):
        """Change directory (cd)"""
        if not args:
            # cd with no args goes to home
            self._cwd = Path.home()
        elif args[0] == "-":
            # cd - (not implemented - would need previous dir tracking)
            self._write_output("cd -: Previous directory not tracked\n")
            return
        elif args[0] == "..":
            self._cwd = self._cwd.parent
        else:
            new_path = self._resolve_path(args[0])
            if new_path.exists() and new_path.is_dir():
                self._cwd = new_path
            else:
                self._write_error(f"cd: {args[0]}: No such directory")
                return
        
        self._write_output(f"{self._cwd}\n")
    
    def _cmd_pwd(self, args: List[str]):
        """Print working directory (pwd)"""
        self._write_output(f"{self._cwd}\n")
    
    def _cmd_ls(self, args: List[str]):
        """List directory contents (ls)"""
        show_all = "-a" in args or "-la" in args or "-al" in args
        show_long = "-l" in args or "-la" in args or "-al" in args
        
        # Filter out flags
        path_args = [a for a in args if not a.startswith("-")]
        target = self._resolve_path(path_args[0] if path_args else "")
        
        if not target.exists():
            self._write_error(f"ls: cannot access '{target}': No such file or directory")
            return
        
        if target.is_file():
            self._write_output(f"{target.name}\n")
            return
        
        try:
            items = list(target.iterdir())
            if not show_all:
                items = [i for i in items if not i.name.startswith(".")]
            
            items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
            
            if show_long:
                for item in items:
                    try:
                        stat = item.stat()
                        size = stat.st_size
                        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%b %d %H:%M")
                        prefix = "d" if item.is_dir() else "-"
                        perms = "rwxr-xr-x" if item.is_dir() else "rw-r--r--"
                        name = item.name + ("/" if item.is_dir() else "")
                        self._write_output(f"{prefix}{perms}  {size:>10}  {mtime}  {name}\n")
                    except Exception:
                        self._write_output(f"?????????  {'?':>10}  {'?':>12}  {item.name}\n")
            else:
                # Simple listing
                output = []
                for item in items:
                    name = item.name
                    if item.is_dir():
                        name += "/"
                    output.append(name)
                
                # Format in columns
                if output:
                    self._write_output("  ".join(output) + "\n")
                    
        except PermissionError:
            self._write_error(f"ls: cannot open directory '{target}': Permission denied")
    
    def _cmd_cat(self, args: List[str]):
        """Display file contents (cat)"""
        if not args:
            self._write_error("cat: missing file operand")
            return
        
        for filename in args:
            path = self._resolve_path(filename)
            if not path.exists():
                self._write_error(f"cat: {filename}: No such file")
                continue
            if path.is_dir():
                self._write_error(f"cat: {filename}: Is a directory")
                continue
            
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                    self._write_output(content)
                    if not content.endswith("\n"):
                        self._write_output("\n")
            except Exception as e:
                self._write_error(f"cat: {filename}: {e}")
    
    def _cmd_echo(self, args: List[str]):
        """Print arguments (echo)"""
        text = " ".join(args)
        # Handle basic variable expansion
        for key, value in os.environ.items():
            text = text.replace(f"${key}", value)
            text = text.replace(f"${{{key}}}", value)
        self._write_output(text + "\n")

    def _cmd_touch(self, args: List[str]):
        """Create empty file or update timestamp (touch)"""
        if not args:
            self._write_error("touch: missing file operand")
            return
        
        for filename in args:
            path = self._resolve_path(filename)
            try:
                path.touch()
                self._write_success(f"Created/updated: {filename}")
            except Exception as e:
                self._write_error(f"touch: {filename}: {e}")
    
    def _cmd_mkdir(self, args: List[str]):
        """Create directory (mkdir)"""
        if not args:
            self._write_error("mkdir: missing operand")
            return
        
        make_parents = "-p" in args
        dirs = [a for a in args if not a.startswith("-")]
        
        for dirname in dirs:
            path = self._resolve_path(dirname)
            try:
                if make_parents:
                    path.mkdir(parents=True, exist_ok=True)
                else:
                    path.mkdir()
                self._write_success(f"Created directory: {dirname}")
            except FileExistsError:
                self._write_error(f"mkdir: {dirname}: Directory exists")
            except Exception as e:
                self._write_error(f"mkdir: {dirname}: {e}")
    
    def _cmd_rm(self, args: List[str]):
        """Remove files (rm)"""
        if not args:
            self._write_error("rm: missing operand")
            return
        
        recursive = "-r" in args or "-rf" in args or "-fr" in args
        force = "-f" in args or "-rf" in args or "-fr" in args
        files = [a for a in args if not a.startswith("-")]
        
        for filename in files:
            path = self._resolve_path(filename)
            if not path.exists():
                if not force:
                    self._write_error(f"rm: {filename}: No such file or directory")
                continue
            
            try:
                if path.is_dir():
                    if recursive:
                        shutil.rmtree(path)
                        self._write_success(f"Removed directory: {filename}")
                    else:
                        self._write_error(f"rm: {filename}: Is a directory (use -r)")
                else:
                    path.unlink()
                    self._write_success(f"Removed: {filename}")
            except Exception as e:
                self._write_error(f"rm: {filename}: {e}")
    
    def _cmd_rmdir(self, args: List[str]):
        """Remove empty directory (rmdir)"""
        if not args:
            self._write_error("rmdir: missing operand")
            return
        
        for dirname in args:
            path = self._resolve_path(dirname)
            try:
                path.rmdir()
                self._write_success(f"Removed directory: {dirname}")
            except OSError as e:
                if "not empty" in str(e).lower():
                    self._write_error(f"rmdir: {dirname}: Directory not empty")
                else:
                    self._write_error(f"rmdir: {dirname}: {e}")
    
    def _cmd_cp(self, args: List[str]):
        """Copy files (cp)"""
        recursive = "-r" in args or "-R" in args
        files = [a for a in args if not a.startswith("-")]
        
        if len(files) < 2:
            self._write_error("cp: missing destination operand")
            return
        
        dest = self._resolve_path(files[-1])
        sources = files[:-1]
        
        for src_name in sources:
            src = self._resolve_path(src_name)
            if not src.exists():
                self._write_error(f"cp: {src_name}: No such file or directory")
                continue
            
            try:
                if src.is_dir():
                    if recursive:
                        target = dest / src.name if dest.is_dir() else dest
                        shutil.copytree(src, target)
                        self._write_success(f"Copied directory: {src_name}")
                    else:
                        self._write_error(f"cp: {src_name}: Is a directory (use -r)")
                else:
                    target = dest / src.name if dest.is_dir() else dest
                    shutil.copy2(src, target)
                    self._write_success(f"Copied: {src_name}")
            except Exception as e:
                self._write_error(f"cp: {src_name}: {e}")
    
    def _cmd_mv(self, args: List[str]):
        """Move/rename files (mv)"""
        files = [a for a in args if not a.startswith("-")]
        
        if len(files) < 2:
            self._write_error("mv: missing destination operand")
            return
        
        dest = self._resolve_path(files[-1])
        sources = files[:-1]
        
        for src_name in sources:
            src = self._resolve_path(src_name)
            if not src.exists():
                self._write_error(f"mv: {src_name}: No such file or directory")
                continue
            
            try:
                target = dest / src.name if dest.is_dir() else dest
                shutil.move(str(src), str(target))
                self._write_success(f"Moved: {src_name}")
            except Exception as e:
                self._write_error(f"mv: {src_name}: {e}")

    def _cmd_clear(self, args: List[str] = None):
        """Clear terminal (clear/cls)"""
        if self._output_text:
            self._output_text.delete("1.0", "end")
    
    def _cmd_history(self, args: List[str]):
        """Show command history"""
        for i, cmd in enumerate(self._history._history, 1):
            self._write_output(f"  {i:4d}  {cmd}\n")
    
    def _cmd_whoami(self, args: List[str]):
        """Print current user"""
        user = os.environ.get('USERNAME', os.environ.get('USER', 'unknown'))
        self._write_output(f"{user}\n")
    
    def _cmd_date(self, args: List[str]):
        """Print current date and time"""
        self._write_output(f"{datetime.now().strftime('%a %b %d %H:%M:%S %Y')}\n")
    
    def _cmd_head(self, args: List[str]):
        """Print first lines of file (head)"""
        n = 10
        files = []
        
        i = 0
        while i < len(args):
            if args[i] == "-n" and i + 1 < len(args):
                n = int(args[i + 1])
                i += 2
            elif args[i].startswith("-"):
                i += 1
            else:
                files.append(args[i])
                i += 1
        
        if not files:
            self._write_error("head: missing file operand")
            return
        
        for filename in files:
            path = self._resolve_path(filename)
            if not path.exists():
                self._write_error(f"head: {filename}: No such file")
                continue
            
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    for i, line in enumerate(f):
                        if i >= n:
                            break
                        self._write_output(line)
            except Exception as e:
                self._write_error(f"head: {filename}: {e}")
    
    def _cmd_tail(self, args: List[str]):
        """Print last lines of file (tail)"""
        n = 10
        files = []
        
        i = 0
        while i < len(args):
            if args[i] == "-n" and i + 1 < len(args):
                n = int(args[i + 1])
                i += 2
            elif args[i].startswith("-"):
                i += 1
            else:
                files.append(args[i])
                i += 1
        
        if not files:
            self._write_error("tail: missing file operand")
            return
        
        for filename in files:
            path = self._resolve_path(filename)
            if not path.exists():
                self._write_error(f"tail: {filename}: No such file")
                continue
            
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                    for line in lines[-n:]:
                        self._write_output(line)
            except Exception as e:
                self._write_error(f"tail: {filename}: {e}")
    
    def _cmd_wc(self, args: List[str]):
        """Count lines, words, chars (wc)"""
        files = [a for a in args if not a.startswith("-")]
        
        if not files:
            self._write_error("wc: missing file operand")
            return
        
        for filename in files:
            path = self._resolve_path(filename)
            if not path.exists():
                self._write_error(f"wc: {filename}: No such file")
                continue
            
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                    lines = content.count('\n')
                    words = len(content.split())
                    chars = len(content)
                    self._write_output(f"  {lines:7d}  {words:7d}  {chars:7d} {filename}\n")
            except Exception as e:
                self._write_error(f"wc: {filename}: {e}")
    
    def _cmd_grep(self, args: List[str]):
        """Search for pattern in files (grep)"""
        if len(args) < 2:
            self._write_error("grep: usage: grep PATTERN FILE...")
            return
        
        pattern = args[0]
        files = args[1:]
        ignore_case = "-i" in args
        if ignore_case:
            files = [f for f in files if f != "-i"]
        
        for filename in files:
            path = self._resolve_path(filename)
            if not path.exists():
                self._write_error(f"grep: {filename}: No such file")
                continue
            
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    for i, line in enumerate(f, 1):
                        check_line = line.lower() if ignore_case else line
                        check_pattern = pattern.lower() if ignore_case else pattern
                        if check_pattern in check_line:
                            self._write_output(f"{filename}:{i}:{line}")
            except Exception as e:
                self._write_error(f"grep: {filename}: {e}")

    def _cmd_find(self, args: List[str]):
        """Find files (simplified find)"""
        if not args:
            self._write_error("find: usage: find PATH [-name PATTERN]")
            return
        
        start_path = self._resolve_path(args[0])
        name_pattern = None
        
        if "-name" in args:
            idx = args.index("-name")
            if idx + 1 < len(args):
                name_pattern = args[idx + 1].lower()
        
        if not start_path.exists():
            self._write_error(f"find: {args[0]}: No such directory")
            return
        
        try:
            for path in start_path.rglob("*"):
                if name_pattern:
                    if name_pattern.replace("*", "") in path.name.lower():
                        self._write_output(f"{path}\n")
                else:
                    self._write_output(f"{path}\n")
        except Exception as e:
            self._write_error(f"find: {e}")
    
    def _cmd_status(self, args: List[str]):
        """Show Frankenstein system status"""
        try:
            from core.governor import get_governor
            from core.memory import get_memory
            governor = get_governor()
            memory = get_memory()

            status = governor.get_status()
            session = memory.get_session_stats()

            self._write_output("\n⚡ FRANKENSTEIN 1.0 STATUS\n")
            self._write_output("=" * 40 + "\n")
            self._write_output(f"CPU:        {status.get('cpu_percent', 'N/A')}%\n")
            self._write_output(f"Memory:     {status.get('memory_percent', 'N/A')}%\n")
            self._write_output(f"Safe:       {'✓' if status.get('safe', False) else '✗'}\n")
            self._write_output(f"Uptime:     {session.get('uptime_human', 'N/A')}\n")
            self._write_output("=" * 40 + "\n\n")
        except ImportError:
            self._write_output("Frankenstein core not initialized.\n")
            self._write_output("Run 'python frankenstein.py' to start full system.\n")
    
    def _cmd_frank(self, args: List[str]):
        """Frankenstein special commands"""
        if not args:
            self._write_output("Usage: frank <command>\n")
            self._write_output("Commands: status, version, quote\n")
            return
        
        subcmd = args[0].lower()
        if subcmd == "status":
            self._cmd_status([])
        elif subcmd == "version":
            self._write_output("⚡ FRANKENSTEIN 1.0\n")
            self._write_output("Target: Dell i3 8th Gen (Tier 1)\n")
        elif subcmd == "quote":
            quotes = [
                '"It\'s alive! IT\'S ALIVE!"',
                '"Knowledge is knowing that Frankenstein is not the monster. Wisdom is knowing that Frankenstein IS the monster."',
                '"Beware; for I am fearless, and therefore powerful."',
                '"Nothing is so painful to the human mind as a great and sudden change."',
                '"Life, although it may only be an accumulation of anguish, is dear to me."',
            ]
            import random
            self._write_output(f"\n🧟 {random.choice(quotes)}\n\n")
        else:
            self._write_error(f"frank: unknown command '{subcmd}'")

    # ==================== SECURITY COMMANDS ====================
    
    def _cmd_security(self, args: List[str]):
        """Security dashboard and threat monitoring commands"""
        try:
            from security.monitor import get_monitor
            from security.dashboard import get_dashboard, handle_security_command

            # Initialize monitor if needed (only on explicit user command)
            if self._security_monitor is None:
                self._security_monitor = get_monitor()
                if not self._security_monitor._running:
                    self._security_monitor.start()
                    self._security_monitor.add_severity_callback(self._on_security_severity_change)

            if self._security_dashboard is None:
                self._security_dashboard = get_dashboard()

            # Handle the command
            handle_security_command(args, self._write_output)

        except ImportError as e:
            self._write_error(f"Security module not available: {e}")
            self._write_output("Make sure security/ directory exists with all required files.\n")
    
    def _on_security_severity_change(self, severity):
        """Callback when security severity level changes"""
        try:
            if self._status_label and self._root:
                # Update status label color based on severity
                self._root.after(0, lambda: self._update_security_status(severity))
        except Exception:
            pass
    
    def _update_security_status(self, severity):
        """Update the terminal status label based on security state"""
        try:
            from security.monitor import ThreatSeverity
            if severity in (ThreatSeverity.CRITICAL, ThreatSeverity.HIGH):
                self._status_label.configure(text=f"  {severity.icon} THREAT  ", text_color=severity.color)
            elif severity == ThreatSeverity.MEDIUM:
                self._status_label.configure(text=f"  {severity.icon} ALERT  ", text_color=severity.color)
            elif severity == ThreatSeverity.LOW:
                self._status_label.configure(text=f"  {severity.icon} CAUTION  ", text_color=severity.color)
            else:
                self._status_label.configure(text="  ● ALIVE  ", text_color=self._colors['electric_green'])
        except Exception:
            pass

    # ==================== HARDWARE COMMANDS ====================
    
    def _cmd_hardware(self, args: List[str]):
        """Hardware health monitor and auto-switch commands"""
        try:
            from core.hardware_monitor import get_hardware_monitor
            from core.hardware_dashboard import handle_hardware_command

            # Initialize monitor if needed (only on explicit user command)
            if self._hardware_monitor is None:
                self._hardware_monitor = get_hardware_monitor()
                if not self._hardware_monitor._running:
                    self._hardware_monitor.start()

            # Handle the command
            handle_hardware_command(args, self._write_output)

        except ImportError as e:
            self._write_error(f"Hardware monitor not available: {e}")
            self._write_output("Make sure core/hardware_monitor.py exists.\n")

    # ==================== PROVIDER REGISTRY COMMANDS (Phase 3 Step 2) ====================

    def _cmd_providers(self, args: List[str]):
        """Provider registry — list, scan, and manage compute providers"""
        try:
            from integration.commands import handle_providers_command
            handle_providers_command(args, self._write_output)
        except ImportError as e:
            self._write_error(f"Provider registry not available: {e}")
            self._write_output("Make sure integration/providers/registry.py exists.\n")

    def _cmd_connect(self, args: List[str]):
        """Connect to a quantum or classical compute provider"""
        try:
            from integration.commands import handle_connect_command
            handle_connect_command(args, self._write_output)
        except ImportError as e:
            self._write_error(f"Provider registry not available: {e}")

    def _cmd_disconnect(self, args: List[str]):
        """Disconnect from a compute provider"""
        try:
            from integration.commands import handle_disconnect_command
            handle_disconnect_command(args, self._write_output)
        except ImportError as e:
            self._write_error(f"Provider registry not available: {e}")

    def _cmd_credentials(self, args: List[str]):
        """Manage saved provider credentials"""
        try:
            from integration.commands import handle_credentials_command
            handle_credentials_command(args, self._write_output)
        except ImportError as e:
            self._write_error(f"Credentials module not available: {e}")
            self._write_output("Make sure integration/credentials.py exists.\n")

    # ==================== INTELLIGENT ROUTER (Phase 3 Step 5) ====================

    def _cmd_route(self, args: List[str]):
        """Route a workload to the optimal compute provider"""
        try:
            from router.commands import handle_route_command
            handle_route_command(args, self._write_output)
        except ImportError as e:
            self._write_error(f"Router module not available: {e}")
            self._write_output("Make sure router/ directory exists.\n")

    def _cmd_route_options(self, args: List[str]):
        """Show all compatible providers for a workload"""
        try:
            from router.commands import handle_route_options_command
            handle_route_options_command(args, self._write_output)
        except ImportError as e:
            self._write_error(f"Router module not available: {e}")

    def _cmd_route_test(self, args: List[str]):
        """Test routing to a specific provider"""
        try:
            from router.commands import handle_route_test_command
            handle_route_test_command(args, self._write_output)
        except ImportError as e:
            self._write_error(f"Router module not available: {e}")

    def _cmd_route_history(self, args: List[str]):
        """Show past routing decisions"""
        try:
            from router.commands import handle_route_history_command
            handle_route_history_command(args, self._write_output)
        except ImportError as e:
            self._write_error(f"Router module not available: {e}")

    # ==================== PERMISSIONS & AUTOMATION ====================

    def _cmd_permissions(self, args: List[str]):
        """Permission management commands"""
        try:
            from permissions.commands import handle_permissions_command
            handle_permissions_command(args, self._write_output)
        except ImportError as e:
            self._write_error(f"Permissions module not available: {e}")
        except Exception as e:
            self._write_error(f"Error executing permissions command: {e}")

    def _cmd_setup(self, args: List[str]):
        """Run setup wizard for permissions and automation"""
        try:
            from permissions.commands import handle_setup_command
            handle_setup_command(args, self._write_output)
        except ImportError as e:
            self._write_error(f"Setup wizard not available: {e}")
        except Exception as e:
            self._write_error(f"Error executing setup command: {e}")

    def _cmd_automation(self, args: List[str]):
        """Automation workflow management commands"""
        try:
            from automation.commands import handle_automation_command
            handle_automation_command(args, self._write_output)
        except ImportError as e:
            self._write_error(f"Automation module not available: {e}")
        except Exception as e:
            self._write_error(f"Error executing automation command: {e}")

    def _cmd_scheduler(self, args: List[str]):
        """Task scheduler management commands"""
        try:
            from automation.commands import handle_scheduler_command
            handle_scheduler_command(args, self._write_output)
        except ImportError as e:
            self._write_error(f"Scheduler module not available: {e}")
        except Exception as e:
            self._write_error(f"Error executing scheduler command: {e}")

    # ==================== SYSTEM DIAGNOSTICS ====================
    
    def _cmd_diagnose(self, args: List[str]):
        """System diagnostics and optimization commands"""
        try:
            from core.system_diagnostics import handle_diagnose_command
            handle_diagnose_command(args, self._write_output)
        except ImportError as e:
            self._write_error(f"Diagnostics module not available: {e}")
            self._write_output("Make sure core/system_diagnostics.py exists.\n")

    # ==================== QUANTUM MODE ====================
    
    def _cmd_quantum(self, args: List[str]):
        """Enter quantum computing mode - hybrid REPL for quantum simulations"""
        try:
            from widget.quantum_mode import get_quantum_mode
            
            # Initialize quantum mode handler
            if self._quantum_mode is None:
                self._quantum_mode = get_quantum_mode()
                self._quantum_mode.set_output_callback(self._write_output)
            
            # Enter quantum mode
            if self._quantum_mode.enter_mode():
                self._in_quantum_mode = True
                # Note: Prompt will be updated via quantum_mode.get_prompt()
            else:
                self._write_error("Failed to enter quantum mode")
                
        except ImportError as e:
            self._write_error(f"Quantum mode not available: {e}")
            self._write_output("Make sure synthesis/ and widget/quantum_mode.py exist.\n")
            self._write_output("\nTo install dependencies:\n")
            self._write_output("  pip install numpy scipy\n\n")

    def _cmd_synthesis(self, args: List[str]):
        """Synthesis engine commands - REAL computational backend"""
        if not args:
            self._show_synthesis_help()
            return
        
        cmd = args[0].lower()
        cmd_args = args[1:] if len(args) > 1 else []
        
        # Direct computation commands
        if cmd == "compute" or cmd == "calc":
            self._synthesis_compute(cmd_args)
        elif cmd == "quantum":
            self._synthesis_quantum(cmd_args)
        elif cmd == "physics":
            self._synthesis_physics(cmd_args)
        elif cmd == "math":
            self._synthesis_math(cmd_args)
        elif cmd == "diff" or cmd == "differentiate":
            self._synthesis_differentiate(cmd_args)
        elif cmd == "integrate":
            self._synthesis_integrate(cmd_args)
        elif cmd == "solve":
            self._synthesis_solve(cmd_args)
        elif cmd == "lorentz":
            self._synthesis_lorentz(cmd_args)
        elif cmd == "schrodinger":
            self._synthesis_schrodinger(cmd_args)
        elif cmd == "status":
            self._synthesis_status()
        elif cmd == "help":
            self._show_synthesis_help()
        else:
            # Fall back to visualization commands
            try:
                from synthesis.terminal_commands import get_synthesis_commands
                synth_cmds = get_synthesis_commands()
                result = synth_cmds.execute(cmd, cmd_args)
                self._write_output(result.message + "\n")
            except ImportError as e:
                self._write_error(f"Command not found: {cmd}\n")
    
    def _show_synthesis_help(self):
        """Show synthesis engine help"""
        help_text = """
╔===================================================================╗
║            FRANKENSTEIN SYNTHESIS ENGINE - REAL COMPUTATIONS      ║
╠===================================================================╣
║  COMPUTATION COMMANDS (performs actual calculations):             ║
║                                                                   ║
║  synthesis compute <expr>     Evaluate expression                 ║
║    Example: synthesis compute sin(pi/4) + cos(pi/4)               ║
║                                                                   ║
║  synthesis diff <expr>        Differentiate symbolically          ║
║    Example: synthesis diff x**3 + sin(x)                          ║
║                                                                   ║
║  synthesis integrate <expr> [a b]  Integrate (definite or indef)  ║
║    Example: synthesis integrate x**2 0 1                          ║
║                                                                   ║
║  synthesis solve <equation>   Solve equation for x                ║
║    Example: synthesis solve x**2 - 4 = 0                          ║
║                                                                   ║
║  synthesis lorentz <velocity> Apply Lorentz transformation        ║
║    Example: synthesis lorentz 0.5                                 ║
║                                                                   ║
║  synthesis schrodinger        Solve Schrödinger equation          ║
║    Example: synthesis schrodinger                                 ║
║                                                                   ║
║  synthesis quantum <cmd>      Quantum mechanics operations        ║
║    Example: synthesis quantum bell                                ║
║                                                                   ║
║  synthesis physics <calc>     Physics calculations                ║
║    Example: synthesis physics gamma 0.8c                          ║
║                                                                   ║
║  synthesis status             Show engine status                  ║
╚===================================================================╝
"""
        self._write_output(help_text)
    
    def _synthesis_compute(self, args: List[str]):
        """Direct computation"""
        if not args:
            self._write_output("Usage: synthesis compute <expression>\n")
            return
        
        try:
            from synthesis.compute.engine import get_compute_engine
            engine = get_compute_engine()
            expression = " ".join(args)
            result = engine.compute(expression)
            
            if result.success:
                self._write_output(f"\n  Expression: {expression}\n")
                if result.numeric_value is not None:
                    self._write_output(f"  Result: {result.numeric_value}\n")
                if result.symbolic_value:
                    self._write_output(f"  Symbolic: {result.symbolic_value}\n")
                self._write_output(f"  Time: {result.computation_time*1000:.2f}ms\n\n")
            else:
                self._write_error(f"Computation failed: {result.error}\n")
        except Exception as e:
            self._write_error(f"Error: {e}\n")
    
    def _synthesis_differentiate(self, args: List[str]):
        """Symbolic differentiation"""
        if not args:
            self._write_output("Usage: synthesis diff <expression> [variable]\n")
            return
        
        try:
            from synthesis.compute.engine import get_compute_engine
            engine = get_compute_engine()
            expression = args[0]
            variable = args[1] if len(args) > 1 else "x"
            result = engine.differentiate(expression, variable)
            
            if result.success:
                self._write_output(f"\n  d/d{variable}({expression}) = {result.symbolic_value}\n\n")
            else:
                self._write_error(f"Differentiation failed: {result.error}\n")
        except Exception as e:
            self._write_error(f"Error: {e}\n")
    
    def _synthesis_integrate(self, args: List[str]):
        """Symbolic/numeric integration"""
        if not args:
            self._write_output("Usage: synthesis integrate <expression> [a b]\n")
            return
        
        try:
            from synthesis.compute.engine import get_compute_engine
            engine = get_compute_engine()
            expression = args[0]
            limits = None
            if len(args) >= 3:
                limits = (float(args[1]), float(args[2]))
            
            result = engine.integrate(expression, limits=limits)
            
            if result.success:
                if limits:
                    self._write_output(f"\n  Integral[{limits[0]},{limits[1]}]({expression}) = {result.symbolic_value}\n")
                    if result.numeric_value:
                        self._write_output(f"  Numeric value: {result.numeric_value}\n")
                else:
                    self._write_output(f"\n  Integral({expression}) = {result.symbolic_value} + C\n")
                self._write_output("\n")
            else:
                self._write_error(f"Integration failed: {result.error}\n")
        except Exception as e:
            self._write_error(f"Error: {e}\n")
    
    def _synthesis_solve(self, args: List[str]):
        """Solve equation"""
        if not args:
            self._write_output("Usage: synthesis solve <equation> [variable]\n")
            return
        
        try:
            from synthesis.compute.engine import get_compute_engine
            engine = get_compute_engine()
            equation = " ".join(args[:-1]) if len(args) > 1 and args[-1].isalpha() else " ".join(args)
            variable = args[-1] if len(args) > 1 and args[-1].isalpha() and len(args[-1]) == 1 else "x"
            
            result = engine.solve_equation(equation, variable)
            
            if result.success:
                self._write_output(f"\n  Solving: {equation}\n")
                self._write_output(f"  Solutions for {variable}: {result.data.get('solutions', [])}\n\n")
            else:
                self._write_error(f"Solve failed: {result.error}\n")
        except Exception as e:
            self._write_error(f"Error: {e}\n")
    
    def _synthesis_lorentz(self, args: List[str]):
        """Lorentz transformation"""
        if not args:
            self._write_output("Usage: synthesis lorentz <velocity>\n")
            self._write_output("  velocity as fraction of c (0 < v < 1)\n")
            return
        
        try:
            from synthesis.compute.physics_compute import get_physics_compute
            physics = get_physics_compute()
            
            v_str = args[0].replace('c', '')
            v_frac = float(v_str)
            v = v_frac * physics.constants["c"]
            
            gamma = physics.lorentz_factor(v)
            
            self._write_output(f"\n  Velocity: {v_frac}c\n")
            self._write_output(f"  Lorentz factor (gamma): {gamma:.6f}\n")
            self._write_output(f"  Time dilation: t' = {gamma:.4f} * t\n")
            self._write_output(f"  Length contraction: L' = L / {gamma:.4f}\n\n")
        except Exception as e:
            self._write_error(f"Error: {e}\n")
    
    def _synthesis_schrodinger(self, args: List[str]):
        """Solve Schrödinger equation using TRUE engine"""
        try:
            from synthesis.core import get_true_engine
            import numpy as np
            
            engine = get_true_engine()
            
            # Parse arguments
            n_qubits = int(args[0]) if args else 2
            t_max = float(args[1]) if len(args) > 1 else np.pi
            n_steps = int(args[2]) if len(args) > 2 else 100
            
            # Initialize state if needed
            if not engine.status()['initialized']:
                engine.initialize_qubits(n_qubits, 'zero')
                engine.hadamard(0)  # Start in superposition
            
            info = engine.get_state_info()
            dim = info['dimension']
            
            # Hamiltonian: Pauli-Z on first qubit (energy splitting)
            H = np.zeros((dim, dim), dtype=np.complex128)
            np.fill_diagonal(H, [1 if i % 2 == 0 else -1 for i in range(dim)])
            
            result = engine.solve_schrodinger(H, t_max, n_steps, store_trajectory=False)
            
            self._write_output("\n  ╔===========================================╗\n")
            self._write_output("  ║      SCHRÖDINGER EVOLUTION COMPLETE       ║\n")
            self._write_output("  ╠===========================================╣\n")
            self._write_output(f"  ║  Qubits: {info['n_qubits']:<33} ║\n")
            self._write_output(f"  ║  Dimension: {dim:<30} ║\n")
            self._write_output(f"  ║  Time: {t_max:.4f}{' '*29} ║\n")
            self._write_output(f"  ║  Steps: {n_steps:<32} ║\n")
            self._write_output(f"  ║  Computation: {result.computation_time*1000:.2f} ms{' '*21} ║\n")
            self._write_output(f"  ║  Final Energy: {result.expectation_values.get('energy', 0):.4f}{' '*20} ║\n")
            self._write_output("  ╚===========================================╝\n\n")
            
        except Exception as e:
            self._write_error(f"Error: {e}\n")
    
    def _synthesis_quantum(self, args: List[str]):
        """Quantum mechanics operations using TRUE Synthesis Engine"""
        if not args:
            self._write_output("Usage: synthesis quantum <command>\n")
            self._write_output("  init [n]    - Initialize n qubits (default: 2)\n")
            self._write_output("  bell        - Create Bell state\n")
            self._write_output("  ghz [n]     - Create GHZ state\n")
            self._write_output("  w [n]       - Create W state\n")
            self._write_output("  h <q>       - Apply Hadamard gate\n")
            self._write_output("  x/y/z <q>   - Apply Pauli gate\n")
            self._write_output("  cnot <c> <t>- Apply CNOT gate\n")
            self._write_output("  measure     - Measure current state\n")
            self._write_output("  evolve      - Time evolution\n")
            self._write_output("  info        - Show state info\n")
            return
        
        try:
            from synthesis.core import get_true_engine
            engine = get_true_engine()
            cmd = args[0].lower()
            
            if cmd == "init":
                n = int(args[1]) if len(args) > 1 else 2
                engine.initialize_qubits(n, 'zero')
                self._write_output(f"\n  Initialized {n} qubits in |{'0'*n}>\n\n")
            
            elif cmd == "bell":
                engine.create_bell_state()
                result = engine.measure(1024, collapse=False)
                self._write_output("\n  Bell State Created: (|00> + |11>)/√2\n")
                self._write_output(f"  Measurement (1024 shots): {result['counts']}\n\n")
            
            elif cmd == "ghz":
                n = int(args[1]) if len(args) > 1 else 3
                engine.create_ghz_state(n)
                result = engine.measure(1024, collapse=False)
                self._write_output(f"\n  GHZ State Created ({n} qubits)\n")
                self._write_output(f"  Measurement: {result['counts']}\n\n")
            
            elif cmd == "w":
                n = int(args[1]) if len(args) > 1 else 3
                engine.create_w_state(n)
                result = engine.measure(1024, collapse=False)
                self._write_output(f"\n  W State Created ({n} qubits)\n")
                self._write_output(f"  Measurement: {result['counts']}\n\n")
            
            elif cmd == "h":
                target = int(args[1]) if len(args) > 1 else 0
                engine.hadamard(target)
                self._write_output(f"\n  Applied Hadamard to qubit {target}\n\n")
            
            elif cmd in ["x", "y", "z"]:
                target = int(args[1]) if len(args) > 1 else 0
                if cmd == "x":
                    engine.pauli_x(target)
                elif cmd == "y":
                    engine.pauli_y(target)
                else:
                    engine.pauli_z(target)
                self._write_output(f"\n  Applied Pauli-{cmd.upper()} to qubit {target}\n\n")
            
            elif cmd == "cnot":
                ctrl = int(args[1]) if len(args) > 1 else 0
                tgt = int(args[2]) if len(args) > 2 else 1
                engine.cnot(ctrl, tgt)
                self._write_output(f"\n  Applied CNOT: control={ctrl}, target={tgt}\n\n")
            
            elif cmd == "measure":
                shots = int(args[1]) if len(args) > 1 else 1024
                result = engine.measure(shots, collapse=False)
                self._write_output(f"\n  Measurement ({shots} shots):\n")
                for state, count in list(result['counts'].items())[:8]:
                    pct = 100 * count / shots
                    bar = '█' * int(pct / 5)
                    self._write_output(f"    |{state}>: {count:5d} ({pct:5.1f}%) {bar}\n")
                self._write_output("\n")
            
            elif cmd == "evolve":
                import numpy as np
                t_max = float(args[1]) if len(args) > 1 else np.pi
                # Default Hamiltonian: Pauli-Z on first qubit
                info = engine.get_state_info()
                dim = info['dimension']
                H = np.zeros((dim, dim), dtype=np.complex128)
                np.fill_diagonal(H, [1 if i % 2 == 0 else -1 for i in range(dim)])
                result = engine.solve_schrodinger(H, t_max, n_steps=100)
                self._write_output(f"\n  Schrödinger evolution complete\n")
                self._write_output(f"  Time: {t_max:.4f}, Steps: 100\n")
                self._write_output(f"  Computation: {result.computation_time*1000:.2f} ms\n\n")
            
            elif cmd == "info":
                info = engine.get_state_info()
                if info['initialized']:
                    self._write_output(f"\n  Qubits: {info['n_qubits']}\n")
                    self._write_output(f"  Dimension: {info['dimension']}\n")
                    self._write_output(f"  Gates applied: {info['gates_applied']}\n")
                    self._write_output(f"  Non-zero states: {info['nonzero_states']}\n")
                    self._write_output("  Top states:\n")
                    for s in info['top_states'][:5]:
                        self._write_output(f"    |{s['state']}>: P={s['probability']:.4f}\n")
                    self._write_output("\n")
                else:
                    self._write_output("\n  No quantum state initialized\n\n")
            
            else:
                self._write_error(f"Unknown quantum command: {cmd}\n")
        except Exception as e:
            self._write_error(f"Error: {e}\n")
    
    def _synthesis_physics(self, args: List[str]):
        """Physics calculations"""
        if not args:
            self._write_output("Usage: synthesis physics <calculation>\n")
            self._write_output("  gamma <v>       - Lorentz factor\n")
            self._write_output("  energy <m> <v>  - Relativistic energy\n")
            self._write_output("  constant <name> - Physical constant\n")
            return
        
        try:
            from synthesis.compute.physics_compute import get_physics_compute
            physics = get_physics_compute()
            cmd = args[0].lower()
            
            if cmd == "gamma":
                v = float(args[1].replace('c', '')) * physics.constants["c"]
                gamma = physics.lorentz_factor(v)
                self._write_output(f"\n  Lorentz gamma = {gamma:.6f}\n\n")
            elif cmd == "constant":
                name = args[1] if len(args) > 1 else "c"
                val = physics.get_constant(name)
                self._write_output(f"\n  {name} = {val:.6e}\n\n")
            else:
                self._write_error(f"Unknown physics command: {cmd}\n")
        except Exception as e:
            self._write_error(f"Error: {e}\n")
    
    def _synthesis_math(self, args: List[str]):
        """Math operations"""
        self._synthesis_compute(args)
    
    def _synthesis_status(self):
        """Show TRUE synthesis engine status"""
        try:
            from synthesis.core import get_true_engine
            
            engine = get_true_engine()
            status = engine.status()
            hw = status['hardware']
            storage = status['storage']
            
            self._write_output("\n")
            self._write_output("  ╔==========================================================╗\n")
            self._write_output("  ║          TRUE SYNTHESIS ENGINE STATUS                    ║\n")
            self._write_output("  ╠==========================================================╣\n")
            self._write_output(f"  ║  Engine:     {status['engine']:40} ║\n")
            self._write_output(f"  ║  Max Qubits: {hw['max_qubits']:<40} ║\n")
            self._write_output(f"  ║  Max Memory: {hw['max_memory_GB']:.1f} GB{' '*33} ║\n")
            self._write_output(f"  ║  Storage:    {hw['max_storage_GB']:.1f} GB allocated{' '*24} ║\n")
            self._write_output(f"  ║  Used:       {storage['used_bytes']/1e6:.2f} MB ({storage['used_percent']:.1f}%){' '*22} ║\n")
            self._write_output(f"  ║  Files:      {storage['file_count']:<40} ║\n")
            self._write_output("  ╠==========================================================╣\n")
            
            if status['initialized']:
                info = engine.get_state_info()
                self._write_output(f"  ║  QUANTUM STATE:                                          ║\n")
                self._write_output(f"  ║    Qubits: {info['n_qubits']}, Dimension: {info['dimension']:<29} ║\n")
                self._write_output(f"  ║    Gates Applied: {info['gates_applied']:<35} ║\n")
            else:
                self._write_output(f"  ║  QUANTUM STATE: Not initialized                          ║\n")
            
            self._write_output("  ╚==========================================================╝\n\n")
        except Exception as e:
            self._write_error(f"Error: {e}\n")

    def _cmd_bloch(self, args: List[str]):
        """Launch 3D Bloch sphere visualization"""
        try:
            from synthesis.terminal_commands import get_synthesis_commands
            
            synth_cmds = get_synthesis_commands()
            
            # Default to 'rabi' simulation type if no args
            sim_type = args[0] if args else "rabi"
            cmd_args = [sim_type] + (args[1:] if len(args) > 1 else [])
            
            result = synth_cmds.execute("bloch", cmd_args)
            self._write_output(result.message + "\n")
            
        except ImportError as e:
            self._write_error(f"Bloch sphere not available: {e}")
            self._write_output("Make sure synthesis/ module exists.\n")

    def _cmd_qubit(self, args: List[str]):
        """Quick qubit operations (shortcut to quantum mode commands)"""
        try:
            from widget.quantum_mode import get_quantum_mode
            
            if self._quantum_mode is None:
                self._quantum_mode = get_quantum_mode()
                self._quantum_mode.set_output_callback(self._write_output)
            
            if not args:
                self._write_output("Usage: qubit <n> or qubit |state>\n")
                self._write_output("  qubit 2      - Initialize 2 qubits in |00>\n")
                self._write_output("  qubit |+>    - Initialize in |+> state\n")
                self._write_output("\nTip: Use 'quantum' or 'q' for full quantum mode.\n")
                return
            
            # Execute via quantum mode
            result = self._quantum_mode.execute_command("qubit " + " ".join(args))
            
        except ImportError as e:
            self._write_error(f"Quantum mode not available: {e}")

    # ==================== GIT COMMANDS ====================
    
    def _cmd_git(self, args: List[str], raw_line: str = None):
        """Enhanced Git - full Bash replacement with progress, colors, auth."""
        if not args:
            self._write_output("╔===========================================================╗\n")
            self._write_output("║  FRANKENSTEIN GIT - Full Replacement                      ║\n")
            self._write_output("╠===========================================================╣\n")
            self._write_output("║  clone <url> [dir]       Clone with progress              ║\n")
            self._write_output("║  status                  Color-coded file states           ║\n")
            self._write_output("║  log [--graph]           Commit visualization             ║\n")
            self._write_output("║  branch [-a]             Branch management                ║\n")
            self._write_output("║  remote [-v]             Remote management                ║\n")
            self._write_output("║  pull/push/fetch         With progress tracking            ║\n")
            self._write_output("╚===========================================================╝\n")
            return

        cmd = args[0].lower()
        handlers = {
            'clone': lambda: self._git_clone(args[1:]),
            'status': lambda: self._git_status(args[1:]),
            'log': lambda: self._git_log(args[1:]),
            'branch': lambda: self._git_branch(args[1:]),
            'remote': lambda: self._git_remote(args[1:]),
            'pull': lambda: self._git_progress('pull', args[1:]),
            'fetch': lambda: self._git_progress('fetch', args[1:]),
            'push': lambda: self._git_progress('push', args[1:]),
        }

        if cmd in handlers:
            handlers[cmd]()
        else:
            self._execute_system_command("git " + " ".join(args))

    def _git_clone(self, args: List[str]):
        """Clone with real-time progress bar."""
        if not args:
            self._write_error("Usage: git clone <url> [directory]\n")
            return

        url = args[0]
        cmd = ['git', 'clone', '--progress'] + args
        self._write_output(f"⚡ Cloning {url}...\n")

        process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1, cwd=str(self._cwd))
        pattern = r'(\w+\s+\w+):\s+(\d+)%\s+\((\d+)/(\d+)\)'
        last_t = time.time()

        for line in process.stderr:
            m = re.search(pattern, line)
            if m and time.time() - last_t > 0.2:
                stage = m.group(1)
                pct = int(m.group(2))
                bar = '█' * (pct//5) + '░' * (20 - pct//5)
                self._write_output(f"\r  {stage}: [{bar}] {pct}%", flush=True)
                last_t = time.time()
            elif 'done' in line.lower():
                self._write_output(line)

        if process.wait() == 0:
            self._write_success("\n✅ Clone complete!\n")
        else:
            self._write_error("\n❌ Clone failed\n")

    def _git_status(self, args: List[str]):
        """Status with colors and icons."""
        result = subprocess.run(['git', 'status', '--porcelain', '-b'], capture_output=True, text=True, cwd=str(self._cwd))
        if result.returncode != 0:
            self._write_error("❌ Not a git repository\n")
            return

        lines = result.stdout.strip().split('\n')
        if lines and lines[0].startswith('##'):
            self._write_output(f"📍 {lines[0][3:]}\n\n")

        staged = []
        modified = []
        untracked = []

        for line in lines[1:]:
            if not line.strip():
                continue
            status = line[:2]
            file = line[3:]

            if status[0] in 'MARC':
                staged.append((status[0], file))
            elif status[1] == 'M':
                modified.append(file)
            elif status == '??':
                untracked.append(file)

        if staged:
            self._write_success("Changes staged:\n")
            for s, f in staged:
                if s == 'M':
                    icon = '✅'
                elif s == 'A':
                    icon = '➕'
                else:
                    icon = '❌'
                self._write_output(f"  {icon} {f}\n")

        if modified:
            self._write_warning("\nChanges not staged:\n")
            for f in modified:
                self._write_output(f"  📝 {f}\n")

        if untracked:
            self._write_output("\nUntracked:\n")
            for f in untracked:
                self._write_output(f"  ❓ {f}\n")

        if not (staged or modified or untracked):
            self._write_success("✨ Working tree clean\n")

    def _git_log(self, args: List[str]):
        """Enhanced log with graph."""
        cmd = ['git', 'log', '--oneline', '--graph', '--decorate', '--all', '-20']
        if args:
            cmd.extend(args)

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self._cwd))
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'HEAD' in line:
                    self._write_success(line + '\n')
                elif '*' in line:
                    self._write_output(line.replace('*', '●') + '\n')
                else:
                    self._write_output(line + '\n')
        else:
            self._write_error(result.stderr)

    def _git_branch(self, args: List[str]):
        """Branch management with highlighting."""
        if not args or args[0] == '-a':
            result = subprocess.run(['git', 'branch', '-a', '-v'], capture_output=True, text=True, cwd=str(self._cwd))
            for line in result.stdout.split('\n'):
                if line.startswith('*'):
                    self._write_success(f"  {line} ← Current\n")
                elif 'remotes/' in line:
                    self._write_output(f"  {line.replace('remotes/', '🌐 ')}\n")
                elif line.strip():
                    self._write_output(f"  {line}\n")
        else:
            self._execute_system_command("git branch " + " ".join(args))

    def _git_remote(self, args: List[str]):
        """Remote management."""
        if not args or args[0] == '-v':
            result = subprocess.run(['git', 'remote', '-v'], capture_output=True, text=True, cwd=str(self._cwd))
            if result.stdout.strip():
                self._write_output("📡 Remotes:\n")
                for line in result.stdout.split('\n'):
                    if line.strip():
                        self._write_output(f"  {line}\n")
            else:
                self._write_warning("No remotes configured\n")
        else:
            self._execute_system_command("git remote " + " ".join(args))

    def _git_progress(self, operation: str, args: List[str]):
        """Generic progress for pull/push/fetch."""
        cmd = ['git', operation, '--progress'] + args
        self._write_output(f"⚡ Running git {operation}...\n")

        process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1, cwd=str(self._cwd))
        pattern = r'(\d+)%'
        last_t = time.time()

        for line in process.stderr:
            if time.time() - last_t > 0.2:
                m = re.search(pattern, line)
                if m:
                    pct = int(m.group(1))
                    bar = '█' * (pct//5) + '░' * (20 - pct//5)
                    self._write_output(f"\r  [{bar}] {pct}%", flush=True)
                    last_t = time.time()

        if process.wait() == 0:
            self._write_success(f"\n✅ {operation.capitalize()} complete!\n")
        else:
            self._write_error(f"\n❌ {operation.capitalize()} failed\n")

    # ==================== SSH COMMANDS ====================
    
    def _cmd_ssh(self, args: List[str], raw_line: str = None):
        """SSH remote connection"""
        if not args:
            self._write_output("Usage: ssh [user@]hostname [command]\n")
            self._write_output("Example: ssh user@example.com\n")
            return
        if raw_line:
            self._execute_system_command(raw_line)
        else:
            self._execute_system_command("ssh " + " ".join(args))
    
    def _cmd_scp(self, args: List[str], raw_line: str = None):
        """Secure copy over SSH"""
        if len(args) < 2:
            self._write_output("Usage: scp [options] source dest\n")
            self._write_output("Example: scp file.txt user@host:/path/\n")
            return
        if raw_line:
            self._execute_system_command(raw_line)
        else:
            self._execute_system_command("scp " + " ".join(args))
    
    def _cmd_ssh_keygen(self, args: List[str]):
        """Generate SSH keys"""
        self._write_output("Generating SSH key pair...\n")
        self._execute_system_command("ssh-keygen " + " ".join(args))
    
    # ==================== PACKAGE MANAGERS ====================
    
    def _cmd_pip(self, args: List[str], raw_line: str = None):
        """Python package manager"""
        if not args:
            self._write_output("Usage: pip <command> [options]\n")
            self._write_output("Commands: install, uninstall, list, show, freeze, search\n")
            return
        if raw_line:
            self._execute_system_command(raw_line)
        else:
            self._execute_system_command("pip " + " ".join(args))
    
    def _cmd_npm(self, args: List[str], raw_line: str = None):
        """Node.js package manager"""
        if not args:
            self._write_output("Usage: npm <command> [options]\n")
            self._write_output("Commands: install, uninstall, list, init, run, test\n")
            return
        if raw_line:
            self._execute_system_command(raw_line)
        else:
            self._execute_system_command("npm " + " ".join(args))
    
    def _cmd_conda(self, args: List[str], raw_line: str = None):
        """Conda package manager"""
        if not args:
            self._write_output("Usage: conda <command> [options]\n")
            self._write_output("Commands: install, create, activate, deactivate, list, env list\n")
            return
        if raw_line:
            self._execute_system_command(raw_line)
        else:
            self._execute_system_command("conda " + " ".join(args))
    
    # ==================== TEXT EDITORS ====================
    
    def _cmd_nano(self, args: List[str]):
        """Launch nano text editor"""
        if not args:
            self._write_output("Usage: nano <filename>\n")
            return
        # On Windows, try to use Git Bash's nano or fall back to notepad
        self._write_output(f"Opening {args[0]} in editor...\n")
        try:
            subprocess.Popen(["nano"] + args, cwd=str(self._cwd), 
                           creationflags=subprocess.CREATE_NEW_CONSOLE)
        except FileNotFoundError:
            self._write_output("nano not found, trying notepad...\n")
            self._cmd_notepad(args)
    
    def _cmd_vim(self, args: List[str]):
        """Launch vim text editor"""
        if not args:
            self._write_output("Usage: vim <filename>\n")
            return
        self._write_output(f"Opening {args[0]} in vim...\n")
        try:
            subprocess.Popen(["vim"] + args, cwd=str(self._cwd),
                           creationflags=subprocess.CREATE_NEW_CONSOLE)
        except FileNotFoundError:
            self._write_output("vim not found, trying notepad...\n")
            self._cmd_notepad(args)
    
    def _cmd_notepad(self, args: List[str]):
        """Launch Windows notepad"""
        if not args:
            subprocess.Popen(["notepad.exe"], cwd=str(self._cwd))
            self._write_output("Opened notepad\n")
            return
        filepath = self._resolve_path(args[0])
        subprocess.Popen(["notepad.exe", str(filepath)], cwd=str(self._cwd))
        self._write_output(f"Opened {args[0]} in notepad\n")
    
    def _cmd_code(self, args: List[str]):
        """Launch VS Code"""
        if not args:
            subprocess.Popen(["code", "."], cwd=str(self._cwd), shell=True)
            self._write_output("Opened VS Code in current directory\n")
            return
        filepath = self._resolve_path(args[0])
        subprocess.Popen(["code", str(filepath)], cwd=str(self._cwd), shell=True)
        self._write_output(f"Opened {args[0]} in VS Code\n")
    
    # ==================== ENVIRONMENT VARIABLES ====================
    
    def _cmd_export(self, args: List[str]):
        """Set environment variable (export VAR=value)"""
        if not args:
            self._write_output("Usage: export VAR=value\n")
            return
        
        # Join all args back together to handle cases like "VAR = value"
        full_arg = " ".join(args)
        
        # Handle multiple assignments separated by spaces (but not within values)
        # Simple case: look for VAR=value pattern
        if "=" in full_arg:
            # Handle potential spaces around = sign
            full_arg = full_arg.replace(" = ", "=").replace(" =", "=").replace("= ", "=")
            
            # Split on first = only
            parts = full_arg.split("=", 1)
            if len(parts) == 2:
                var = parts[0].strip()
                value = parts[1].strip().strip('"').strip("'")  # Remove quotes if present
                
                if var:
                    self._env[var] = value
                    os.environ[var] = value
                    self._write_success(f"Set {var}={value}")
                    return
        
        self._write_error(f"export: invalid format. Use: export VAR=value")
    
    def _cmd_env(self, args: List[str]):
        """Show all environment variables"""
        if args:
            # Run command with modified environment
            self._execute_system_command(" ".join(args))
            return
        output = []
        for key, value in sorted(os.environ.items()):
            output.append(f"{key}={value}")
        self._write_output("\n".join(output[:50]) + "\n")
        if len(os.environ) > 50:
            self._write_output(f"... and {len(os.environ) - 50} more variables\n")
    
    def _cmd_set(self, args: List[str]):
        """Set or show environment variables (Windows style)"""
        if not args:
            self._cmd_env([])
            return
        for arg in args:
            if "=" in arg:
                var, value = arg.split("=", 1)
                self._env[var] = value
                os.environ[var] = value
                self._write_success(f"Set {var}={value}")
            else:
                # Show specific variable
                value = os.environ.get(arg, "")
                if value:
                    self._write_output(f"{arg}={value}\n")
                else:
                    self._write_error(f"Environment variable {arg} not defined")
    
    def _cmd_unset(self, args: List[str]):
        """Unset environment variable"""
        if not args:
            self._write_output("Usage: unset VAR [VAR...]\n")
            return
        for var in args:
            if var in os.environ:
                del os.environ[var]
                if var in self._env:
                    del self._env[var]
                self._write_success(f"Unset {var}")
            else:
                self._write_error(f"unset: {var}: not set")
    
    def _cmd_printenv(self, args: List[str]):
        """Print environment variable value"""
        if not args:
            self._cmd_env([])
            return
        for var in args:
            value = os.environ.get(var, "")
            if value:
                self._write_output(f"{value}\n")
            else:
                self._write_error(f"printenv: {var}: not set")
    
    # ==================== SCRIPTING ====================
    
    def _cmd_source(self, args: List[str]):
        """Execute script file (source/run)"""
        if not args:
            self._write_output("Usage: source <script_file>\n")
            self._write_output("Supported: .sh, .bat, .cmd, .ps1, .py\n")
            return
        
        filepath = self._resolve_path(args[0])
        if not filepath.exists():
            self._write_error(f"source: {args[0]}: No such file")
            return
        
        ext = filepath.suffix.lower()
        if ext in ('.sh', '.bash'):
            self._execute_system_command(f'bash "{filepath}"')
        elif ext in ('.bat', '.cmd'):
            self._execute_system_command(f'cmd /c "{filepath}"')
        elif ext == '.ps1':
            self._execute_system_command(f'powershell -ExecutionPolicy Bypass -File "{filepath}"')
        elif ext == '.py':
            self._execute_system_command(f'python "{filepath}"')
        else:
            self._write_error(f"source: unsupported file type '{ext}'")
    
    def _cmd_python(self, args: List[str], raw_line: str = None):
        """Run Python interpreter or script"""
        if not args:
            self._write_output("Usage: python [script.py] [args]\n")
            self._write_output("Or: python -c 'code' to run inline code\n")
            return
        # Use raw command line to preserve quotes
        if raw_line:
            self._execute_system_command(raw_line)
        else:
            self._execute_system_command("python " + " ".join(args))
    
    def _cmd_node(self, args: List[str], raw_line: str = None):
        """Run Node.js interpreter or script"""
        if not args:
            self._write_output("Usage: node [script.js] [args]\n")
            self._write_output("Or: node -e 'code' to run inline code\n")
            return
        # Use raw command line to preserve quotes
        if raw_line:
            self._execute_system_command(raw_line)
        else:
            self._execute_system_command("node " + " ".join(args))

    def _cmd_exit(self, args: List[str]):
        """Exit terminal"""
        self._write_output("Goodbye! Frankenstein signing off...\n")
        self._root.after(500, self._on_close)
    
    def _cmd_help(self, args: List[str]):
        """Show help for commands"""
        if args:
            cmd = args[0].lower()
            help_text = {
                'cd': 'cd [DIR] - Change directory. Use ~ for home, .. for parent',
                'pwd': 'pwd - Print current working directory',
                'ls': 'ls [-la] [PATH] - List directory contents. -l for long, -a for all',
                'cat': 'cat FILE... - Display file contents',
                'echo': 'echo TEXT - Print text. Supports $VAR expansion',
                'touch': 'touch FILE... - Create empty file or update timestamp',
                'mkdir': 'mkdir [-p] DIR... - Create directories. -p for parents',
                'rm': 'rm [-rf] FILE... - Remove files. -r recursive, -f force',
                'cp': 'cp [-r] SRC... DEST - Copy files. -r for directories',
                'mv': 'mv SRC... DEST - Move/rename files',
                'clear': 'clear - Clear terminal screen',
                'history': 'history - Show command history',
                'head': 'head [-n N] FILE - Show first N lines (default 10)',
                'tail': 'tail [-n N] FILE - Show last N lines (default 10)',
                'wc': 'wc FILE... - Count lines, words, characters',
                'grep': 'grep [-i] PATTERN FILE... - Search for pattern',
                'find': 'find PATH [-name PATTERN] - Find files',
                'status': 'status - Show Frankenstein system status',
                'frank': 'frank <cmd> - Frankenstein commands (status, version, quote)',
                # Git
                'git': '''git <cmd> - ENHANCED Git Bash replacement with progress bars & colors

ENHANCED COMMANDS (with visual progress & icons):
  git clone <url> [dir]  Clone repo with real-time progress bar
  git status             Color-coded file states with icons
                         ✅ staged  📝 modified  ❓ untracked
  git log [--graph]      Visual commit graph with colors
  git branch [-a]        Branch list with current highlighted
  git remote [-v]        Show remotes with visual indicators
  git pull/push/fetch    Progress bars for network operations

STANDARD COMMANDS (passed through):
  git add <file>         Stage files for commit
  git commit -m "msg"    Commit with message
  git checkout <branch>  Switch branches
  git diff               Show changes
  git init               Initialize repository

Type 'git' with no args to see the enhanced features menu.
''',
                # SSH
                'ssh': 'ssh [user@]host - Connect to remote host via SSH',
                'scp': 'scp src dest - Secure copy files over SSH',
                'ssh-keygen': 'ssh-keygen - Generate SSH key pair',
                # Package managers
                'pip': 'pip <cmd> - Python package manager (install, uninstall, list, freeze)',
                'npm': 'npm <cmd> - Node.js package manager (install, uninstall, list, init)',
                'conda': 'conda <cmd> - Conda package manager (install, create, list, env)',
                # Text editors
                'nano': 'nano FILE - Open file in nano editor',
                'vim': 'vim FILE - Open file in vim editor',
                'vi': 'vi FILE - Open file in vim editor',
                'notepad': 'notepad [FILE] - Open Windows notepad',
                'code': 'code [FILE/DIR] - Open in VS Code',
                # Environment
                'export': 'export VAR=value - Set environment variable',
                'env': 'env - Show all environment variables',
                'set': 'set [VAR=value] - Set or show environment variables',
                'unset': 'unset VAR - Remove environment variable',
                'printenv': 'printenv [VAR] - Print environment variable value',
                # Scripting
                'source': 'source FILE - Execute script file (.sh, .bat, .py)',
                'python': 'python [script.py] - Run Python interpreter or script',
                'node': 'node [script.js] - Run Node.js interpreter or script',
                # Security
                'security': 'security [status|log|report|test] - Security dashboard and threat monitor',
                # Hardware
                'hardware': 'hardware [status|trend|tiers|recommend] - Hardware health monitor',
                # Provider Registry (Phase 3 Step 4 - ALL 30 PROVIDERS)
                'providers': '''providers - Manage quantum and classical compute providers

PHASE 3 STEP 4 COMPLETE: 30 provider adapters available!

SUBCOMMANDS:
  providers              Show all providers with SDK status
  providers scan         Refresh SDK availability scan
  providers info <id>    Detailed info for a specific provider
  providers install <id> Show pip install command for SDK
  providers quantum      List quantum providers only (19 total)
  providers classical    List classical providers only (10 total)

===============================================================
QUANTUM PROVIDERS (19 Total)
===============================================================

CLOUD PLATFORMS (6):
  local_simulator        Built-in NumPy simulator — 20 qubits, offline, FREE ✅
  ibm_quantum            IBM Quantum — 127 qubits, free tier (10 min/mo)
  aws_braket             AWS Braket — multi-provider (IonQ, Rigetti, D-Wave)
  azure_quantum          Azure Quantum — IonQ + Quantinuum, free credits
  google_cirq            Google Quantum AI — 72 qubits, research access
  nvidia_quantum_cloud   NVIDIA Quantum Cloud — cuQuantum GPU acceleration

HARDWARE VENDORS (11):
  ionq                   IonQ — 36 qubits, trapped-ion, free tier
  rigetti                Rigetti — 84 qubits, superconducting
  quantinuum             Quantinuum — 56 qubits, trapped-ion (via Azure)
  xanadu                 Xanadu — 24 qubits, photonic (PennyLane)
  dwave                  D-Wave — 5000 qubits, quantum annealing
  iqm                    IQM — 20 qubits, superconducting (Europe)
  quera                  QuEra — 256 qubits, neutral atom
  oxford                 Oxford QC — 32 qubits, superconducting (UK)
  atom_computing         Atom Computing — 1225 qubits, neutral atom
  pasqal                 Pasqal — 200 qubits, neutral atom (France)
  aqt                    AQT Alpine — 24 qubits, trapped-ion (Austria)

ADVANCED SIMULATORS (2):
  qiskit_aer             Qiskit Aer — GPU-accelerated, 32+ qubits
  cuquantum              cuQuantum — NVIDIA GPU simulator, 30+ qubits

===============================================================
CLASSICAL PROVIDERS (10 Total)
===============================================================

CPUs (5):
  local_cpu              Local CPU — NumPy/SciPy, always available ✅
  intel                  Intel oneAPI — optimized for Intel CPUs
  amd                    AMD — optimized for AMD CPUs  
  arm                    ARM — ARM processors
  risc_v                 RISC-V — RISC-V architectures

GPUs (4):
  nvidia_cuda            NVIDIA CUDA — CuPy GPU acceleration
  amd_rocm               AMD ROCm — AMD GPU compute (PyTorch)
  intel_oneapi           Intel oneAPI — Intel GPU support
  apple_metal            Apple Metal — M-series GPU (macOS only)

ACCELERATORS (3):
  tpu                    Google TPU — Tensor Processing Units
  fpga                   FPGA — Field-Programmable Gate Arrays
  npu                    NPU — Neural Processing Units

===============================================================
QUICK START
===============================================================

WORKS RIGHT NOW (No setup needed):
  connect local_simulator    Quantum simulation, 20 qubits, instant
  connect local_cpu          Classical compute, NumPy/SciPy

SETUP REQUIRED (Install SDK first):
  providers install ibm_quantum      Show install command
  connect ibm_quantum                Connect after SDK install

EXAMPLES:
  providers info ibm_quantum         Full details about IBM Quantum
  providers quantum                  List all quantum providers
  providers install aws_braket       Show AWS Braket install steps
''',
                'connect': '''connect <provider_id> [OPTIONS] - Connect to a compute provider

Phase 3 Step 4: 30 provider adapters available!

Establishes connection to quantum or classical provider.
SDK must be installed first (use 'providers install <id>').

IMPORTANT: Most cloud providers require paid accounts or credits.
Only local_simulator and local_cpu are completely free.

═══════════════════════════════════════════════════════════════
CREDENTIAL MANAGEMENT (3 METHODS)
═══════════════════════════════════════════════════════════════

METHOD 1: Inline credentials (Quick testing)
  connect ibm_quantum --token "YOUR_API_TOKEN"
  connect aws_braket --credentials '{"access_key":"...","secret":"..."}'

METHOD 2: Provider's native storage (RECOMMENDED - Most secure)
  Each SDK has built-in encrypted credential storage:
  
  IBM Quantum (saves to ~/.qiskit/qiskit-ibm.json):
    python -c "from qiskit_ibm_runtime import QiskitRuntimeService; \
               QiskitRuntimeService.save_account(token='YOUR_TOKEN')"
  
  AWS (saves to ~/.aws/credentials):
    aws configure
    # Enter: Access Key ID, Secret Access Key, Region
  
  Azure (saves to Azure CLI config):
    az login
    # Follow browser authentication
  
  Google Cloud (saves to ~/.config/gcloud):
    gcloud auth application-default login

METHOD 3: Environment variables (CI/CD, automation)
  export IBM_QUANTUM_TOKEN="your_token"
  export AWS_ACCESS_KEY_ID="your_key"
  export AWS_SECRET_ACCESS_KEY="your_secret"
  export AZURE_SUBSCRIPTION_ID="your_sub_id"
  # Then: connect <provider_id>

SECURITY BEST PRACTICES:
  ✓ Use Method 2 (native SDK storage) for production
  ✓ Use Method 1 for quick testing only
  ✓ NEVER commit credentials to Git
  ✓ Use .env files with .gitignore for local development
  ✓ Rotate API keys regularly
  ✓ Use separate keys for dev/production

═══════════════════════════════════════════════════════════════
FREE - AVAILABLE RIGHT NOW (No credentials, no costs)
═══════════════════════════════════════════════════════════════

  connect local_simulator    20 qubits, instant, offline, FREE ✅
  connect local_cpu          NumPy/SciPy, always available, FREE ✅

═══════════════════════════════════════════════════════════════
CLOUD QUANTUM (Requires credentials + COSTS MONEY 💰)
═══════════════════════════════════════════════════════════════

⚠️  WARNING: These providers charge for usage beyond free tiers!
    Always check pricing before connecting.

IBM Quantum (FREE tier: 10 min/month, then paid)
  Setup:
    1. pip install qiskit qiskit-ibm-runtime
    2. Create account: https://quantum.ibm.com
    3. Get API token from account settings
    4. Save token:
       python -c "from qiskit_ibm_runtime import QiskitRuntimeService; \
                  QiskitRuntimeService.save_account(token='YOUR_TOKEN')"
    5. connect ibm_quantum
  
  OR pass token inline:
    connect ibm_quantum --token "YOUR_API_TOKEN"

AWS Braket (FREE tier: 1 hour simulator/month, then $$$)
  Setup:
    1. pip install amazon-braket-sdk
    2. Create AWS account: https://aws.amazon.com
    3. Enable Braket service in AWS Console
    4. Configure AWS CLI:
       aws configure
       # Enter Access Key ID, Secret Key, Region (us-east-1)
    5. connect aws_braket
  
  Pricing: ~$0.30/task (QPU), $0.075/min (simulator)

Azure Quantum (FREE credits: $500 for new accounts, then paid)
  Setup:
    1. pip install azure-quantum
    2. Create Azure account: https://portal.azure.com
    3. Create Quantum Workspace
    4. az login  (authenticate via browser)
    5. connect azure_quantum --credentials '{
         "subscription_id": "YOUR_SUB_ID",
         "resource_group": "YOUR_RG",
         "workspace_name": "YOUR_WS"
       }'
  
  Pricing: Varies by provider (IonQ, Quantinuum)

Google Quantum AI (Research access only - APPLICATION REQUIRED)
  Setup:
    1. pip install cirq cirq-google
    2. Apply for access: https://quantumai.google/
    3. Wait for approval (can take weeks/months)
    4. Set up Google Cloud project
    5. gcloud auth application-default login
    6. connect google_cirq --credentials '{"project_id": "YOUR_PROJECT"}'
  
  Note: Not publicly available, research partners only

NVIDIA Quantum Cloud (Requires NVIDIA NGC account)
  Setup:
    1. Create NGC account: https://ngc.nvidia.com
    2. Generate API key from NGC portal
    3. connect nvidia_quantum_cloud --credentials '{"api_key": "YOUR_KEY"}'
  
  Note: Pricing varies, check NVIDIA website

═══════════════════════════════════════════════════════════════
HARDWARE VENDORS (Via cloud platforms, mostly PAID)
═══════════════════════════════════════════════════════════════

IonQ (Via AWS Braket or Azure, ~$0.30/task)
  connect ionq  # After configuring AWS/Azure credentials

Rigetti (Via AWS Braket, ~$0.30/task)
  connect rigetti  # After configuring AWS credentials

Quantinuum (Via Azure Quantum, most expensive - $$$$)
  connect quantinuum  # After configuring Azure credentials

Xanadu (FREE tier available via Xanadu Cloud)
  Setup:
    1. pip install pennylane
    2. Create account: https://cloud.xanadu.ai
    3. Get API token
    4. connect xanadu --token "YOUR_TOKEN"

D-Wave (FREE minute/month, then paid)
  Setup:
    1. pip install dwave-ocean-sdk
    2. Create account: https://cloud.dwavesys.com
    3. Get API token
    4. dwave config create  (interactive setup)
    5. connect dwave

IQM (European superconducting, 20 qubits)
  connect iqm --token "YOUR_TOKEN"

QuEra (Neutral atom, 256 qubits, via AWS Braket)
  connect quera --token "YOUR_TOKEN"

Oxford Quantum Circuits (UK, superconducting, 32 qubits)
  connect oxford --token "YOUR_TOKEN"

Atom Computing (Neutral atom, 1225 qubits)
  connect atom_computing --token "YOUR_TOKEN"

Pasqal (France, neutral atom, 200 qubits)
  connect pasqal --token "YOUR_TOKEN"

AQT Alpine Quantum Technologies (Austria, trapped-ion, FREE tier)
  connect aqt --token "YOUR_TOKEN"

═══════════════════════════════════════════════════════════════
SIMULATORS (Requires GPU hardware, NO cloud costs)
═══════════════════════════════════════════════════════════════

Qiskit Aer (FREE - local GPU/CPU simulation)
  connect qiskit_aer  # No credentials needed

cuQuantum (FREE - requires NVIDIA GPU)
  connect cuquantum  # No credentials needed

═══════════════════════════════════════════════════════════════
GPU ACCELERATION (Requires hardware, NO cloud costs)
═══════════════════════════════════════════════════════════════

NVIDIA CUDA (FREE - requires NVIDIA GPU)
  connect nvidia_cuda  # No credentials needed

AMD ROCm (FREE - requires AMD GPU)
  connect amd_rocm  # No credentials needed

Apple Metal (FREE - requires M1/M2/M3 Mac)
  connect apple_metal  # No credentials needed

Intel oneAPI (FREE - optimized for Intel hardware)
  connect intel_oneapi  # No credentials needed

═══════════════════════════════════════════════════════════════
OTHER COMPUTE (Requires hardware, NO cloud costs)
═══════════════════════════════════════════════════════════════

ARM Compute (FREE - ARM processors, Raspberry Pi, etc.)
  connect arm  # No credentials needed

RISC-V Compute (FREE - open ISA, emerging platform)
  connect risc_v  # No credentials needed

Google TPU (FREE via Colab, or Google Cloud project)
  connect tpu  # May need GCP project_id for cloud TPU

FPGA (FREE - requires FPGA hardware, Xilinx/Intel)
  connect fpga  # No credentials needed

NPU (FREE - Intel/Qualcomm Neural Processing Unit)
  connect npu  # No credentials needed

═══════════════════════════════════════════════════════════════
VERIFICATION & TROUBLESHOOTING
═══════════════════════════════════════════════════════════════

After connecting:
  providers                  Verify connection (shows ✅ checkmark)
  providers info <id>        See available backends

Common issues:
  - "SDK not installed" → providers install <id>
  - "Authentication failed" → Check credentials are correct
  - "No backends available" → Provider may be down, check status page
  - "Quota exceeded" → Check account credits/usage limits

Disconnect when done to avoid accidental charges:
  disconnect <id>           Release connection safely
  disconnect all            Disconnect all providers

═══════════════════════════════════════════════════════════════
COST SUMMARY (Approximate, check current pricing)
═══════════════════════════════════════════════════════════════

FREE (No limits):
  ✅ local_simulator, local_cpu, qiskit_aer, cuquantum
  ✅ All GPU providers (if you have hardware)

FREE Tier (Limited):
  ⚡ IBM Quantum: 10 min/month free
  ⚡ AWS Braket: 1 hour simulator/month free
  ⚡ Azure Quantum: $500 credits for new accounts
  ⚡ Xanadu: Limited free tier
  ⚡ D-Wave: 1 minute/month free

PAID (No free tier):
  💰 Google Quantum AI: Research only, pricing N/A
  💰 IonQ: ~$0.30/task via AWS/Azure
  💰 Rigetti: ~$0.30/task via AWS
  💰 Quantinuum: $$$ (most expensive)

RECOMMENDATION FOR TESTING:
  1. Start with local_simulator (completely free)
  2. Experiment with IBM Quantum free tier (10 min/month)
  3. Try AWS Braket free tier (1 hour/month)
  4. Only use paid providers for production workloads

⚠️  IMPORTANT: Always monitor your usage and set billing alerts!
''',
                'disconnect': '''disconnect <provider_id> | disconnect all - Disconnect from providers

Safely disconnects from quantum or classical providers.
Releases resources and clears credentials from memory.

EXAMPLES:
  disconnect ibm_quantum         Disconnect from IBM Quantum
  disconnect local_simulator     Disconnect from local simulator
  disconnect nvidia_cuda         Release GPU resources
  disconnect all                 Disconnect ALL active providers

BEST PRACTICES:
- Disconnect cloud providers when done to avoid accidental usage
- Disconnect GPU providers to free VRAM for other applications
- Use 'disconnect all' before switching between projects

VERIFICATION:
  providers                      Check connection status after disconnect
''',
                'credentials': '''credentials [save|list|delete|show|verify] - Manage provider API keys

SUBCOMMANDS:
  credentials                          Show usage guide
  credentials save <id> --token TOKEN  Save API token for a provider
  credentials save <id> --credentials '{...}'  Save JSON credentials
  credentials list                     List providers with saved credentials
  credentials show <id>                Show saved credentials (masked)
  credentials delete <id>              Delete saved credentials
  credentials verify <id>              Test if saved credentials work

EXAMPLES:
  credentials save ibm_quantum --token "crn:v1:abc123..."
  credentials save aws_braket --credentials '{"aws_access_key_id":"AKIA...","aws_secret_access_key":"...","region_name":"us-east-1"}'
  credentials verify ibm_quantum
  credentials list
  credentials delete ibm_quantum

NOTES:
  Credentials stored in ~/.frankenstein/credentials.json
  File permissions set to owner-only (600 on Unix) for basic protection
  Use 'credentials verify <id>' to test before connecting
  After saving, just run 'connect <id>' - credentials load automatically
''',
                # Diagnostics
                'diagnose': 'diagnose [refresh|fix|kill|quick] - System diagnostics and optimization',
                # Intelligent Router (Phase 3 Step 5)
                'route': '''route - Route workloads to optimal compute providers

INTELLIGENT ROUTER (Phase 3 Step 5)

Routes quantum and classical workloads to the best available
provider based on hardware, resources, and user priority.

USAGE:
  route --qubits N --priority MODE
  route --type TYPE --qubits N --depth N
  route --type classical_optimization --threads 2 --memory 512

OPTIONS:
  --type TYPE       Workload type:
                      quantum_simulation (default if --qubits > 0)
                      classical_optimization (default otherwise)
                      hybrid_computation
                      data_synthesis
  --qubits N        Number of qubits (default 0)
  --depth N         Circuit depth (default 0)
  --threads N       CPU threads needed (default 1)
  --memory N        Memory in MB (default 100)
  --priority MODE   cost | speed | accuracy (default cost)

SAFETY:
  Hard limits enforced: CPU max 80%, RAM max 70%
  Routes that would exceed limits are automatically blocked.

EXAMPLES:
  route --qubits 10 --priority cost      Small quantum, prefer free
  route --qubits 30 --priority accuracy  Large quantum, best fidelity
  route --type classical_optimization    Classical CPU routing

RELATED COMMANDS:
  route-options    Show all compatible providers ranked
  route-test       Test routing to a specific provider
  route-history    Show past routing decisions
''',
                'route-options': 'route-options --type TYPE --qubits N - Show all compatible providers ranked',
                'route-test': 'route-test --provider NAME --qubits N - Test routing to a specific provider',
                'route-history': 'route-history [--limit N] - Show past routing decisions',
                # Permissions & Automation (Phase 3 Step 6)
                'permissions': '''permissions - Permission management system

PERMISSION MANAGEMENT (Phase 3 Step 6)

Manage user roles, access control, and audit logging for
all quantum and classical compute providers.

USAGE:
  permissions                     Show permission summary
  permissions set-role ROLE       Set user role (Admin, User, Agent, ReadOnly)
  permissions check PERMISSION    Check if permission is allowed
  permissions providers           Show accessible providers
  permissions audit [DAYS]        Show audit log (default: 7 days)
  permissions reset               Reset to default settings

ROLES:
  Admin     - Full access to all 28 providers, automation control
  User      - Submit jobs to quantum (15) and classical (13) providers
  Agent     - Automated workflows only, no manual job submission
  ReadOnly  - View-only access, no job submission

PERMISSIONS:
  quantum_job_submit         Submit quantum jobs
  classical_compute_submit   Submit classical jobs
  automation_control         Control automated workflows
  permission_modify          Modify permission settings
  provider_connect           Connect to providers
  credential_modify          Modify credentials

EXAMPLES:
  permissions set-role Admin
  permissions check quantum_job_submit
  permissions providers
  permissions audit 30

RELATED COMMANDS:
  setup       Run setup wizard for permissions
  automation  Manage automated workflows
''',
                'setup': '''setup - Setup wizard for permissions and automation

SETUP WIZARD (Phase 3 Step 6)

Interactive wizard to configure user role, automation preferences,
and workflow settings for Frankenstein 1.0.

USAGE:
  setup             Run interactive setup wizard
  setup --default   Apply default configuration (Admin role, automation enabled)

SETUP STEPS:
  1. Select user role (Admin, User, Agent, ReadOnly)
  2. Enable/disable automation
  3. Configure automated workflows:
     - Quantum queue optimization
     - Classical queue optimization
     - Credential expiry checking
     - Resource report generation
     - Provider health monitoring
     - Hardware auto-tuning

DEFAULT CONFIGURATION:
  Role: Admin
  Automation: Enabled
  All workflows: Enabled (except auto_tune_hardware)

EXAMPLES:
  setup             Interactive setup
  setup --default   Quick default setup
''',
                'automation': '''automation - Automation workflow management

AUTOMATED WORKFLOWS (Phase 3 Step 6)

Manage background automation workflows that optimize queue
management, monitor provider health, and tune hardware.

USAGE:
  automation                      Show automation status
  automation start                Start automation engine
  automation stop                 Stop automation engine
  automation status               Show workflow execution status
  automation run WORKFLOW         Run a workflow manually
  automation consent WORKFLOW     Grant termination consent
  automation revoke WORKFLOW      Revoke termination consent

WORKFLOWS (6 Total):
  quantum_queue         Optimize quantum job queue (every 5 min)
  classical_queue       Optimize classical compute queue (every 5 min)
  credential_expiry     Check for expiring credentials (daily)
  resource_report       Generate resource usage reports (daily)
  provider_health       Monitor provider status (every 15 min)
  hardware_tuning       Auto-tune hardware parameters (hourly)

RESOURCE SAFETY:
  CPU limit: 80% maximum
  RAM limit: 75% maximum
  Workflows paused if limits exceeded

TERMINATION CONSENT:
  Some workflows may terminate stuck/failed jobs.
  User consent required before termination.

EXAMPLES:
  automation start
  automation run quantum_queue
  automation consent quantum_queue
  automation status

RELATED COMMANDS:
  scheduler     Manage scheduled tasks
  permissions   Configure automation permissions
''',
                'scheduler': '''scheduler - Task scheduler management

TASK SCHEDULER (Phase 3 Step 6)

Manage scheduled background tasks for automation workflows.
Tasks run at configured intervals (every 5 min, hourly, daily).

USAGE:
  scheduler              Show scheduler status
  scheduler tasks        List all scheduled tasks
  scheduler pause TASK   Pause a task
  scheduler resume TASK  Resume a paused task
  scheduler stop         Stop the scheduler

SCHEDULE TYPES:
  Once       - Run once at specified time
  Recurring  - Run repeatedly at interval
  Daily      - Run once per day

TASK STATUS:
  pending   - Waiting to run
  running   - Currently executing
  paused    - Temporarily paused
  stopped   - Stopped, won't run again
  failed    - Execution failed

SAFETY FEATURES:
  - Resource monitoring (CPU < 80%, RAM < 75%)
  - Auto-pause on high resource usage
  - Error tracking and retry logic
  - Graceful shutdown on stop

EXAMPLES:
  scheduler tasks
  scheduler pause quantum_queue_task
  scheduler resume quantum_queue_task

RELATED COMMANDS:
  automation    Manage workflows
  permissions   Configure scheduler permissions
''',
                'routing': '''routing - Intelligent Router Help Topic

PHASE 3 STEP 5: INTELLIGENT WORKLOAD ROUTER

The router automatically selects the best quantum or classical
compute provider for your workload.

HOW IT WORKS:
  1. Analyzes your workload (qubits, memory, priority)
  2. Detects available hardware (CPU, GPU, tier)
  3. Checks resource safety (CPU < 80%, RAM < 70%)
  4. Scores providers (cost, speed, accuracy)
  5. Returns optimal provider + fallback chain

ROUTING RULES:
  Quantum:
    <=5 qubits   -> Local simulators (free, instant)
    6-20 qubits  -> Local sim + cloud fallback
    21-29 qubits -> Cloud providers (IBM, AWS, Azure)
    30+ qubits   -> Large-scale providers (IonQ, Rigetti, QuEra)

  Classical:
    NVIDIA GPU   -> nvidia_cuda
    AMD GPU      -> amd_rocm
    Apple Silicon -> apple_metal
    Intel CPU    -> intel_oneapi, local_cpu
    Default      -> local_cpu (NumPy/SciPy)

PRIORITY MODES:
  cost     -> Prefer free/local providers (default)
  speed    -> Prefer fastest execution
  accuracy -> Prefer highest fidelity

COMMANDS:
  route --qubits 10 --priority cost
  route-options --type quantum_simulation --qubits 5
  route-test --provider ibm_quantum --qubits 10
  route-history
''',
                # Quantum Mode
                'quantum': '''quantum - Enter quantum computing REPL mode

ENTERING QUANTUM MODE:
  Just type 'quantum' or 'q' to enter the quantum computing sub-shell.
  
QUANTUM MODE COMMANDS (once inside):
  qubit <n>       Initialize n qubits in |0> state
  qubit <n>       Initialize n qubits in state |0>
  qubit STATE     Initialize specific state (|+>, |0>, etc)
  h <q>           Hadamard gate on qubit q
  x/y/z <q>       Pauli gates
  rx/ry/rz <q> θ  Rotation gates (use 'pi' for π)
  cx <c> <t>      CNOT gate (control c, target t)
  measure         Measure qubits and launch Bloch sphere visualization
  bloch           Launch Bloch sphere visualization
  bell            Quick Bell state creation
  ghz [n]         Quick GHZ state (n qubits)
  evolve H t      Time evolution under Hamiltonian
  back            Return to main terminal

AUTO-VISUALIZATION:
  After each 'measure' command, the 3D Bloch sphere opens in browser.
  Use 'viz off' to disable, 'viz on' to enable.

EXAMPLE SESSION:
  frankenstein> quantum
  quantum[1q|0g]> qubit 2
  quantum[2q|0g]> h 0
  quantum[2q|1g]> cx 0 1
  quantum[2q|2g]> measure
  [3D Bloch sphere opens in browser]
  quantum[2q|2g]> back
  frankenstein>
''',
                'q': 'q - Shortcut to enter quantum mode (same as quantum)',
                # Synthesis Engine
                'synthesis': '''synthesis - Schrödinger-Lorentz quantum simulation engine

SYNTHESIS COMMANDS:
  synthesis run <preset>     Run simulation (gaussian, tunneling, harmonic, relativistic)
  synthesis gaussian [σ] [k] Gaussian wave packet evolution
  synthesis tunneling [V₀]   Quantum tunneling simulation
  synthesis harmonic [ω]     Harmonic oscillator
  synthesis lorentz <v>      Set Lorentz boost velocity (v/c)
  synthesis compare <v>      Compare lab vs boosted frame
  synthesis visualize        Show ASCII visualization
  synthesis status           Engine status
  synthesis help             Full command list

OPTIONS:
  --velocity V    Set velocity for relativistic simulations
  --points N      Grid points (default: 256, max: 512)
  --time T        Simulation time (default: 10.0)

EXAMPLES:
  synthesis run gaussian --velocity 0.3
  synthesis tunneling 5.0
  synthesis compare 0.5
''',
                'synth': 'synth - Alias for synthesis command',
                'bloch': '''bloch [type] - Launch 3D Bloch sphere visualization

TYPES:
  bloch rabi         Rabi oscillation (default)
  bloch precession   Free precession
  bloch spiral       Spiral trajectory
  bloch hadamard     Hadamard gate evolution

OPTIONS:
  --omega W      Rabi frequency (default: 1.0)
  --gamma G      Lorentz gamma factor

EXAMPLES:
  bloch              (launches rabi by default)
  bloch spiral --gamma 1.25
  bloch precession --omega 2.0
''',
                'qubit': 'qubit <n> or qubit |state> - Quick qubit initialization (shortcut)',
            }
            if cmd in help_text:
                self._write_output(f"\n{help_text[cmd]}\n\n")
            else:
                self._write_error(f"help: no help for '{cmd}'")
            return
        
        help_msg = """
╔==================================================================╗
║                    FRANKENSTEIN TERMINAL HELP                    ║
╚==================================================================╝

NAVIGATION:
  cd [DIR]        Change directory (~ for home, .. for parent)
  pwd             Print working directory
  ls [-la]        List files (-l long, -a all including hidden)

FILE OPERATIONS:
  cat FILE        Display file contents
  head [-n N]     Show first N lines (default 10)
  tail [-n N]     Show last N lines (default 10)
  touch FILE      Create empty file
  mkdir [-p] DIR  Create directory (-p for parents)
  rm [-rf] FILE   Remove file (-r recursive, -f force)
  cp [-r] S D     Copy source to destination
  mv SRC DEST     Move/rename files

UTILITIES:
  echo TEXT       Print text (supports $VAR)
  grep PAT FILE   Search for pattern in files
  find PATH       Find files recursively
  wc FILE         Count lines/words/chars
  clear           Clear screen
  history         Show command history
  date            Show current date/time
  whoami          Show current user

FRANKENSTEIN:
  status          Show system status
  frank quote     Get an inspirational quote
  frank version   Show version info

GIT (ENHANCED - Progress Bars & Colors):
  git             Show enhanced Git features menu
  git clone       Clone with real-time progress ⚡
  git status      Color-coded files (✅📝❓)
  git log         Visual commit graph with colors
  git branch      Highlighted branch list
  git remote      Show remotes with indicators
  git pull/push   Network operations with progress
  git add/commit  Standard Git commands (all supported)

SSH:
  ssh             Connect to remote host
  scp             Secure copy files
  ssh-keygen      Generate SSH keys

PACKAGE MANAGERS:
  pip             Python package manager
  npm             Node.js package manager
  conda           Conda package manager

TEXT EDITORS:
  nano/vim        Terminal editors
  notepad         Windows notepad
  code            VS Code

ENVIRONMENT:
  export VAR=val  Set environment variable
  env             Show all variables
  set/unset       Set/unset variables
  printenv        Print variable value

SCRIPTING:
  source FILE     Run script (.sh/.bat/.py)
  python          Run Python
  node            Run Node.js

SECURITY:
  security        Show security dashboard
  security status Full threat level display
  security log    View security event feed
  security report Detailed threat analysis
  security test   Run security self-test

HARDWARE:
  hardware        Show hardware health dashboard
  hardware status Full health display with diagnosis
  hardware trend  Resource trend analysis
  hardware tiers  Hardware tier reference
  hardware recommend  Switch recommendation

PROVIDERS (Phase 3 Step 4: 30 Quantum + Classical Adapters):
  providers       List all 30 compute providers with SDK status
  providers quantum   List 19 quantum providers
  providers classical List 10 classical providers
  providers info <id> Detailed info on a specific provider
  providers install <id>  Show install command for provider SDK
  connect <id>    Connect to a provider (e.g. connect ibm_quantum)
  disconnect <id> Disconnect from a provider
  
  +----------------------------------------------------+
  |  QUICK START — 30 PROVIDERS AVAILABLE:            |
  |                                                    |
  |  WORKS RIGHT NOW (no setup):                      |
  |    connect local_simulator  (20 qubits, instant)  |
  |    connect local_cpu        (NumPy/SciPy)         |
  |                                                    |
  |  CLOUD QUANTUM (setup required):                  |
  |    providers install ibm_quantum                  |
  |    connect ibm_quantum  (127 qubits, free tier)   |
  |    connect aws_braket   (multi-provider access)   |
  |    connect azure_quantum (IonQ + Quantinuum)      |
  |    connect google_cirq  (72 qubits)               |
  |                                                    |
  |  GPU ACCELERATION:                                |
  |    connect nvidia_cuda  (100x speedup)            |
  |    connect amd_rocm     (AMD GPUs)                |
  |    connect apple_metal  (M-series Macs)           |
  |                                                    |
  |  Full list: help providers                        |
  |  Details: help connect                            |
  +----------------------------------------------------+

DIAGNOSTICS:
  diagnose        Run full system diagnosis
  diagnose refresh    Refresh diagnosis report
  diagnose fix <n>    Apply recommendation #n
  diagnose kill <name>  Terminate a process
  diagnose quick      Quick CPU/RAM stats

INTELLIGENT ROUTER (Phase 3 Step 5):
  route --qubits N --priority MODE    Route workload to optimal provider
  route-options --type TYPE --qubits N  Show all compatible providers
  route-test --provider NAME --qubits N Test routing to specific provider
  route-history                       Show past routing decisions

  +----------------------------------------------------+
  |  ROUTING QUICK START:                              |
  |                                                    |
  |  route --qubits 10 --priority cost                |
  |    Routes 10-qubit simulation to best free option  |
  |                                                    |
  |  route --qubits 30 --priority accuracy            |
  |    Routes to highest-fidelity quantum hardware     |
  |                                                    |
  |  route --type classical_optimization              |
  |    Routes classical workload to best local compute|
  |                                                    |
  |  Safety: CPU max 80%, RAM max 70% enforced        |
  |  Details: help route  |  Topics: help routing     |
  +----------------------------------------------------+

PERMISSIONS AND AUTOMATION (Phase 3 Step 6):
  help permissions     Manage user roles and access control
  help setup           Setup wizard for permissions and automation
  help automation      Manage automated workflows (6 workflows)
  help scheduler       Task scheduler management

  +----------------------------------------------------+
  |  PERMISSIONS & AUTOMATION QUICK START:             |
  |                                                    |
  |  setup --default                                  |
  |    Quick setup with Admin role and automation on   |
  |                                                    |
  |  permissions                                      |
  |    View your role, permissions, and provider access|
  |                                                    |
  |  automation start                                 |
  |    Start 6 background workflows (queue optimization|
  |    credential checking, health monitoring)         |
  |                                                    |
  |  scheduler tasks                                  |
  |    View all scheduled tasks and their status       |
  |                                                    |
  |  4 Roles: Admin, User, Agent, ReadOnly            |
  |  28 Providers: 15 quantum + 13 classical          |
  |  6 Workflows: Queue optimization, health checks   |
  |  Safety Limits: CPU max 80%, RAM max 75%          |
  |                                                    |
  |  Details: help permissions  |  help automation    |
  +----------------------------------------------------+

QUANTUM MODE:
  quantum         Enter quantum computing mode (or 'q')
  qubit <n>       Quick qubit initialization
  
  +----------------------------------------------------+
  |  QUANTUM MODE QUICK START:                        |
  |                                                    |
  |  1. Type 'quantum' or 'q' to enter quantum mode   |
  |  2. Initialize: qubit 2  (creates 2 qubits)       |
  |  3. Apply gates: h 0, cx 0 1  (Bell state)        |
  |  4. Measure: measure  (auto-shows 3D Bloch!)      |
  |  5. Type 'back' to return to main terminal        |
  |                                                    |
  |  Shortcuts: bell, ghz, qft for common circuits    |
  |  Toggle viz: viz off (disable auto-visualization) |
  +----------------------------------------------------+

SYNTHESIS ENGINE:
  synthesis       Schrödinger-Lorentz quantum simulations
  synth           Alias for synthesis
  bloch [type]    Launch 3D Bloch sphere (rabi, spiral, precession)
  
  +----------------------------------------------------+
  |  SYNTHESIS QUICK COMMANDS:                        |
  |                                                    |
  |  synthesis run gaussian    - Wave packet evolution|
  |  synthesis run tunneling   - Quantum tunneling    |
  |  synthesis run harmonic    - Harmonic oscillator  |
  |  synthesis lorentz 0.5     - Apply Lorentz boost  |
  |  synthesis compare 0.3     - Lab vs boosted frame |
  |  bloch rabi                - 3D Rabi oscillation  |
  |  bloch spiral --gamma 1.2  - Relativistic spiral  |
  +----------------------------------------------------+

TIPS:
  - Use Tab for path completion
  - Use Up/Down arrows for command history
  - Right-click for copy/paste menu
  - Any command not listed runs as system command

Type 'help COMMAND' for detailed help on a specific command.
"""
        self._write_output(help_msg)


# ==================== GLOBAL INSTANCE ====================

_terminal: Optional[FrankensteinTerminal] = None

def get_terminal() -> FrankensteinTerminal:
    """Get or create the global terminal instance"""
    global _terminal
    if _terminal is None:
        _terminal = FrankensteinTerminal()
    return _terminal


def launch_terminal():
    """Launch the terminal (convenience function)"""
    terminal = get_terminal()
    if not terminal._running:
        terminal.start()
    return terminal


# Allow running directly
if __name__ == "__main__":
    print("🧟 Launching Frankenstein Terminal...")
    terminal = launch_terminal()
    
    # Keep main thread alive
    try:
        while terminal._running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n👋 Terminal closed.")
