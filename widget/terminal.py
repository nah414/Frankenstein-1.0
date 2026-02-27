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
            # Artifact overview
            'saves': self._cmd_saves_overview,
            # Memory Management (Pre-Phase 4)
            'memory': self._cmd_memory,
            # Circuit Library (Pre-Phase 4)
            'circuit': self._cmd_circuit,
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
            # Real-Time Adaptation (Phase 3 Step 7)
            'adapt-status': self._cmd_adapt_status,
            'adapt-patterns': self._cmd_adapt_patterns,
            'adapt-performance': self._cmd_adapt_performance,
            'adapt-insights': self._cmd_adapt_insights,
            'adapt-recommend': self._cmd_adapt_recommend,
            'adapt-history': self._cmd_adapt_history,
            'adapt-dashboard': self._cmd_adapt_dashboard,
            # Phase 4 / Day 7 — Eye of Sauron (displays as [FRANK])
            'sauron': self._cmd_frank_ai,
            'eye':    self._cmd_frank_ai,  # shortcut alias
        }

        # Security monitor integration
        self._security_monitor = None
        self._security_dashboard = None

        # Hardware monitor integration
        self._hardware_monitor = None

        # Quantum mode integration
        self._quantum_mode = None
        self._in_quantum_mode = False

        # Real-time adaptation integration (Phase 3 Step 7)
        self._adaptation_commands = None  # Lazy-loaded

        # Eye of Sauron integration (Phase 4 / Day 7 — displays as [FRANK])
        self._in_frank_mode      = False   # True when interactive chat is active
        self._frank_thread       = None    # Background daemon thread during inference
        self._frank_thinking     = False   # True while waiting for streamed tokens
        self._frank_last_active  = None    # float timestamp — for idle auto-unload
        self._frank_stop_event   = None    # threading.Event — signals interrupt/stop
        self._frank_spinner_idx  = 0       # Cycles through spinner frames
        self._frank_monitor_label = None   # CTkLabel in monitor panel for FRANK status
        self._frank_idle_after_id = None   # tkinter after() ID for idle watchdog
        # Permission guard state (FRANK terminal execution — build guide)
        self._frank_pending_cmd     = None   # str: command awaiting user approval
        self._frank_pending_quantum = None   # tuple(action, kwargs): quantum op awaiting approval
        self._frank_pending_tier    = 0      # int: 1=DESTROY needs CONFIRM, 2=MODIFY needs y/n
        self._frank_exec_log        = []     # list[dict]: session audit trail
        self._frank_exec_buffer     = ""     # str: token accumulator for ::EXEC:: / ::QUANTUM:: detection
        self._quantum_tool          = None   # QuantumTool singleton for FRANK chat dispatch
    
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
            width=240,
            height=208,
            fg_color=self._colors['bg_light'],
            border_width=2,
            border_color=self._colors['electric_purple'],
            corner_radius=10
        )
        self._monitor_frame.place(relx=1.0, rely=0.0, x=-6, y=65, anchor="ne")
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
            wraplength=195,
            justify="left"
        )
        self._diagnosis_label.place(x=8, y=132)

        # ===== FRANK AI SECTION =====
        ctk.CTkLabel(
            self._monitor_frame,
            text="-" * 30,
            font=("Consolas", 6),
            text_color=self._colors['border_glow']
        ).place(x=4, y=140)

        ctk.CTkLabel(
            self._monitor_frame,
            text="[FRANK] AI",
            font=("Consolas", 9, "bold"),
            text_color=self._colors['electric_blue'],
            anchor="w"
        ).place(x=8, y=148)

        self._frank_monitor_label = ctk.CTkLabel(
            self._monitor_frame,
            text="● OFFLINE",
            font=("Consolas", 9),
            text_color=self._colors['text_secondary'],
            anchor="w"
        )
        self._frank_monitor_label.place(x=8, y=170)

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
        """Generate Git Bash-style prompt, or FRANK prompt when in chat mode."""
        if self._in_frank_mode:
            return "[FRANK]>"
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
                max_mem = 75

                # If hardware monitor was started by user, use its richer data
                if self._hardware_monitor and self._hardware_monitor._running:
                    try:
                        from core.hardware_monitor import HealthStatus
                        hw_stats = self._hardware_monitor.get_stats()
                        health = self._hardware_monitor.get_health_status()
                        max_cpu = hw_stats.get('tier_max_cpu', 80)
                        max_mem = hw_stats.get('tier_max_memory', 75)
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

            # ===== FRANK AI STATUS =====
            try:
                from agents.sauron import is_loaded
                if self._frank_monitor_label:
                    if not is_loaded():
                        self._frank_monitor_label.configure(
                            text="● OFFLINE",
                            text_color=self._colors['text_secondary']
                        )
                    elif self._frank_thinking:
                        self._frank_monitor_label.configure(
                            text="● THINKING",
                            text_color=self._colors['warning_amber']
                        )
                    else:
                        from agents.sauron import get_sauron
                        h = get_sauron().health_check()
                        turns = h.get('conversation_turns', 0)
                        max_t  = h.get('max_turns', '?')
                        self._frank_monitor_label.configure(
                            text=f"● ACTIVE  T:{turns}/{max_t}",
                            text_color="#7c3aed"
                        )
            except Exception:
                if self._frank_monitor_label:
                    self._frank_monitor_label.configure(
                        text="● OFFLINE",
                        text_color=self._colors['text_secondary']
                    )

        except Exception:
            pass

        # Schedule next update (every 30 seconds — per Day 7 spec)
        if self._running and self._root:
            self._root.after(30000, self._update_monitor_panel)

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
    |  🤖 [FRANK] AI   frank chat  |  Use !run <cmd> inside chat      |
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
        # Check if in FRANK chat mode — route input to FRANK handler
        if self._in_frank_mode:
            self._write_frank(f"[FRANK]> {command_line}\n")
            self._handle_frank_input(command_line)
            return

        # Check if in quantum mode - route to quantum handler
        if self._in_quantum_mode and self._quantum_mode:
            # Show prompt with command
            self._write_output(f"{self._quantum_mode.get_prompt()} {command_line}\n")
            
            # Handle in quantum mode
            stay_in_mode = self._quantum_mode.handle_command(command_line)
            
            if not stay_in_mode:
                self._in_quantum_mode = False
                self._update_prompt()
                # Restore FRANK to normal inference profile (Profile B)
                try:
                    from agents.sauron import is_loaded, get_sauron
                    if is_loaded():
                        get_sauron().set_quantum_active(False)
                except Exception:
                    pass
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
        """Frankenstein special commands + FRANK AI routing"""
        # AI subcommands — route to the FRANK AI handler
        _AI_SUBCMDS = {'chat', 'ask', 'agents', 'unload', 'reset'}
        if args and args[0].lower() in _AI_SUBCMDS:
            self._cmd_frank_ai(args)
            return

        if not args:
            self._frank_help_guide()
            return

        subcmd = args[0].lower()
        if subcmd == "help":
            self._frank_help_guide()
        elif subcmd == "status":
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
            self._write_error(f"frank: unknown command '{subcmd}'. Type 'frank help' for options.")

    # ==================== FRANK AI COMMANDS (Phase 4 / Day 7) ====================

    def _write_frank(self, text: str):
        """Write FRANK-branded output in purple (#7c3aed). Main thread only."""
        if not self._output_text:
            return
        try:
            # Configure the frank_output tag once per widget lifetime
            if not getattr(self, '_frank_tag_ready', False):
                self._output_text.tag_config("frank_output", foreground="#7c3aed")
                self._frank_tag_ready = True
            # Insert text and tag the inserted range
            start = self._output_text.index("end-1c")
            self._output_text.insert("end", text)
            end = self._output_text.index("end-1c")
            self._output_text.tag_add("frank_output", start, end)
            self._output_text.see("end")
        except Exception:
            # Fallback: plain white if tags unavailable
            self._output_text.insert("end", text)
            self._output_text.see("end")

    def _cmd_frank_ai(self, args: List[str]):
        """[FRANK] Eye of Sauron AI — Usage: frank [status|chat|ask|unload|reset|agents]"""
        subcmd = args[0].lower() if args else ""

        if not subcmd or subcmd == "help":
            self._frank_help_guide()
        elif subcmd == "status":
            self._frank_status()
        elif subcmd == "chat":
            self._frank_enter_chat()
        elif subcmd == "ask":
            if len(args) < 2:
                self._write_error("Usage: frank ask <your question>")
                return
            self._frank_ask_single(" ".join(args[1:]))
        elif subcmd == "agents":
            self._frank_list_agents()
        elif subcmd == "reset":
            self._frank_reset_history()
        elif subcmd == "unload":
            self._frank_unload()
        else:
            self._write_error(
                f"[FRANK] Unknown subcommand: '{subcmd}'. Type 'frank help'."
            )

    def _frank_status(self):
        """Show FRANK health status. Never triggers a model load."""
        from agents.sauron import is_loaded
        self._write_frank("\n[FRANK] Status\n")
        self._write_frank("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        if not is_loaded():
            self._write_frank("  State    :  OFFLINE\n")
            self._write_frank("  Model    :  not loaded  (~2.5 GB on first use)\n")
            self._write_frank("  Activate :  frank chat   or   frank ask <text>\n")
            self._write_frank("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")
            return
        try:
            from agents.sauron import get_sauron
            h = get_sauron().health_check()
            self._write_frank(
                f"  State    :  {'ACTIVE' if h.get('loaded') else 'STANDBY'}\n"
                f"  Model    :  {h.get('model', 'unknown')}\n"
                f"  Status   :  {h.get('status', '?')}\n"
                f"  Turns    :  {h.get('conversation_turns', 0)} / {h.get('max_turns', '?')}\n"
                f"  Threads  :  {h.get('inference_threads', '?')}\n"
                f"  CPU cap  :  {h.get('safety_cpu_limit', '?')}%\n"
                f"  RAM cap  :  {h.get('safety_ram_limit', '?')}%\n"
            )
        except Exception as e:
            self._write_frank(f"  State    :  ERROR\n  Detail   :  {e}\n")
        self._write_frank("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")

    def _frank_list_agents(self):
        """List all agents discoverable by the orchestrator."""
        self._write_frank("\n[FRANK] Discoverable Agents\n")
        self._write_frank("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        try:
            from agents.sauron.orchestrator import get_orchestrator
            agents = get_orchestrator().discover()
            for a in agents:
                icon = "✅" if a.available else "❌"
                self._write_frank(f"  {icon}  {a.name:<22}  {a.description}\n")
            self._write_frank(f"\n  Total: {len(agents)} agent(s) registered\n")
        except Exception as e:
            self._write_frank(f"  Error discovering agents: {e}\n")
        self._write_frank("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")

    def _frank_reset_history(self):
        """Clear FRANK conversation history without unloading the model."""
        from agents.sauron import is_loaded
        if not is_loaded():
            self._write_frank("\n[FRANK] Nothing to reset — model not loaded.\n\n")
            return
        try:
            from agents.sauron import get_sauron
            get_sauron().reset_conversation()
            self._write_frank("\n[FRANK] Conversation history cleared.\n\n")
        except Exception as e:
            self._write_error(f"[FRANK] Reset failed: {e}")

    def _frank_unload(self):
        """Unload FRANK model from RAM (~2.5 GB freed)."""
        from agents.sauron import is_loaded
        if not is_loaded():
            self._write_frank("\n[FRANK] Already offline — nothing to unload.\n\n")
            return
        # Cancel idle watchdog — model is going away
        if self._frank_idle_after_id:
            try:
                self._root.after_cancel(self._frank_idle_after_id)
            except Exception:
                pass
            self._frank_idle_after_id = None
        try:
            from agents.sauron import unload_sauron
            unload_sauron()
            self._frank_last_active = None
            self._write_frank("\n[FRANK] Unloaded. ~2.5 GB RAM freed.\n\n")
        except Exception as e:
            self._write_error(f"[FRANK] Unload failed: {e}")

    # ------------------------------------------------------------------
    # FRANK — Idle auto-unload watchdog (Step 5)
    # ------------------------------------------------------------------

    def _frank_start_idle_watch(self):
        """Arm the idle watchdog once — safe to call multiple times."""
        if self._frank_idle_after_id is None and self._running and self._root:
            self._frank_idle_after_id = self._root.after(
                60_000, self._frank_idle_check   # first check after 60 s
            )

    def _frank_idle_check(self):
        """Main thread: runs every 60 s. Auto-unloads after 10 min idle."""
        self._frank_idle_after_id = None   # mark slot as free before any early return
        if not self._running or not self._root:
            return
        try:
            from agents.sauron import is_loaded
            if (is_loaded()
                    and self._frank_last_active is not None
                    and not self._frank_thinking):
                idle_secs = time.time() - self._frank_last_active
                if idle_secs >= 600:   # 10 minutes
                    self._write_frank(
                        "\n[FRANK] Idle 10 min — auto-unloading to free RAM.\n"
                        "         Type 'frank chat' to reload.\n\n"
                    )
                    # Exit chat mode if still active
                    if self._in_frank_mode:
                        self._in_frank_mode = False
                        self._update_prompt()
                        if self._status_label:
                            self._status_label.configure(
                                text="  ● ALIVE  ",
                                text_color=self._colors['electric_green']
                            )
                    self._frank_last_active = None
                    try:
                        from agents.sauron import unload_sauron
                        unload_sauron()
                    except Exception:
                        pass
                    return   # don't reschedule — model is gone
        except Exception:
            pass
        # Reschedule for next 60 s window
        self._frank_idle_after_id = self._root.after(
            60_000, self._frank_idle_check
        )

    # ------------------------------------------------------------------
    # FRANK — Permission Guard (build guide Steps B-H)
    # ------------------------------------------------------------------

    # TIER 0 — regex patterns that are ALWAYS blocked, no override
    _FRANK_FORBIDDEN = [
        r'rm\s+-[a-z]*rf?\s+/',          # rm -rf /  (root wipe)
        r'rm\s+-[a-z]*rf?\s+\*',         # rm -rf *
        r'rm\s+-[a-z]*rf?\s+[cC]:\\',    # rm -rf C:\
        r'format\s+[cCdDeEfF]:',          # format c:
        r'format\s+/',                    # format /
        r'del\s+/s\s+/q\s+[cC]:\\',      # del /s /q C:\
        r'rmdir\s+/s\s+/q\s+[cC]:\\',    # rmdir /s /q C:\
        r'dd\s+if=/dev/',                 # dd overwrite disk
        r':\(\)\s*\{.*\|.*&.*\}',         # fork bomb
        r'DROP\s+DATABASE',               # SQL nuke
        r'DROP\s+TABLE',                  # SQL nuke
        r'TRUNCATE\s+TABLE',              # SQL nuke
        r'git\s+clean\s+.*-fdx\s+/',     # git clean force delete root
        r'git\s+reset\s+--hard\s+/',     # git reset hard on /
    ]

    # TIER 2 — command nouns that always need y/n (non-recursive file ops etc.)
    _FRANK_MODIFY_CMDS = {
        'cd', 'touch', 'mkdir', 'cp', 'copy', 'mv', 'move', 'echo',
        'nano', 'vim', 'vi', 'notepad', 'code',
        'export', 'set', 'unset', 'source',
        'ssh', 'scp', 'ssh-keygen',
        'connect', 'disconnect', 'credentials',
        'setup', 'automation', 'scheduler', 'route-test',
        'pip', 'npm', 'conda', 'python', 'node',
        'quantum', 'q', 'bloch', 'qubit',
        'synthesis', 'synth',
    }

    # TIER 2 — specific git subcommands that modify state
    _FRANK_MODIFY_GIT = {
        'add', 'commit', 'push', 'pull', 'merge',
        'checkout', 'clone', 'fetch', 'rebase', 'stash',
        'tag', 'cherry-pick',
    }

    def _frank_classify_risk(self, cmd_line: str):
        """
        Classify a command string into a permission tier.
        Returns (tier: int, label: str).
          0 = ABSOLUTE FORBIDDEN  — blocked, no override
          1 = DESTRUCTIVE         — requires typed CONFIRM
          2 = MODIFYING           — requires y/n
          3 = READ-ONLY           — auto-executes
        First-match-wins; checked in order 0 → 1 → 2 → 3.
        """
        import re
        raw   = cmd_line.strip()
        lower = raw.lower()
        parts = raw.split()
        if not parts:
            return (3, "empty command")
        noun  = parts[0].lower()

        # ── TIER 0: absolute forbidden (regex) ──────────────────────────
        for pattern in self._FRANK_FORBIDDEN:
            if re.search(pattern, raw, re.IGNORECASE):
                return (0, "ABSOLUTE FORBIDDEN — permanently blocked")

        # ── TIER 1: destructive — needs explicit CONFIRM ─────────────────
        # rm / del with recursive flag
        if noun in ('rm', 'del'):
            flags = ' '.join(parts[1:])
            if any(f in flags for f in ('-r', '-rf', '-fr', '/s', '--recursive')):
                return (1, "DESTRUCTIVE — recursive delete, cannot be undone")
        # rmdir always destructive
        if noun == 'rmdir':
            return (1, "DESTRUCTIVE — removes directory, cannot be undone")
        # git reset --hard / git clean
        if noun == 'git' and len(parts) >= 2:
            sub = parts[1].lower()
            if sub == 'reset' and '--hard' in lower:
                return (1, "DESTRUCTIVE — discards all uncommitted changes")
            if sub == 'clean':
                return (1, "DESTRUCTIVE — permanently deletes untracked files")
        # memory clear, circuit delete
        if noun == 'memory' and len(parts) >= 2 and parts[1].lower() == 'clear':
            return (1, "DESTRUCTIVE — clears stored memory, cannot be undone")
        if noun == 'circuit' and len(parts) >= 2 and parts[1].lower() == 'delete':
            return (1, "DESTRUCTIVE — deletes saved circuit, cannot be undone")
        if noun == 'frank' and len(parts) >= 2 and parts[1].lower() == 'reset':
            return (1, "DESTRUCTIVE — clears all conversation history")

        # ── TIER 2: modifying — needs y/n ────────────────────────────────
        # Plain rm (no recursive flag) — just a single file delete
        if noun in ('rm', 'del'):
            return (2, "MODIFYING — deletes a file")
        # git modifying subcommands
        if noun == 'git' and len(parts) >= 2:
            if parts[1].lower() in self._FRANK_MODIFY_GIT:
                return (2, "MODIFYING — changes git repository state")
        # pip uninstall
        if noun == 'pip' and len(parts) >= 2 and parts[1].lower() == 'uninstall':
            return (2, "MODIFYING — removes an installed package")
        # All other TIER 2 command nouns
        if noun in self._FRANK_MODIFY_CMDS:
            return (2, "MODIFYING — changes files or system state")
        # frank unload
        if noun == 'frank' and len(parts) >= 2 and parts[1].lower() == 'unload':
            return (2, "MODIFYING — frees model from RAM")
        # circuit save/load/export
        if noun == 'circuit' and len(parts) >= 2 and parts[1].lower() in ('save', 'load', 'export'):
            return (2, "MODIFYING — changes circuit library")
        # memory export
        if noun == 'memory' and len(parts) >= 2 and parts[1].lower() == 'export':
            return (2, "MODIFYING — writes memory to disk")

        # ── TIER 3: read-only — auto-executes ────────────────────────────
        return (3, "READ-ONLY — safe to run")

    def _frank_guard_exec(self, cmd_line: str):
        """
        Single entry point for ALL FRANK-initiated command execution.
        Classifies risk, checks resources, presents permission prompt or
        auto-executes, and logs every proposal to the audit trail.
        Must be called from the main thread.
        """
        import time as _time
        cmd_line = cmd_line.strip()
        if not cmd_line:
            return

        tier, label = self._frank_classify_risk(cmd_line)
        ts = _time.strftime("%H:%M:%S")

        # Resource check before any live execution (TIER 2 & 3)
        if tier >= 2:
            try:
                from core import get_governor
                gov = get_governor()
                safety = gov.is_safe_to_proceed()
                if not safety.get("safe", True):
                    self._write_frank(
                        f"\n[FRANK] ⚠ System too busy to execute safely.\n"
                        f"  Reason: {safety.get('reason', 'unknown')}\n"
                        f"  Try again when CPU/RAM usage drops.\n\n"
                    )
                    self._frank_exec_log.append({
                        "ts": ts, "tier": tier, "cmd": cmd_line,
                        "status": "DEFERRED — system overloaded"
                    })
                    return
            except Exception:
                pass   # governor unavailable — proceed anyway

        # ── TIER 0: absolute block ────────────────────────────────────────
        if tier == 0:
            self._write_frank(
                f"\n[FRANK] ⛔ BLOCKED\n"
                f"  Command : {cmd_line}\n"
                f"  Reason  : {label}\n"
                f"  This command is permanently forbidden and cannot be run.\n\n"
            )
            self._frank_exec_log.append({
                "ts": ts, "tier": 0, "cmd": cmd_line, "status": "BLOCKED"
            })
            return

        # ── TIER 1: destructive — store pending, require CONFIRM ──────────
        if tier == 1:
            self._frank_pending_cmd  = cmd_line
            self._frank_pending_tier = 1
            self._write_frank(
                f"\n[FRANK] 🔴 DESTRUCTIVE OPERATION\n"
                f"  Command : {cmd_line}\n"
                f"  Risk    : {label}\n"
                f"  ─────────────────────────────────────────\n"
                f"  Type  CONFIRM  to execute  |  n  to cancel\n\n"
            )
            return   # wait for user response in _handle_frank_input

        # ── TIER 2: modifying — store pending, require y/n ───────────────
        if tier == 2:
            self._frank_pending_cmd  = cmd_line
            self._frank_pending_tier = 2
            self._write_frank(
                f"\n[FRANK] 🟡 FRANK wants to run:\n"
                f"  > {cmd_line}\n"
                f"  Execute?  y  to approve  |  n  to cancel\n\n"
            )
            return   # wait for user response in _handle_frank_input

        # ── TIER 3: read-only — auto-execute ─────────────────────────────
        self._write_frank(f"\n[FRANK] 🟢 Running: {cmd_line}\n")
        self._frank_exec_log.append({
            "ts": ts, "tier": 3, "cmd": cmd_line, "status": "EXECUTED"
        })
        self._execute_command(cmd_line)

    def _frank_enter_chat(self):
        """Enter interactive FRANK chat mode. Lazy-loads model on first use."""
        if self._in_frank_mode:
            self._write_frank(
                "\n[FRANK] Already in chat mode. Type 'exit' to leave.\n\n"
            )
            return
        self._write_frank(
            "\n[FRANK] Loading... (first load: ~2-4 s, ~2.5 GB RAM)\n"
        )
        def _load():
            try:
                from agents.sauron import get_sauron
                get_sauron()  # triggers lazy model load
                self._root.after(0, self._frank_chat_ready)
            except Exception as e:
                self._root.after(
                    0, lambda: self._write_error(f"[FRANK] Load failed: {e}")
                )
        threading.Thread(target=_load, daemon=True).start()

    def _frank_help_guide(self):
        """Full FRANK chat guide — mirrors Monster Terminal help format. Purple output."""
        self._write_frank("""
╔══════════════════════════════════════════════════════════════════╗
║               [FRANK] AI CHAT — COMMAND GUIDE                   ║
╚══════════════════════════════════════════════════════════════════╝

HOW I OPERATE:
  Model:     Phi-3.5 Mini 3.8B (Ollama local, ~2.5 GB RAM)
  Manual:    !run <cmd>   You propose → guard checks tier → executes
  Automatic: I detect need → output ::EXEC::cmd → guard fires
  Quantum:   I execute ::QUANTUM:: ops directly (see section below)
  Approve:   y / yes      Approve MODIFY or Ring 2 quantum ops
             CONFIRM      Approve DESTRUCTIVE (TIER 1) commands
  Reject:    n / cancel   Block any pending command or quantum op

CONTEXT AWARENESS:
  On every message I receive a live system context block with:
  • Active quantum state (qubits, gates, top probabilities)
  • Saved states and circuits (names, newest first)
  • Session stats (uptime, task count, success/fail)
  • Storage usage and CPU/RAM percentages
  Ask me "what was I working on?" or "what states do I have?" and
  I will answer from context — no extra commands needed.

PERMISSION TIERS:
  🟢 TIER 3 — Read-only    Auto-executes immediately (no prompt)
  🟡 TIER 2 — Modify       Requires y/yes approval before running
  🔴 TIER 1 — Destructive  Requires typing CONFIRM before running
  ⛔ TIER 0 — Forbidden    Blocked permanently. Never runs.

NAVIGATION & FILES:                                         [🟢 auto]
  cd [DIR]        Change directory (~ home, .. parent)
  pwd             Print working directory
  ls [-la]        List files (-l long, -a all hidden)
  cat FILE        Display file contents
  head/tail FILE  Show first/last N lines (default 10)
  find PATH       Find files recursively
  grep PAT FILE   Search for pattern in file(s)
  wc FILE         Count lines, words, characters

FILE MODIFICATION:                                        [🟡 approve]
  touch FILE      Create empty file
  mkdir [-p] DIR  Create directory (-p for parent dirs)
  echo TEXT       Print / redirect output to file
  cp [-r] S D     Copy file or directory
  mv SRC DEST     Move or rename files

DESTRUCTIVE FILE OPS:                                      [🔴 CONFIRM]
  rm FILE         Remove a single file
  rm -r/-rf DIR   Remove recursively (DESTRUCTIVE)
  rmdir DIR       Remove empty directory

UTILITIES:                                                  [🟢 auto]
  history         Show command history
  date            Show current date and time
  whoami          Show current user
  clear           Clear terminal screen

GIT — READ:                                                 [🟢 auto]
  git status      Color-coded file states (✅📝❓)
  git log         Visual commit graph with colors
  git diff        Show unstaged changes
  git branch      List branches with current highlighted
  git remote      Show remotes with visual indicators

GIT — WRITE:                                              [🟡 approve]
  git add         Stage files for commit
  git commit      Create a commit
  git push/pull   Push to / pull from remote
  git fetch       Fetch from remote (no merge)
  git merge       Merge branch
  git checkout    Switch branch or restore file
  git stash       Stash / pop working changes
  git tag         Create or list tags

GIT — DANGEROUS:                                           [🔴 CONFIRM]
  git reset --hard   Reset branch to commit (destructive)
  git clean          Remove untracked files

PACKAGE MANAGEMENT:                                       [🟡 approve]
  pip install     Install a Python package
  pip list        List installed packages  [🟢 auto]
  pip show        Show package details     [🟢 auto]
  pip uninstall   Remove a package
  python FILE     Run a Python script

SSH / REMOTE:                                             [🟡 approve]
  ssh             Connect to remote host
  scp             Secure copy files
  ssh-keygen      Generate SSH key pair

QUANTUM COMPUTING:                                          [🟢 auto]
  quantum / q     Enter quantum sub-shell (REPL)
  qubit N         Initialize N qubits in |0> state
  h/x/y/z <q>    Hadamard / Pauli gates
  cx/cz <c> <t>  Two-qubit CNOT / controlled-Z gate
  mcx <c,..> <t> Multi-controlled X (up to 16 qubits)
  measure [shots] Measure all qubits + auto-launch Bloch sphere
  bloch [type]    3D Bloch sphere (Three.js, opens in browser)
  bloch2d [3d]    Matplotlib 2D/3D Bloch sphere
  circuit list    List saved circuits          [🟢 auto]
  circuit save    Save current circuit         [🟡 approve]
  circuit load    Load + replay a saved circuit [🟡 approve]
  circuit export  Export circuit to OpenQASM 2.0
  circuit delete  Delete saved circuit         [🔴 CONFIRM]
  bell / ghz [n]  Quick Bell / GHZ state presets
  qft [n]         Quantum Fourier Transform

FRANK QUANTUM CHAT EXECUTION (inside frank chat mode):
  FRANK now executes quantum operations directly from conversation.
  Just ask: "create a Bell state", "run QFT on 3 qubits", "measure"
  No manual commands needed — FRANK issues ::QUANTUM:: actions itself.

  ─── Ring 3: Auto-execute (no approval) ───────────────  [🟢 auto]
  init_qubits               FRANK initializes N-qubit register
  apply_gate (all gates)    H, X, Y, Z, CX, RX, RY, RZ, SWAP, etc.
  run_preset bell           Bell state (H + CNOT, 2 qubits)
  run_preset ghz [n]        GHZ state (n qubits)
  run_preset qft [n]        Quantum Fourier Transform (n qubits)
  get_state_info            FRANK reads current statevector
  list_circuits             FRANK lists saved circuits

  ─── Ring 2: Requires y/n approval ───────────────────  [🟡 approve]
  measure [shots]           Measure all qubits + auto-launch Bloch sphere
  show_bloch                Launch 3D Bloch sphere (no measurement)
  save_state <name>         Save current quantum state to disk
  save_circuit <name>       Save current circuit to library
  delete_circuit <name>     Delete a saved circuit
  synthesis_run <preset>    Run Gaussian/Tunneling/Harmonic/Lorentz
  synthesis_bloch           Launch synthesis Bloch animation
  qiskit_run <qasm>         Run OpenQASM circuit via Qiskit
  qutip_evolve ...          Run QuTiP Lindblad evolution

  When FRANK outputs a Ring 2 quantum action:
    y / yes   → executes the operation
    n / no    → cancels without executing

SYNTHESIS ENGINE:                                           [🟢 auto]
  synthesis run <preset>    Run physics simulation
  synthesis gaussian        Gaussian wave packet evolution
  synthesis tunneling       Quantum tunneling simulation
  synthesis harmonic        Harmonic oscillator
  synthesis lorentz <v>     Set Lorentz boost velocity
  synthesis compare/visualize/status
  synth                     Alias for synthesis

HARDWARE MONITOR:                                           [🟢 auto]
  hardware                  Full dashboard (CPU, RAM, disk, tier)
  hardware trend            Resource trend analysis
  hardware tiers            Tier information and limits
  hardware recommend        Auto-switch recommendation + headroom %
  hardware diagnose         Hardware diagnosis with tier limits
  hardware line             Compact status line

PROVIDERS & CLOUD COMPUTE:                                  [🟢 auto]
  providers                 List all quantum + classical providers
  providers scan            Refresh SDK availability scan
  providers info <id>       Detailed info for a provider
  providers install <id>    Show pip install command (read-only)
  providers quantum         List only quantum providers
  providers classical       List only classical providers
  providers suggest         Generate setup suggestions

INTELLIGENT ROUTER:                                         [🟢 auto]
  route --qubits N          Route workload to optimal provider
  route --type T --priority P  Route by type + priority
                            Priorities: cost | speed | accuracy
  route-options --qubits N  Show all compatible providers (ranked)
  route-test --provider ID  Test routing feasibility for provider  [🟡]
  route-history             Show last 20 routing decisions
  Router reports: primary provider, score, CPU%/RAM% safety,
  fallback chain, alternatives, routing time in ms.

REAL-TIME ADAPTATION ENGINE:                                [🟢 auto]
  adapt-status              Current adaptation mode + active patterns
  adapt-patterns            Learned patterns (condition → action → rate)
  adapt-performance         Provider rankings with latency/reliability
  adapt-insights            Analytics on workload + provider behavior
  adapt-recommend <type>    Recommended provider for a task type
  adapt-history             Chronological adaptation decisions log
  adapt-dashboard           Full visual dashboard (all metrics)

MEMORY & ARTIFACTS:
  ─── VIEW ─────────────────────────────────────────────  [🟢 auto]
  memory status             Detailed RAM + disk + Frankenstein usage
  memory view sessions      Current session info + last 10 task records
  memory view logs          Log files across all dirs (size + date)
  memory view states        Saved quantum states (numbered, newest first)
  memory view circuits      List saved circuits
  memory view config        Configuration files
  saves                     Show all saved quantum artifacts

  ─── CLEAR ───────────────────────────────────────────  [🟡 approve]
  memory clear cache        Clear gate + synthesis cache (reports bytes)
  memory clear logs [N]     Delete old logs, keep last N (default 10)
  memory clear pycache      Clear __pycache__ dirs in project
  memory export             Export full memory report to JSON

  ─── DESTRUCTIVE ──────────────────────────────────────  [🔴 CONFIRM]
  memory clear states               Delete ALL saved quantum states
  memory clear states <name>        Delete ONE state by name
  circuit delete <name>             Delete saved circuit

PERMISSIONS & SECURITY:
  ─── READ / AUDIT ────────────────────────────────────  [🟢 auto]
  permissions               Show current role + full permission summary
  permissions check <action> Check if specific action is allowed
  permissions providers     Show accessible providers for current role
  permissions audit [days]  Show audit trail (default: last 7 days)
  security                  Full threat dashboard (level, uptime, events)
  security log [N]          Show last N security events (default 20)
  security report           Threat statistics + severity breakdown
  security level            Current threat level indicator
  security test             Run security test suite

  ─── MODIFY ─────────────────────────────────────────  [🟡 approve]
  permissions set-role <r>  Change role: Admin / Operator / User
  permissions reset         Reset permissions to defaults
  security clear            Clear security event history
  automation enable/disable Enable or disable a workflow
  automation consent/revoke Grant or revoke workflow termination consent

  ─── DESTRUCTIVE ────────────────────────────────────  [🔴 CONFIRM]
  diagnose fix <n>          Apply system recommendation #N
  diagnose kill <name>      Kill a running process by name

  SECURITY BEST PRACTICES (built into guard system):
  ├─ Roles: Admin > Operator > User  (set with: permissions set-role)
  ├─ Every exec logged: timestamp, tier, status  →  !history
  ├─ TIER 0 forbidden list blocks all OS-critical operations
  ├─ TIER 1 requires typing CONFIRM explicitly (no accidents)
  ├─ Governor: CPU < 80% and RAM < 75% checked before every exec
  └─ permissions audit  →  full role-change and sensitive action log

SYSTEM DIAGNOSTICS & AUTOMATION:
  ─── READ ────────────────────────────────────────────  [🟢 auto]
  status          Frankenstein full system status
  diagnose        Full system diagnosis + ranked recommendations
  diagnose quick  Quick CPU% / RAM% snapshot
  setup           Run setup wizard
  scheduler       Scheduler status summary
  scheduler tasks List all scheduled tasks

  ─── MODIFY ─────────────────────────────────────────  [🟡 approve]
  automation start/stop     Start or stop all automation workflows
  automation run <name>     Run specific workflow by name
  automation status         Detailed per-workflow status
  scheduler pause <id>      Pause a scheduled task by ID
  scheduler resume <id>     Resume a paused task
  scheduler stop            Stop the task scheduler

[FRANK] AI:                                             [🟢 auto]
  frank status    Health check (never loads model)
  frank unload    Free Phi-3.5 model from RAM (~2.5 GB) [🟡 approve]
  frank reset     Clear conversation history          [🔴 CONFIRM]
  frank agents    List all discoverable agents
  Note: FRANK is context-aware — sees quantum state, saved items,
        CPU/RAM, and session stats automatically on every message.

IN-CHAT SHORTCUTS:
  !run <cmd>    Propose command for guarded execution
  !help         This guide
  !commands     Full 69-command tier reference (dense)
  !history      Session execution audit log
  !status       Quick FRANK health check
  exit / quit   Leave FRANK chat mode
  stop          Interrupt current AI response
  reset         Clear conversation history

PERMANENTLY FORBIDDEN (⛔ always blocked, no override):
  rm -rf /     rm -rf /*   format c:    del /s /q C:\\
  dd if=/dev/  :(){ :|:&   DROP DATABASE   DROP TABLE
  Anything touching: system32, boot, BIOS, kernel, MBR,
  registry, /etc/hosts, or core OS files
═══════════════════════════════════════════════════════════════════
""")

    def _frank_chat_ready(self):
        """Called on main thread once model has loaded. Activate chat mode."""
        self._in_frank_mode = True
        self._frank_last_active = time.time()
        self._update_prompt()
        if self._status_label:
            self._status_label.configure(
                text="  [FRANK]  ", text_color="#7c3aed"
            )
        self._frank_help_guide()
        self._write_frank("─" * 67 + "\n")
        self._write_frank("[FRANK] Ready. Type a message to begin...\n\n")
        self._frank_start_idle_watch()

    def _frank_ask_single(self, query: str):
        """Single-shot query using stream() — no history, no mode change."""
        self._write_frank("\n[FRANK] Loading model for query...\n")
        def _load_and_ask():
            try:
                from agents.sauron import get_sauron
                sauron = get_sauron()
                self._root.after(
                    0, lambda: self._frank_start_stream(
                        query, stream_func=sauron.stream
                    )
                )
            except Exception as e:
                self._root.after(
                    0, lambda: self._write_error(f"[FRANK] Load failed: {e}")
                )
        threading.Thread(target=_load_and_ask, daemon=True).start()

    def _handle_frank_input(self, text: str):
        """Route user input while in FRANK chat mode."""
        import time as _time
        stripped = text.strip()
        lower    = stripped.lower()

        # ── PRIORITY 0: pending quantum approval ─────────────────────────
        # If FRANK proposed a Ring 2 quantum operation via ::QUANTUM::,
        # consume this input as the approval before anything else.
        if self._frank_pending_quantum is not None:
            if lower in ('y', 'yes'):
                action, kwargs = self._frank_pending_quantum
                self._frank_pending_quantum = None
                self._frank_pending_tier = 0
                self._frank_quantum_exec_approved(action, kwargs)
            elif lower in ('n', 'no', 'cancel'):
                self._frank_pending_quantum = None
                self._frank_pending_tier = 0
                self._write_frank("[FRANK] Quantum operation cancelled.\n\n")
            else:
                self._write_frank(
                    "[FRANK] Quantum op pending — waiting for your decision:\n"
                    "  Type  y  to run  |  n  to cancel\n\n"
                )
            return

        # ── PRIORITY 1: pending approval queue ───────────────────────────
        # If FRANK proposed a command and is waiting for user approval,
        # consume this input as the answer before anything else.
        if self._frank_pending_cmd is not None:
            ts = _time.strftime("%H:%M:%S")
            if self._frank_pending_tier == 2 and lower in ('y', 'yes'):
                cmd = self._frank_pending_cmd
                self._frank_pending_cmd  = None
                self._frank_pending_tier = 0
                self._frank_exec_log.append({
                    "ts": ts, "tier": 2, "cmd": cmd, "status": "EXECUTED"
                })
                self._write_frank(f"[FRANK] ✓ Approved. Running: {cmd}\n")
                self._execute_command(cmd)
            elif self._frank_pending_tier == 1 and lower == 'confirm':
                cmd = self._frank_pending_cmd
                self._frank_pending_cmd  = None
                self._frank_pending_tier = 0
                self._frank_exec_log.append({
                    "ts": ts, "tier": 1, "cmd": cmd, "status": "EXECUTED"
                })
                self._write_frank(f"[FRANK] ✓ Confirmed. Running: {cmd}\n")
                self._execute_command(cmd)
            elif lower in ('n', 'no', 'cancel'):
                cmd = self._frank_pending_cmd
                self._frank_exec_log.append({
                    "ts": ts, "tier": self._frank_pending_tier,
                    "cmd": cmd, "status": "CANCELLED"
                })
                self._frank_pending_cmd  = None
                self._frank_pending_tier = 0
                self._write_frank("[FRANK] Cancelled.\n\n")
            else:
                # User typed something else — remind them what's needed
                if self._frank_pending_tier == 1:
                    self._write_frank(
                        "[FRANK] Waiting for your decision:\n"
                        "  Type  CONFIRM  to execute  |  n  to cancel\n\n"
                    )
                else:
                    self._write_frank(
                        "[FRANK] Waiting for your decision:\n"
                        "  Type  y  to approve  |  n  to cancel\n\n"
                    )
            return

        # ── PRIORITY 2: !cmd shortcut syntax ─────────────────────────────
        if stripped.startswith('!'):
            self._frank_handle_bang(stripped)
            return

        # Exit chat mode
        if lower in ('exit', 'quit', '\\q'):
            if self._frank_thinking:
                self._frank_stop_streaming()
            self._in_frank_mode = False
            self._update_prompt()
            self._write_frank("\n[FRANK] Chat mode closed.\n\n")
            if self._status_label:
                self._status_label.configure(
                    text="  ● ALIVE  ",
                    text_color=self._colors['electric_green']
                )
            return

        # Interrupt current stream
        if lower == 'stop':
            self._frank_stop_streaming()
            return

        # Reset conversation history
        if lower == 'reset':
            self._frank_reset_history()
            return

        # Guard: already thinking — allow stop, refuse new message
        if self._frank_thinking:
            self._write_frank(
                "\n[FRANK] Still thinking... type 'stop' to interrupt.\n\n"
            )
            return

        # Empty input
        if not stripped:
            return

        # Send to FRANK
        try:
            from agents.sauron import get_sauron
            sauron = get_sauron()
            self._frank_start_stream(stripped, stream_func=sauron.chat_stream)
        except Exception as e:
            self._write_error(f"[FRANK] {e}")

    def _frank_handle_bang(self, text: str):
        """
        Route !cmd shortcuts typed inside FRANK chat mode.
          !run <cmd>   → guarded execution
          !help        → full command reference
          !commands    → quick tier summary
          !history     → execution audit log
          !status      → FRANK health check
        """
        parts = text.split(None, 1)          # ['!run', 'git status']  or ['!help']
        cmd   = parts[0].lower()             # e.g. '!run'
        rest  = parts[1].strip() if len(parts) > 1 else ""

        if cmd == '!run':
            if not rest:
                self._write_frank(
                    "\n[FRANK] Usage: !run <terminal command>\n"
                    "  Example: !run git status\n"
                    "  Example: !run ls -la\n\n"
                )
            else:
                self._frank_guard_exec(rest)

        elif cmd == '!help':
            self._frank_help_guide()

        elif cmd == '!commands':
            self._frank_cmd_list_quick()

        elif cmd == '!history':
            self._frank_exec_history()

        elif cmd == '!status':
            self._frank_status()

        elif cmd == '!':
            self._write_frank(
                "\n[FRANK] In-chat shortcuts:\n"
                "  !run <cmd>   Run a terminal command (guarded)\n"
                "  !help        Full command reference with tier badges\n"
                "  !commands    Quick command list\n"
                "  !history     Execution audit log\n"
                "  !status      FRANK health check\n\n"
            )

        else:
            self._write_frank(
                f"\n[FRANK] Unknown shortcut '{cmd}'. "
                f"Type !help for available shortcuts.\n\n"
            )

    def _frank_cmd_list_quick(self):
        """Quick command summary grouped by tier — shorter than full reference."""
        self._write_frank(
            "\n[FRANK] Command Tiers — Quick View\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 READ-ONLY (auto-execute — no approval needed)\n"
            "   ls  pwd  cat  head  tail  wc  grep  find\n"
            "   git status  git log  git diff  git branch\n"
            "   status  hardware  security  diagnose  whoami  date\n"
            "   env  printenv  history  frank status  frank agents\n"
            "   providers  saves  memory status  memory view\n"
            "   adapt-*  route  route-options  route-history\n"
            "   synthesis status  circuit info  help\n"
            "\n"
            "🟡 MODIFYING (type y to approve)\n"
            "   cd  touch  mkdir  cp  mv  echo  rm <file>\n"
            "   git add  commit  push  pull  merge  checkout  clone\n"
            "   pip install/uninstall  npm  conda\n"
            "   python  node  nano  vim  notepad  code\n"
            "   ssh  scp  export  set  source  connect\n"
            "   quantum  synthesis <cmd>  circuit save/load\n"
            "   memory export  frank unload  setup  automation\n"
            "\n"
            "🔴 DESTRUCTIVE (type CONFIRM to execute)\n"
            "   rm -r  rmdir  git reset --hard  git clean\n"
            "   memory clear  circuit delete  frank reset\n"
            "\n"
            "⛔ BLOCKED (permanently forbidden — no override)\n"
            "   rm -rf /  format c:  del /s /q C:\\  dd if=/dev/\n"
            "   fork bombs  DROP DATABASE  DROP TABLE\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Type !help for the full 69-command detailed reference.\n\n"
        )

    def _frank_cmd_reference(self):
        """Full purple-formatted command reference. Called by !help."""
        ref = (
            "\n[FRANK] COMPLETE COMMAND REFERENCE\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "TIERS:  🟢 READ-ONLY (auto)  🟡 MODIFY (y/n)  "
            "🔴 DESTROY (CONFIRM)  ⛔ BLOCKED\n"
            "━━ NAVIGATION & FILE SYSTEM ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 ls [path]                List directory contents\n"
            "🟢 dir [path]               Windows alias for ls\n"
            "🟢 pwd                       Print working directory\n"
            "🟡 cd <path>                Change directory\n"
            "🟢 cat <file>               Read file contents\n"
            "🟢 type <file>              Windows alias for cat\n"
            "🟡 touch <file>             Create empty file\n"
            "🟡 mkdir <dir>              Create directory\n"
            "🟡 cp [-r] <src> <dest>     Copy file or directory\n"
            "🟡 mv <src> <dest>          Move or rename\n"
            "🟡 rm <file>                Delete single file  (no flags)\n"
            "🔴 rm -r <dir>              Recursive delete directory\n"
            "🔴 rmdir <dir>              Remove directory\n"
            "🟢 head [-n N] <file>       First N lines  (default 10)\n"
            "🟢 tail [-n N] <file>       Last N lines   (default 10)\n"
            "🟢 wc <file>                Count lines, words, characters\n"
            "🟢 grep [-i] <pat> <file>   Search pattern in file\n"
            "🟢 find <path> [-name P]    Find files matching pattern\n"
            "━━ SYSTEM INFO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 status                   Frankenstein full system status\n"
            "🟢 whoami                   Show current user\n"
            "🟢 date                     Current date and time\n"
            "🟢 history                  Command history log\n"
            "🟢 hardware                 Live CPU, RAM, disk stats\n"
            "🟢 security                 Security shield dashboard\n"
            "🟢 diagnose                 Full system diagnosis\n"
            "🟢 env                      List all environment variables\n"
            "🟢 printenv [KEY]           Print one environment variable\n"
            "━━ ENVIRONMENT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟡 export KEY=VALUE         Set environment variable\n"
            "🟡 set KEY VALUE            Set variable  (Windows style)\n"
            "🟡 unset KEY                Remove environment variable\n"
            "🟡 source <script>          Execute a shell script\n"
            "🟡 echo <text>              Print text  (or redirect to file)\n"
            "━━ GIT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 git status               Color-coded working tree status\n"
            "🟢 git log [--graph]        Visual commit history\n"
            "🟢 git diff                 Staged and unstaged changes\n"
            "🟢 git branch [-a]          List all branches\n"
            "🟢 git remote [-v]          Show remotes with indicators\n"
            "🟡 git add <file>           Stage files for commit\n"
            "🟡 git commit -m \"msg\"      Create commit\n"
            "🟡 git pull                 Pull from remote\n"
            "🟡 git push                 Push to remote\n"
            "🟡 git checkout <branch>    Switch branches\n"
            "🟡 git clone <url> [dir]    Clone repository\n"
            "🟡 git merge <branch>       Merge branch into current\n"
            "🔴 git reset --hard         Hard reset  (DESTROYS uncommitted work)\n"
            "🔴 git clean -f             Delete all untracked files\n"
            "━━ PACKAGE MANAGEMENT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 pip list                 List installed Python packages\n"
            "🟢 pip show <pkg>           Show package details\n"
            "🟡 pip install <pkg>        Install Python package\n"
            "🟡 pip uninstall <pkg>      Remove Python package\n"
            "🟡 npm install [pkg]        Install Node.js package\n"
            "🟡 conda install <pkg>      Install conda package\n"
            "━━ DEVELOPMENT TOOLS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟡 python <script>          Run Python script\n"
            "🟡 node <script>            Run Node.js script\n"
            "🟡 nano <file>              Open file in Nano editor\n"
            "🟡 vim / vi <file>          Open file in Vim\n"
            "🟡 notepad <file>           Open in Windows Notepad\n"
            "🟡 code [file/dir]          Open in VS Code\n"
            "━━ SSH / REMOTE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟡 ssh user@host            Connect to remote host\n"
            "🟡 scp <src> <dest>         Secure file copy\n"
            "🟡 ssh-keygen               Generate SSH key pair\n"
            "━━ PROVIDERS & CLOUD COMPUTE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 providers                List all 30 compute providers\n"
            "🟡 connect <provider>       Connect to a provider\n"
            "🟡 disconnect <provider>    Disconnect from provider\n"
            "🟡 credentials <provider>   Manage provider credentials\n"
            "━━ QUANTUM COMPUTING ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟡 quantum [cmd]            Enter quantum computing mode\n"
            "🟡 q                        Shortcut for quantum\n"
            "🟡 bloch                    Quick Bloch sphere visualization\n"
            "🟡 qubit [ops]              Quick qubit gate operations\n"
            "🟢 circuit info <name>      Show circuit details\n"
            "🟡 circuit list             Show saved circuits\n"
            "🟡 circuit save <name>      Save current circuit\n"
            "🟡 circuit load <name>      Load a saved circuit\n"
            "🟡 circuit export <name>    Export circuit to file\n"
            "🔴 circuit delete <name>    Delete saved circuit permanently\n"
            "━━ SYNTHESIS ENGINE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 synthesis status         Synthesis engine status\n"
            "🟡 synthesis compute <expr> Run computation\n"
            "🟡 synthesis quantum <expr> Quantum simulation\n"
            "🟡 synthesis physics <expr> Physics calculation\n"
            "🟡 synthesis math <expr>    Mathematical computation\n"
            "🟡 synthesis diff <expr>    Differentiate expression\n"
            "🟡 synthesis integrate <e>  Integrate expression\n"
            "🟡 synthesis solve <expr>   Solve equation\n"
            "🟡 synthesis lorentz <p>    Lorentz transformation\n"
            "🟡 synthesis schrodinger    Schrodinger equation solver\n"
            "🟡 synth                    Alias for synthesis\n"
            "━━ INTELLIGENT ROUTING ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 route [query]            Route request to best backend\n"
            "🟢 route-options            Show available routing options\n"
            "🟡 route-test               Test routing decision engine\n"
            "🟢 route-history            Show past routing decisions\n"
            "━━ REAL-TIME ADAPTATION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 adapt-status             Adaptation engine status\n"
            "🟢 adapt-patterns           Learned usage patterns\n"
            "🟢 adapt-performance        Performance metrics dashboard\n"
            "🟢 adapt-insights           AI-driven system insights\n"
            "🟢 adapt-recommend          Current recommendations\n"
            "🟢 adapt-history            Adaptation event log\n"
            "🟢 adapt-dashboard          Full adaptation overview\n"
            "━━ MEMORY & ARTIFACTS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 memory status            Memory system status\n"
            "🟢 memory view [key]        View stored memory entry\n"
            "🟡 memory export            Export memory to file\n"
            "🔴 memory clear [key]       Clear memory  (permanent data loss)\n"
            "🟢 saves                    Artifact save overview\n"
            "━━ SYSTEM & AUTOMATION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 permissions              Show current permission settings\n"
            "🟡 setup [component]        Setup or configure a component\n"
            "🟡 automation [cmd]         Automation engine controls\n"
            "🟡 scheduler [cmd]          Task scheduler management\n"
            "━━ [FRANK] AI ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 frank status             FRANK AI health check\n"
            "🟡 frank chat               Enter interactive FRANK chat mode\n"
            "🟡 frank ask <text>         Single-shot AI query  (no history)\n"
            "🟢 frank agents             List all discoverable agents\n"
            "🔴 frank reset              Clear conversation history permanently\n"
            "🟡 frank unload             Unload model to free ~4.5 GB RAM\n"
            "🟢 frank version            FRANK version info\n"
            "🟢 frank quote              Random Frankenstein quote\n"
            "━━ IN-CHAT SHORTCUTS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  !run <command>    Propose terminal command for guarded execution\n"
            "  !help             Show this full command reference\n"
            "  !commands         Quick command list grouped by tier\n"
            "  !history          FRANK execution audit log (this session)\n"
            "  !status           Quick FRANK health check\n"
            "  exit / quit       Leave FRANK chat mode\n"
            "  stop              Interrupt current streaming response\n"
            "  reset             Clear conversation history\n"
            "  y / yes           Approve a pending TIER 2 (MODIFY) command\n"
            "  CONFIRM           Approve a pending TIER 1 (DESTROY) command\n"
            "  n / no / cancel   Cancel any pending command\n"
            "━━ PERMANENTLY FORBIDDEN ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⛔ rm -rf /          Wipe root filesystem\n"
            "⛔ rm -rf /*         Wipe root filesystem (variant)\n"
            "⛔ format c:         Format C drive\n"
            "⛔ del /s /q C:\\     Recursive delete C drive\n"
            "⛔ dd if=/dev/zero   Overwrite disk with zeros\n"
            "⛔ :(){ :|:& };:     Fork bomb  (system crash)\n"
            "⛔ DROP DATABASE     Destroy entire database\n"
            "⛔ DROP TABLE        Destroy database table\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        self._write_frank(ref)

    def _frank_exec_history(self):
        """Display the session audit log of all FRANK command proposals."""
        log = self._frank_exec_log
        if not log:
            self._write_frank(
                "\n[FRANK] Execution Audit Log\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "  No commands proposed yet this session.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            )
            return

        _TIER_ICONS = {0: '⛔', 1: '🔴', 2: '🟡', 3: '🟢'}
        executed  = sum(1 for e in log if e['status'] == 'EXECUTED')
        blocked   = sum(1 for e in log if e['status'] == 'BLOCKED')
        cancelled = sum(1 for e in log if e['status'] == 'CANCELLED')
        deferred  = sum(1 for e in log if 'DEFERRED' in e['status'])

        lines = [
            "\n[FRANK] Execution Audit Log\n",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
            f"  {'#':<3}  {'Time':<10}  {'Tier':<4}  {'Status':<12}  Command\n",
            f"  {'─'*3}  {'─'*8}  {'─'*4}  {'─'*10}  {'─'*30}\n",
        ]
        for i, entry in enumerate(log, 1):
            icon   = _TIER_ICONS.get(entry['tier'], '?')
            cmd    = entry['cmd'][:45] + ('…' if len(entry['cmd']) > 45 else '')
            status = entry['status'][:10]
            lines.append(
                f"  {i:<3}  {entry['ts']:<10}  {icon:<4}  {status:<12}  {cmd}\n"
            )
        lines += [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
            f"  Total: {len(log)}  |  ✓ {executed} executed  |  "
            f"⛔ {blocked} blocked  |  ✗ {cancelled} cancelled",
        ]
        if deferred:
            lines.append(f"  |  ⏸ {deferred} deferred")
        lines.append("\n\n")
        self._write_frank("".join(lines))

    def _frank_start_stream(self, message: str, stream_func):
        """Kick off a background inference stream. Must be called from main thread."""
        self._frank_stop_event  = threading.Event()
        self._frank_thinking    = True
        self._frank_spinner_idx = 0
        self._frank_last_active = time.time()
        # Print response header
        self._write_frank("\n[FRANK]  ")
        # Start spinner in header status bar
        self._frank_spin()
        # Launch background worker
        self._frank_thread = threading.Thread(
            target=self._frank_stream_worker,
            args=(message, stream_func),
            daemon=True
        )
        self._frank_thread.start()

    def _frank_stream_worker(self, message: str, stream_func):
        """Background thread: pull tokens and schedule main-thread GUI writes."""
        stop_event = self._frank_stop_event
        try:
            for token in stream_func(message):
                if stop_event and stop_event.is_set():
                    break
                # Capture token in lambda default to avoid loop-closure bug
                self._root.after(0, lambda t=token: self._on_frank_token(t))
        except Exception as e:
            self._root.after(
                0, lambda: self._write_frank(f"\n[FRANK] Stream error: {e}\n")
            )
        finally:
            self._root.after(0, self._on_frank_stream_done)

    def _on_frank_token(self, token: str):
        """
        Main thread: handle a single streamed token.
        Accumulates into _frank_exec_buffer watching for ::EXEC:: and ::QUANTUM:: markers.
        ::QUANTUM::action|param=value  → dispatched to _frank_quantum_dispatch()
        ::EXEC::command                → dispatched to _frank_guard_exec()
        All other tokens display immediately.
        """
        _MARKER_QUANTUM = '::QUANTUM::'
        _MARKER_EXEC    = '::EXEC::'
        self._frank_exec_buffer += token

        # ── Check for ::QUANTUM:: marker ────────────────────────────────────
        if _MARKER_QUANTUM in self._frank_exec_buffer:
            pre, _, rest = self._frank_exec_buffer.partition(_MARKER_QUANTUM)
            if rest:
                line = rest.split('\n')[0].strip()
                if line:
                    if pre:
                        self._write_frank(pre)
                    remainder = rest[len(rest.split('\n')[0]):]
                    self._frank_exec_buffer = remainder
                    self._root.after(0, lambda l=line: self._frank_quantum_dispatch(l))
                    return
            # Marker present but action not complete yet — keep buffering
            return

        # ── Check for ::EXEC:: marker ────────────────────────────────────────
        if _MARKER_EXEC in self._frank_exec_buffer:
            pre, _, rest = self._frank_exec_buffer.partition(_MARKER_EXEC)
            if rest:
                cmd = rest.split('\n')[0].strip()
                if cmd:
                    if pre:
                        self._write_frank(pre)
                    remainder = rest[len(rest.split('\n')[0]):]
                    self._frank_exec_buffer = remainder
                    self._root.after(0, lambda c=cmd: self._frank_guard_exec(c))
                    return
            # Marker present but command not complete yet — keep buffering
            return

        # No marker — display immediately and clear buffer
        self._write_frank(token)
        self._frank_exec_buffer = ""

    def _on_frank_stream_done(self):
        """Main thread: called when the stream thread finishes or is interrupted."""
        # Flush any remaining buffered text that didn't trigger ::EXEC::
        if self._frank_exec_buffer:
            self._write_frank(self._frank_exec_buffer)
            self._frank_exec_buffer = ""
        self._frank_thinking = False
        self._write_frank("\n\n")
        self._frank_last_active = time.time()
        if self._status_label:
            if self._in_frank_mode:
                self._status_label.configure(
                    text="  [FRANK]  ", text_color="#7c3aed"
                )
            else:
                self._status_label.configure(
                    text="  ● ALIVE  ",
                    text_color=self._colors['electric_green']
                )
        self._frank_start_idle_watch()

    # ── ::QUANTUM:: dispatch ─────────────────────────────────────────────────

    # Ring 3 — execute immediately, no approval needed
    _QUANTUM_RING3 = frozenset({
        "init_qubits", "apply_gate", "run_circuit", "run_preset",
        "get_state_info", "list_circuits", "synthesis_status", "true_engine_status",
    })

    # Ring 2 — requires y/n approval (bypasses blocking input() in QuantumTool)
    _QUANTUM_RING2 = frozenset({
        "measure", "save_state", "save_circuit", "delete_circuit",
        "load_circuit_and_run", "qiskit_run", "qutip_evolve", "show_bloch",
        "synthesis_run", "synthesis_bloch", "synthesis_gaussian",
        "synthesis_tunneling", "synthesis_harmonic", "synthesis_lorentz",
    })

    def _frank_quantum_dispatch(self, action_line: str):
        """
        Parse a ::QUANTUM::action|param=value|... string and dispatch to QuantumTool.
        Ring 3 actions execute immediately. Ring 2 actions enter y/n approval flow.
        Runs on main thread.
        """
        try:
            parts = action_line.split('|')
            action = parts[0].strip()
            kwargs = {}
            for part in parts[1:]:
                if '=' in part:
                    key, val = part.split('=', 1)
                    key = key.strip()
                    val = val.strip()
                    # Type coercion
                    if val.isdigit():
                        val = int(val)
                    elif val.replace('.', '', 1).isdigit():
                        val = float(val)
                    elif val.lower() in ('true', 'false'):
                        val = val.lower() == 'true'
                    kwargs[key] = val

            # Lazy-load the QuantumTool singleton
            if self._quantum_tool is None:
                from agents.sauron.tools.quantum_tool import QuantumTool
                self._quantum_tool = QuantumTool()

            if action in self._QUANTUM_RING3:
                # Safe — execute immediately via QuantumTool.execute()
                self._write_frank(
                    f"\n[FRANK] ⚛  Quantum: {action}"
                    f"({', '.join(f'{k}={v}' for k, v in kwargs.items())})\n"
                )
                result = self._quantum_tool.execute(action=action, **kwargs)
                self._frank_display_quantum_result(action, result)

            elif action in self._QUANTUM_RING2:
                # Sensitive — show y/n approval prompt (non-blocking, avoids input() deadlock)
                desc_map = {
                    "measure":              f"Run measurement ({kwargs.get('shots', 1024)} shots) + launch Bloch sphere",
                    "show_bloch":           "Launch Bloch sphere visualisation in browser",
                    "save_state":           f"Save quantum state as '{kwargs.get('name', '?')}'",
                    "save_circuit":         f"Save circuit as '{kwargs.get('name', '?')}'",
                    "delete_circuit":       f"Delete circuit '{kwargs.get('name', '?')}'",
                    "load_circuit_and_run": f"Load + run circuit '{kwargs.get('name', '?')}'",
                    "qiskit_run":           f"Run QASM via Qiskit ({kwargs.get('shots', 1024)} shots)",
                    "qutip_evolve":         "Run QuTiP time evolution",
                    "synthesis_run":        f"Run synthesis: {kwargs.get('preset', 'gaussian')}",
                    "synthesis_bloch":      f"Launch synthesis Bloch: {kwargs.get('sim_type', 'rabi')}",
                    "synthesis_gaussian":   f"Gaussian wave packet (sigma={kwargs.get('sigma', 1.0)})",
                    "synthesis_tunneling":  f"Quantum tunneling (barrier={kwargs.get('barrier', 1.0)})",
                    "synthesis_harmonic":   f"Harmonic oscillator (omega={kwargs.get('omega', 1.0)})",
                    "synthesis_lorentz":    f"Lorentz boost (v={kwargs.get('velocity', 0.5)}c)",
                }
                desc = desc_map.get(action, f"Execute quantum.{action}")
                self._frank_pending_quantum = (action, kwargs)
                self._frank_pending_tier = 2
                self._write_frank(
                    f"\n[FRANK] 🟡 Quantum operation requested:\n"
                    f"  ⚛  {desc}\n"
                    f"  Approve?  y  to run  |  n  to cancel\n\n"
                )
            else:
                self._write_frank(
                    f"\n[FRANK] ❌ Unknown quantum action: '{action}'\n"
                    f"  Valid Ring 3: {', '.join(sorted(self._QUANTUM_RING3))}\n"
                    f"  Valid Ring 2: {', '.join(sorted(self._QUANTUM_RING2))}\n\n"
                )

        except Exception as e:
            self._write_frank(f"\n[FRANK] ❌ Quantum dispatch error: {e}\n\n")

    def _frank_quantum_exec_approved(self, action: str, kwargs: dict):
        """
        Execute a Ring 2 quantum action that has already been approved via y/n prompt.
        Calls the QuantumTool private method directly to bypass the blocking
        request_permission() / input() call inside QuantumTool.execute().
        """
        try:
            if self._quantum_tool is None:
                from agents.sauron.tools.quantum_tool import QuantumTool
                self._quantum_tool = QuantumTool()

            # Map each Ring 2 action to its private implementation method
            private_dispatch = {
                "measure":              self._quantum_tool._measure,
                "show_bloch":           self._quantum_tool._show_bloch,
                "save_state":           self._quantum_tool._save_state,
                "save_circuit":         self._quantum_tool._save_circuit,
                "delete_circuit":       self._quantum_tool._delete_circuit,
                "load_circuit_and_run": self._quantum_tool._load_circuit_and_run,
                "qiskit_run":           self._quantum_tool._qiskit_run,
                "qutip_evolve":         self._quantum_tool._qutip_evolve,
                "synthesis_run":        self._quantum_tool._synthesis_run,
                "synthesis_bloch":      self._quantum_tool._synthesis_bloch,
                "synthesis_gaussian":   self._quantum_tool._synthesis_gaussian,
                "synthesis_tunneling":  self._quantum_tool._synthesis_tunneling,
                "synthesis_harmonic":   self._quantum_tool._synthesis_harmonic,
                "synthesis_lorentz":    self._quantum_tool._synthesis_lorentz,
            }
            if action not in private_dispatch:
                self._write_frank(f"[FRANK] ❌ No private dispatch for: {action}\n\n")
                return

            self._write_frank(
                f"[FRANK] ✓ Approved. Running quantum.{action}"
                f"({', '.join(f'{k}={v}' for k, v in kwargs.items())})\n"
            )
            result = private_dispatch[action](**kwargs)
            self._frank_display_quantum_result(action, result)

        except Exception as e:
            self._write_frank(f"[FRANK] ❌ Quantum execution error: {e}\n\n")

    def _frank_display_quantum_result(self, action: str, result) -> None:
        """Display a ToolResult from a quantum operation in frank-chat output."""
        if result.success:
            self._write_frank(f"[FRANK] ✅ {result.summary or 'Done'}\n")
            data = result.data or {}
            if 'counts' in data:
                total = sum(data['counts'].values())
                top = sorted(data['counts'].items(), key=lambda kv: -kv[1])[:6]
                self._write_frank("  Measurement results:\n")
                for state, count in top:
                    prob = count / total * 100
                    self._write_frank(f"    |{state}⟩  {count:>5}  ({prob:.1f}%)\n")
            elif 'top_states' in data:
                self._write_frank("  State probabilities:\n")
                for s in data['top_states'][:6]:
                    self._write_frank(f"    |{s['state']}⟩  {s['probability']:.4f}\n")
            elif 'bloch_launched' in data or action in ('show_bloch', 'synthesis_bloch'):
                self._write_frank("  🔮 Bloch sphere launched in browser.\n")
            elif 'n_qubits' in data:
                self._write_frank(
                    f"  Initialized {data['n_qubits']} qubits  |  "
                    f"Engine: {data.get('engine', 'SynthesisEngine')}\n"
                )
            elif data:
                # Generic: show up to 4 key=value pairs
                for k, v in list(data.items())[:4]:
                    self._write_frank(f"  {k}: {v}\n")
        else:
            self._write_frank(f"[FRANK] ❌ {result.error}\n")
        self._write_frank("\n")

    def _frank_stop_streaming(self):
        """Signal the background stream thread to stop immediately."""
        if self._frank_stop_event:
            self._frank_stop_event.set()
        self._frank_thinking = False
        self._write_frank("\n[FRANK] Interrupted.\n\n")
        if self._status_label:
            label = "  [FRANK]  " if self._in_frank_mode else "  ● ALIVE  "
            color = "#7c3aed" if self._in_frank_mode else self._colors['electric_green']
            self._status_label.configure(text=label, text_color=color)

    _FRANK_SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def _frank_spin(self):
        """Cycle spinner chars in the header status bar while FRANK is thinking."""
        if not self._frank_thinking or not self._root:
            return
        if self._status_label:
            frame = self._FRANK_SPINNER[
                self._frank_spinner_idx % len(self._FRANK_SPINNER)
            ]
            self._frank_spinner_idx += 1
            self._status_label.configure(
                text=f"  {frame} [FRANK]  ", text_color="#7c3aed"
            )
        self._root.after(150, self._frank_spin)

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

    # ==================== REAL-TIME ADAPTATION ====================

    def _ensure_adaptation_commands(self):
        """Lazy-load adaptation commands on first use"""
        if self._adaptation_commands is None:
            try:
                from agents.adaptation import get_adaptation_commands
                self._adaptation_commands = get_adaptation_commands()
            except ImportError as e:
                self._write_error(f"⚠️ Adaptation module not available: {e}")
                return None
        return self._adaptation_commands

    def _cmd_adapt_status(self, args: List[str]):
        """Display current adaptation status"""
        commands = self._ensure_adaptation_commands()
        if commands:
            try:
                output = commands.cmd_adapt_status(args)
                self._write_output(output)
            except Exception as e:
                self._write_error(f"Error getting adaptation status: {e}")

    def _cmd_adapt_patterns(self, args: List[str]):
        """Display learned adaptation patterns"""
        commands = self._ensure_adaptation_commands()
        if commands:
            try:
                output = commands.cmd_adapt_patterns(args)
                self._write_output(output)
            except Exception as e:
                self._write_error(f"Error getting patterns: {e}")

    def _cmd_adapt_performance(self, args: List[str]):
        """Display performance metrics and rankings"""
        commands = self._ensure_adaptation_commands()
        if commands:
            try:
                output = commands.cmd_adapt_performance(args)
                self._write_output(output)
            except Exception as e:
                self._write_error(f"Error getting performance metrics: {e}")

    def _cmd_adapt_insights(self, args: List[str]):
        """Display adaptation insights and analytics"""
        commands = self._ensure_adaptation_commands()
        if commands:
            try:
                output = commands.cmd_adapt_insights(args)
                self._write_output(output)
            except Exception as e:
                self._write_error(f"Error getting insights: {e}")

    def _cmd_adapt_recommend(self, args: List[str]):
        """Get provider recommendation for a task type"""
        commands = self._ensure_adaptation_commands()
        if commands:
            try:
                output = commands.cmd_adapt_recommend(args)
                self._write_output(output)
            except Exception as e:
                self._write_error(f"Error getting recommendation: {e}")

    def _cmd_adapt_history(self, args: List[str]):
        """Display adaptation history"""
        commands = self._ensure_adaptation_commands()
        if commands:
            try:
                output = commands.cmd_adapt_history(args)
                self._write_output(output)
            except Exception as e:
                self._write_error(f"Error getting history: {e}")

    def _cmd_adapt_dashboard(self, args: List[str]):
        """Display full adaptation dashboard"""
        commands = self._ensure_adaptation_commands()
        if commands:
            try:
                from agents.adaptation import get_adaptation_engine
                from agents.adaptation.adaptation_display import AdaptationDisplay

                engine = get_adaptation_engine(initialize=True)
                engine._initialize_components()

                dashboard = AdaptationDisplay.render_dashboard(engine)
                self._write_output(dashboard)
            except Exception as e:
                self._write_error(f"Error rendering dashboard: {e}")

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

    # ==================== ARTIFACT OVERVIEW ====================

    def _cmd_saves_overview(self, args: List[str]):
        """Show all saved quantum artifacts — states, circuits, and computation logs."""
        self._write_output("\n📦 Saved Artifacts\n")
        self._write_output("═" * 55 + "\n\n")

        # --- Quantum States ---
        self._write_output("🔬 Quantum States  (recall <name> in quantum mode):\n")
        self._write_output("─" * 45 + "\n")
        try:
            from synthesis.core.true_engine import get_true_engine
            states = get_true_engine().list_states()
            if states:
                for s in states:
                    if "error" in s:
                        self._write_output(f"  {s['name']:24s}  ⚠️  corrupt\n")
                    else:
                        self._write_output(
                            f"  {s['name']:24s}  {s['n_qubits']:2d} qubits"
                            f"  {s['size_kb']:6.1f} KB"
                            f"  {s['modified'][:10]}\n"
                        )
            else:
                self._write_output("  (none saved yet — use 'save <name>' in quantum mode)\n")
        except Exception as e:
            self._write_output(f"  (unavailable: {e})\n")

        self._write_output("\n")

        # --- Circuit Library ---
        self._write_output("⚡ Circuit Library  (circuit load/export in quantum mode):\n")
        self._write_output("─" * 45 + "\n")
        try:
            from synthesis.circuit_library import get_circuit_library
            circuits = get_circuit_library().list_circuits()
            if circuits:
                for c in circuits:
                    if "error" in c:
                        self._write_output(f"  {c['name']:24s}  ⚠️  corrupt\n")
                    else:
                        self._write_output(
                            f"  {c['name']:24s}  {c['n_qubits']:2d} qubits"
                            f"  {c['gates']:3d} gates  v{c['version']}"
                            f"  {c.get('modified','')[:10]}\n"
                        )
            else:
                self._write_output("  (none saved yet)\n")
        except Exception as e:
            self._write_output(f"  (unavailable: {e})\n")

        self._write_output("\n")

        # --- Computation Logs ---
        self._write_output("📋 Computation Logs  (memory view logs — coming in Session 3):\n")
        self._write_output("─" * 45 + "\n")
        try:
            from synthesis.computation_log import ComputationLogger
            logs = ComputationLogger.list_session_logs()
            if logs:
                for log in logs[:5]:
                    self._write_output(
                        f"  {log['filename']:38s}  {log['events']:4d} events"
                        f"  {log['size_kb']:6.1f} KB\n"
                    )
                if len(logs) > 5:
                    self._write_output(f"  ... and {len(logs) - 5} older sessions\n")
            else:
                self._write_output("  (no sessions logged yet)\n")
        except Exception as e:
            self._write_output(f"  (unavailable: {e})\n")

        self._write_output("\n")

    # ==================== MEMORY MANAGEMENT ====================

    def _cmd_memory(self, args: List[str]):
        """Memory management commands — view, edit, clear storage."""
        if not args:
            self._memory_overview()
            return

        subcmd = args[0].lower()
        subargs = args[1:] if len(args) > 1 else []

        if subcmd == "status":
            self._memory_status_detailed()
        elif subcmd == "view":
            self._memory_view(subargs)
        elif subcmd == "clear":
            self._memory_clear(subargs)
        elif subcmd == "export":
            self._memory_export()
        elif subcmd == "help":
            self._memory_help()
        else:
            self._write_error(f"Unknown memory command: {subcmd}\n")
            self._write_output("  Usage: memory [status|view|clear|export|help]\n")

    def _memory_overview(self):
        """Show memory system overview."""
        from pathlib import Path
        import json

        base = Path.home() / ".frankenstein"
        synth = base / "synthesis_data"

        # Calculate sizes for each area
        areas = {
            "Session & History": base / "history",
            "Adaptation Data": base / "data",
            "Security Logs": base / "logs",
            "Quantum States": synth / "states",
            "Simulation Results": synth / "results",
            "Circuit Library": synth / "circuits",
            "Gate Cache": synth / "cache",
            "Computation Logs": synth / "logs",
        }

        self._write_output("\n")
        self._write_output("╔══════════════════════════════════════════════════════════╗\n", color="cyan")
        self._write_output("║          FRANKENSTEIN MEMORY SYSTEM OVERVIEW            ║\n", color="cyan")
        self._write_output("╚══════════════════════════════════════════════════════════╝\n", color="cyan")
        self._write_output("\n")
        self._write_output(f"  Base Path: {base}\n")
        self._write_output(f"  Storage Budget: 20 GB (synthesis) + 10 GB (system)\n")
        self._write_output("\n")

        total_bytes = 0
        for area_name, area_path in areas.items():
            size = 0
            file_count = 0
            if area_path.exists():
                for f in area_path.rglob("*"):
                    if f.is_file():
                        size += f.stat().st_size
                        file_count += 1
            total_bytes += size

            size_str = self._format_size(size)
            self._write_output(f"  {area_name:<25} {size_str:>10}  ({file_count} files)\n")

        self._write_output(f"  {'─' * 50}\n")
        self._write_output(f"  {'TOTAL':<25} {self._format_size(total_bytes):>10}\n")
        self._write_output(f"  {'Budget Used':<25} {total_bytes / (30 * 1024**3) * 100:.2f}%\n")
        self._write_output("\n")

        # NAMED ITEMS — show state and circuit names
        states_dir = synth / "states"
        circuits_dir = synth / "circuits"
        state_names = []
        circuit_names = []
        if states_dir.exists():
            state_names = [
                f.stem for f in sorted(
                    states_dir.glob("*.npz"),
                    key=lambda f: f.stat().st_mtime,
                    reverse=True,
                )
            ]
        if circuits_dir.exists():
            circuit_names = [
                f.stem for f in sorted(
                    circuits_dir.glob("*.json"),
                    key=lambda f: f.stat().st_mtime,
                    reverse=True,
                )
            ]
        if state_names or circuit_names:
            self._write_output("  NAMED ITEMS:\n", color="cyan")
            if state_names:
                preview = ", ".join(state_names[:8])
                extra = f" (+{len(state_names) - 8} more)" if len(state_names) > 8 else ""
                self._write_output(f"    Quantum States ({len(state_names)}): {preview}{extra}\n")
            if circuit_names:
                preview = ", ".join(circuit_names[:8])
                extra = f" (+{len(circuit_names) - 8} more)" if len(circuit_names) > 8 else ""
                self._write_output(f"    Circuits       ({len(circuit_names)}): {preview}{extra}\n")
            self._write_output("\n")

        self._write_output("  Commands: memory status | memory view | memory clear | memory export\n")
        self._write_output("\n")

    def _memory_status_detailed(self):
        """Detailed memory status with system RAM info."""
        import psutil

        vm = psutil.virtual_memory()
        self._write_output("\n")
        self._write_output("  SYSTEM RAM:\n", color="cyan")
        self._write_output(f"    Total:     {vm.total / (1024**3):.1f} GB\n")
        self._write_output(f"    Used:      {vm.used / (1024**3):.1f} GB ({vm.percent}%)\n")
        self._write_output(f"    Available: {vm.available / (1024**3):.1f} GB\n")
        self._write_output(f"    Safety Limit: 75% ({vm.total * 0.75 / (1024**3):.1f} GB)\n")
        self._write_output("\n")

        # Show disk usage
        import shutil
        disk = shutil.disk_usage("C:\\")
        self._write_output("  DISK STORAGE:\n", color="cyan")
        self._write_output(f"    Total:     {disk.total / (1024**3):.1f} GB\n")
        self._write_output(f"    Used:      {disk.used / (1024**3):.1f} GB\n")
        self._write_output(f"    Free:      {disk.free / (1024**3):.1f} GB\n")
        self._write_output("\n")

        # Show Frankenstein-specific storage
        self._memory_overview()

    def _memory_view(self, args: List[str]):
        """View contents of specific storage areas."""
        if not args:
            self._write_output("\n  Usage: memory view [sessions|logs|states|circuits|config]\n\n")
            return

        area = args[0].lower()
        from pathlib import Path
        import json
        base = Path.home() / ".frankenstein"

        if area == "sessions":
            # Show session history — with file paths, sizes, and last 10 tasks
            session_file = base / "session.json"
            if session_file.exists():
                data = json.loads(session_file.read_text())
                stat = session_file.stat()
                self._write_output("\n  CURRENT SESSION:\n", color="cyan")
                self._write_output(f"    File: {session_file}  ({self._format_size(stat.st_size)})\n")
                for k, v in data.items():
                    self._write_output(f"    {k}: {v}\n")

            history_file = base / "history" / "tasks.json"
            if history_file.exists():
                tasks = json.loads(history_file.read_text())
                stat = history_file.stat()
                self._write_output(
                    f"\n  TASK HISTORY: {len(tasks)} records  [{self._format_size(stat.st_size)}]\n",
                    color="cyan",
                )
                self._write_output(f"    File: {history_file}\n")
                for t in tasks[-10:]:  # Show last 10
                    status = "✅" if t.get("success") else "❌"
                    self._write_output(
                        f"    {status} {t.get('task_type', '?')}: {t.get('input_summary', '')[:50]}\n"
                    )
            self._write_output("\n")

        elif area == "logs":
            # Show log files from all log directories — filenames, sizes, dates
            from datetime import datetime
            log_dirs = [
                base / "logs",
                base / "synthesis_data" / "logs",
            ]
            found_any = False
            for log_dir in log_dirs:
                if not log_dir.exists():
                    continue
                files = sorted(
                    [f for f in log_dir.iterdir() if f.is_file()],
                    key=lambda f: f.stat().st_mtime,
                    reverse=True,
                )
                if not files:
                    continue
                found_any = True
                self._write_output(
                    f"\n  {log_dir.name.upper()} ({log_dir})  — {len(files)} files\n",
                    color="cyan",
                )
                for f in files[:15]:
                    stat = f.stat()
                    mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                    self._write_output(
                        f"    {f.name:<40} {self._format_size(stat.st_size):>8}   {mtime}\n"
                    )
                if len(files) > 15:
                    self._write_output(f"    ... (+{len(files) - 15} older files)\n")
            if not found_any:
                self._write_output("\n  No log files found.\n")
            self._write_output("\n")

        elif area == "states":
            # Show saved quantum states — sorted by mtime, numbered, with date
            from datetime import datetime
            states_dir = base / "synthesis_data" / "states"
            if states_dir.exists():
                files = sorted(
                    states_dir.glob("*.npz"),
                    key=lambda f: f.stat().st_mtime,
                    reverse=True,
                )
                self._write_output(f"\n  SAVED QUANTUM STATES: {len(files)}\n", color="cyan")
                for i, f in enumerate(files, 1):
                    stat = f.stat()
                    mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                    self._write_output(
                        f"    {i:>2}. {f.stem:<30} {self._format_size(stat.st_size):>8}   {mtime}\n"
                    )
                if files:
                    self._write_output("  Hint: memory clear states <name>  to delete one\n")
            else:
                self._write_output("\n  No saved quantum states.\n")
            self._write_output("\n")

        elif area == "circuits":
            # Alias for circuit list
            self._cmd_circuit(["list"])

        elif area == "config":
            # Show config files
            config_dir = base / "config"
            if config_dir.exists():
                self._write_output(f"\n  CONFIGURATION FILES:\n", color="cyan")
                for f in config_dir.glob("*"):
                    if f.is_file():
                        self._write_output(f"    {f.name}: {self._format_size(f.stat().st_size)}\n")
            self._write_output("\n")

        else:
            self._write_error(f"Unknown area: {area}\n")
            self._write_output("  Options: sessions, logs, states, circuits, config\n")

    def _memory_clear(self, args: List[str]):
        """Clear storage areas with confirmation."""
        if not args:
            self._write_output("\n  Usage: memory clear [cache|logs|states|pycache|all]\n")
            self._write_output("         memory clear states <name>  — delete one state by name\n")
            self._write_output("  ⚠️  Destructive operations require confirmation.\n\n")
            return

        area = args[0].lower()
        from pathlib import Path
        base = Path.home() / ".frankenstein"

        if area == "cache":
            # Clear gate cache and general cache — report bytes freed
            cache_dirs = [
                base / "cache",
                base / "synthesis_data" / "cache",
            ]
            cleared = 0
            cleared_bytes = 0
            for d in cache_dirs:
                if d.exists():
                    for f in d.glob("*"):
                        if f.is_file():
                            cleared_bytes += f.stat().st_size
                            f.unlink()
                            cleared += 1
            self._write_output(
                f"\n  ✅ Cache cleared: {cleared} files removed"
                f" ({self._format_size(cleared_bytes)} freed).\n\n"
            )

        elif area == "logs":
            keep = 10
            if len(args) > 1 and args[1].isdigit():
                keep = int(args[1])
            try:
                from synthesis.computation_log import ComputationLogger
                result = ComputationLogger.clear_old_logs(keep_last=keep)
                self._write_output(f"\n  ✅ Cleared {result['deleted_files']} old log files ({result['freed_kb']} KB freed).\n")
                self._write_output(f"  Kept {result['remaining_logs']} most recent logs.\n\n")
            except ImportError:
                self._write_output("\n  Computation logger not available.\n\n")

        elif area == "states":
            states_dir = base / "synthesis_data" / "states"
            # Specific state deletion by name
            if len(args) > 1 and args[1] not in ("--confirm",):
                name = args[1]
                target = states_dir / f"{name}.npz"
                if not target.exists():
                    self._write_error(f"\n  State '{name}' not found.\n\n")
                    return
                size = target.stat().st_size
                target.unlink()
                self._write_output(
                    f"\n  ✅ Deleted state '{name}' ({self._format_size(size)} freed).\n\n"
                )
                return

            files = list(states_dir.glob("*.npz")) if states_dir.exists() else []
            if not files:
                self._write_output("\n  No saved states to clear.\n\n")
                return

            self._write_output(f"\n  ⚠️  This will delete {len(files)} saved quantum states.\n")
            if len(args) > 1 and args[1] == "--confirm":
                total_bytes = sum(f.stat().st_size for f in files)
                for f in files:
                    f.unlink()
                self._write_output(
                    f"  ✅ Deleted {len(files)} state files"
                    f" ({self._format_size(total_bytes)} freed).\n\n"
                )
            else:
                self._write_output("  Add --confirm to proceed: memory clear states --confirm\n")
                self._write_output("  To delete one:           memory clear states <name>\n\n")

        elif area == "pycache":
            # Clear __pycache__ directories from the Frankenstein project
            import os
            project_dir = Path(r"C:\Users\adamn\Frankenstein-1.0")
            cleared_dirs = 0
            cleared_bytes = 0
            for root, dirs, files in os.walk(project_dir):
                for d in dirs:
                    if d == "__pycache__":
                        cache_path = Path(root) / d
                        for f in cache_path.iterdir():
                            if f.is_file():
                                cleared_bytes += f.stat().st_size
                                f.unlink()
                        cleared_dirs += 1
            self._write_output(
                f"\n  ✅ __pycache__ cleared: {cleared_dirs} dirs"
                f" ({self._format_size(cleared_bytes)} freed).\n\n"
            )

        elif area == "all":
            self._write_output("\n  ⚠️  This will clear: cache, old logs, and saved states.\n")
            self._write_output("  Circuits and session data will NOT be deleted.\n")
            if len(args) > 1 and args[1] == "--confirm":
                self._memory_clear(["cache"])
                self._memory_clear(["logs"])
                self._memory_clear(["states", "--confirm"])
            else:
                self._write_output("  Add --confirm to proceed: memory clear all --confirm\n\n")

        else:
            self._write_error(f"Unknown area: {area}\n")
            self._write_output("  Options: cache, logs [N], states, pycache, all\n")

    def _memory_export(self):
        """Export memory usage report to JSON file."""
        import json
        from pathlib import Path
        from datetime import datetime

        report = {
            "generated": datetime.now().isoformat(),
            "engine": "Frankenstein 1.0",
        }

        # Collect all storage stats
        base = Path.home() / ".frankenstein"
        for area_name, subdir in [
            ("session", ""),
            ("history", "history"),
            ("adaptation", "data"),
            ("logs", "logs"),
            ("quantum_states", "synthesis_data/states"),
            ("simulation_results", "synthesis_data/results"),
            ("circuits", "synthesis_data/circuits"),
            ("gate_cache", "synthesis_data/cache"),
            ("computation_logs", "synthesis_data/logs"),
        ]:
            path = base / subdir if subdir else base
            size = 0
            count = 0
            if path.exists():
                for f in path.rglob("*"):
                    if f.is_file():
                        size += f.stat().st_size
                        count += 1
            report[area_name] = {"bytes": size, "files": count}

        # Write report
        report_path = base / "memory_report.json"
        report_path.write_text(json.dumps(report, indent=2))
        self._write_output(f"\n  ✅ Memory report exported to: {report_path}\n\n")

    def _memory_help(self):
        """Show memory command help."""
        help_text = """
╔══════════════════════════════════════════════════════════╗
║                  MEMORY MANAGEMENT HELP                 ║
╚══════════════════════════════════════════════════════════╝

  memory                  Overview of all storage areas
  memory status           Detailed RAM + disk + Frankenstein usage
  memory view sessions    View session state and task history
  memory view logs        View computation log files
  memory view states      View saved quantum states
  memory view circuits    View saved circuits (same as 'circuit list')
  memory view config      View configuration files
  memory clear cache      Clear gate cache and temp files
  memory clear logs [N]   Delete old logs, keep last N (default: 10)
  memory clear states --confirm   Delete all saved quantum states
  memory clear all --confirm      Clear cache + logs + states
  memory export           Export full memory report to JSON

  Storage Location: ~/.frankenstein/
  Budget: 20 GB (quantum data) + 10 GB (system data) = 30 GB max
"""
        self._write_output(help_text)

    @staticmethod
    def _format_size(bytes_val: int) -> str:
        """Format bytes as human-readable size."""
        if bytes_val < 1024:
            return f"{bytes_val} B"
        elif bytes_val < 1024 * 1024:
            return f"{bytes_val / 1024:.1f} KB"
        elif bytes_val < 1024 * 1024 * 1024:
            return f"{bytes_val / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_val / (1024 ** 3):.2f} GB"

    # ==================== CIRCUIT LIBRARY ====================

    def _cmd_circuit(self, args: List[str]):
        """Circuit library commands — save, load, list, export, delete."""
        if not args:
            self._circuit_help()
            return

        subcmd = args[0].lower()
        subargs = args[1:] if len(args) > 1 else []

        if subcmd == "list":
            self._circuit_list()
        elif subcmd == "save":
            self._circuit_save(subargs)
        elif subcmd == "load":
            self._circuit_load(subargs)
        elif subcmd == "delete":
            self._circuit_delete(subargs)
        elif subcmd == "export":
            self._circuit_export(subargs)
        elif subcmd == "info":
            self._circuit_info(subargs)
        elif subcmd == "help":
            self._circuit_help()
        else:
            self._write_error(f"Unknown circuit command: {subcmd}\n")
            self._write_output("  Usage: circuit [list|save|load|delete|export|info|help]\n")

    def _circuit_list(self):
        """List all saved circuits."""
        try:
            from synthesis.circuit_library import get_circuit_library
            lib = get_circuit_library()
            circuits = lib.list_circuits()

            if not circuits:
                self._write_output("\n  No circuits saved yet.\n")
                self._write_output("  Save one with: circuit save <name>\n\n")
                return

            self._write_output(f"\n  CIRCUIT LIBRARY ({len(circuits)} circuits):\n\n", color="cyan")
            self._write_output(f"  {'Name':<20} {'Qubits':<8} {'Gates':<8} {'Ver':<5} {'Description'}\n")
            self._write_output(f"  {'─' * 70}\n")
            for c in circuits:
                if "error" in c:
                    self._write_output(f"  {c['name']:<20} ⚠️ {c['error']}\n", color="yellow")
                else:
                    self._write_output(f"  {c['name']:<20} {c['n_qubits']:<8} {c['gates']:<8} v{c['version']:<4} {c['description']}\n")
            self._write_output("\n")
        except ImportError:
            self._write_error("  Circuit library not available.\n")

    def _circuit_save(self, args: List[str]):
        """Save current quantum state's gate log as a named circuit."""
        if not args:
            self._write_output("\n  Usage: circuit save <name> [description]\n\n")
            return

        name = args[0]
        description = " ".join(args[1:]) if len(args) > 1 else ""

        try:
            from synthesis.circuit_library import get_circuit_library, CircuitDefinition
            from synthesis.core.true_engine import get_true_engine

            engine = get_true_engine()
            if engine._state is None:
                self._write_error("  No quantum state initialized. Enter quantum mode first.\n")
                return

            # Build circuit definition from gate log
            circuit = CircuitDefinition(name, engine._state.n_qubits, description)

            for gate_entry in engine._gate_log:
                gate_name = gate_entry.get("gate", "unknown")
                targets = gate_entry.get("targets", [])
                controls = gate_entry.get("controls", [])
                params = gate_entry.get("params", {})
                circuit.add_gate(gate_name, targets, controls if controls else None, params if params else None)

            lib = get_circuit_library()
            filepath = lib.save(circuit)

            self._write_output(f"\n  ✅ Circuit '{name}' saved ({len(circuit.gates)} gates, {circuit.n_qubits} qubits)\n")
            self._write_output(f"  Path: {filepath}\n\n")

            # Log to computation logger
            try:
                from synthesis.computation_log import get_computation_logger
                log = get_computation_logger()
                log.log_circuit_saved(name, len(circuit.gates), circuit.n_qubits)
            except ImportError:
                pass

        except ImportError as e:
            self._write_error(f"  Circuit library not available: {e}\n")

    def _circuit_load(self, args: List[str]):
        """Load a circuit from library and replay its gates."""
        if not args:
            self._write_output("\n  Usage: circuit load <name>\n\n")
            return

        name = args[0]

        try:
            from synthesis.circuit_library import get_circuit_library
            from synthesis.core.true_engine import get_true_engine

            lib = get_circuit_library()
            circuit = lib.load(name)

            if circuit is None:
                self._write_error(f"  Circuit '{name}' not found.\n")
                self._write_output("  Use 'circuit list' to see available circuits.\n")
                return

            # Initialize qubits
            engine = get_true_engine()
            engine.initialize_qubits(circuit.n_qubits, "zero")

            # Replay gates using correct TrueSynthesisEngine method names
            gate_count = 0
            for g in circuit.gates:
                gate_name = g["gate"].lower()
                targets = g["targets"]
                controls = g.get("controls", [])
                params = g.get("params", {})

                try:
                    if gate_name == "h":
                        engine.hadamard(targets[0])
                    elif gate_name == "x":
                        engine.pauli_x(targets[0])
                    elif gate_name == "y":
                        engine.pauli_y(targets[0])
                    elif gate_name == "z":
                        engine.pauli_z(targets[0])
                    elif gate_name == "p":
                        engine.phase(targets[0], params.get("phi", 0.0))
                    elif gate_name == "rx":
                        engine.rotation_x(targets[0], params.get("theta", 0.0))
                    elif gate_name == "ry":
                        engine.rotation_y(targets[0], params.get("theta", 0.0))
                    elif gate_name == "rz":
                        engine.rotation_z(targets[0], params.get("theta", 0.0))
                    elif gate_name in ("cx", "cnot") and controls:
                        engine.cnot(controls[0], targets[0])
                    elif gate_name == "cz" and controls:
                        engine.cz(controls[0], targets[0])
                    elif gate_name == "swap" and len(targets) >= 2:
                        engine.swap(targets[0], targets[1])
                    elif gate_name in ("mcx", "ccx", "toffoli") and controls:
                        engine.mcx(controls, targets[0])
                    else:
                        self._write_output(f"  ⚠️ Skipped unknown gate: {gate_name}\n", color="yellow")
                        continue
                    gate_count += 1
                except Exception as e:
                    self._write_output(f"  ⚠️ Gate {gate_name} failed: {e}\n", color="yellow")

            self._write_output(f"\n  ✅ Circuit '{name}' loaded: {gate_count}/{len(circuit.gates)} gates applied to {circuit.n_qubits} qubits\n")
            if circuit.description:
                self._write_output(f"  Description: {circuit.description}\n")
            self._write_output(f"  Use 'measure' in quantum mode to see results, or continue adding gates.\n\n")

        except ImportError as e:
            self._write_error(f"  Circuit library not available: {e}\n")

    def _circuit_delete(self, args: List[str]):
        """Delete a circuit from library."""
        if not args:
            self._write_output("\n  Usage: circuit delete <name>\n\n")
            return

        name = args[0]
        confirm = len(args) > 1 and args[1] == "--confirm"

        try:
            from synthesis.circuit_library import get_circuit_library
            lib = get_circuit_library()

            circuit = lib.load(name)
            if circuit is None:
                self._write_error(f"  Circuit '{name}' not found.\n")
                return

            if not confirm:
                self._write_output(f"\n  ⚠️  Delete circuit '{name}' ({len(circuit.gates)} gates, {circuit.n_qubits} qubits)?\n")
                self._write_output(f"  Run: circuit delete {name} --confirm\n\n")
                return

            lib.delete(name)
            self._write_output(f"\n  ✅ Circuit '{name}' deleted.\n\n")

        except ImportError:
            self._write_error("  Circuit library not available.\n")

    def _circuit_export(self, args: List[str]):
        """Export circuit to OpenQASM 2.0."""
        if not args:
            self._write_output("\n  Usage: circuit export <name>\n\n")
            return

        name = args[0]

        try:
            from synthesis.circuit_library import get_circuit_library
            lib = get_circuit_library()

            filepath = lib.export_qasm(name)
            if filepath is None:
                self._write_error(f"  Circuit '{name}' not found.\n")
                return

            self._write_output(f"\n  ✅ Exported to OpenQASM 2.0: {filepath}\n")
            self._write_output(f"  Import in Qiskit: qiskit.qasm2.load('{filepath}')\n")
            self._write_output(f"  View contents: cat {filepath}\n\n")

            # Show the QASM content
            qasm_content = filepath.read_text()
            self._write_output("  ─── QASM CONTENT ───\n", color="cyan")
            for line in qasm_content.split("\n")[:20]:  # Show first 20 lines
                self._write_output(f"  {line}\n")
            if qasm_content.count("\n") > 20:
                self._write_output(f"  ... ({qasm_content.count(chr(10)) - 20} more lines)\n")
            self._write_output("  ─────────────────────\n\n")

        except ImportError:
            self._write_error("  Circuit library not available.\n")

    def _circuit_info(self, args: List[str]):
        """Show detailed circuit information."""
        if not args:
            self._write_output("\n  Usage: circuit info <name>\n\n")
            return

        name = args[0]

        try:
            from synthesis.circuit_library import get_circuit_library
            lib = get_circuit_library()
            circuit = lib.load(name)

            if circuit is None:
                self._write_error(f"  Circuit '{name}' not found.\n")
                return

            self._write_output(f"\n  CIRCUIT: {circuit.name} (v{circuit.version})\n", color="cyan")
            self._write_output(f"  ─────────────────────────────\n")
            self._write_output(f"  Description: {circuit.description or '(none)'}\n")
            self._write_output(f"  Qubits:      {circuit.n_qubits}\n")
            self._write_output(f"  Gates:       {len(circuit.gates)}\n")
            self._write_output(f"  Depth:       ~{circuit.depth_estimate()}\n")
            self._write_output(f"  Created:     {circuit.created}\n")
            self._write_output(f"  Modified:    {circuit.modified}\n")
            self._write_output(f"  Tags:        {', '.join(circuit.tags) if circuit.tags else '(none)'}\n")

            # Gate breakdown
            counts = circuit.gate_count()
            if counts:
                self._write_output(f"\n  Gate Breakdown:\n")
                for gate, count in sorted(counts.items()):
                    self._write_output(f"    {gate.upper()}: {count}\n")

            # Show gate sequence
            self._write_output(f"\n  Gate Sequence:\n")
            for i, g in enumerate(circuit.gates[:20]):
                controls = g.get("controls", [])
                targets = g["targets"]
                params = g.get("params", {})

                ctrl_str = f" ctrl={controls}" if controls else ""
                param_str = f" ({', '.join(f'{k}={v}' for k, v in params.items())})" if params else ""
                self._write_output(f"    {i+1:3}. {g['gate'].upper()} target={targets}{ctrl_str}{param_str}\n")

            if len(circuit.gates) > 20:
                self._write_output(f"    ... ({len(circuit.gates) - 20} more gates)\n")

            self._write_output("\n")

        except ImportError:
            self._write_error("  Circuit library not available.\n")

    def _circuit_help(self):
        """Show circuit command help."""
        help_text = """
╔══════════════════════════════════════════════════════════╗
║                  CIRCUIT LIBRARY HELP                   ║
╚══════════════════════════════════════════════════════════╝

  circuit list            List all saved circuits
  circuit save <name>     Save current quantum circuit
  circuit load <name>     Load circuit and apply gates
  circuit delete <name>   Delete circuit (add --confirm)
  circuit export <name>   Export to OpenQASM 2.0 (.qasm)
  circuit info <name>     Show detailed circuit info

  WORKFLOW:
    1. Enter quantum mode:    quantum
    2. Build a circuit:       qubit 3 → h 0 → cx 0 1 → cx 0 2
    3. Save it:               circuit save my_ghz A 3-qubit GHZ state
    4. Later, reload it:      circuit load my_ghz
    5. Export for Qiskit:     circuit export my_ghz

  Storage: ~/.frankenstein/synthesis_data/circuits/
  QASM exports: ~/.frankenstein/synthesis_data/circuits/qasm/
"""
        self._write_output(help_text)

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
                # Switch FRANK to quantum-active inference profile (Profile A)
                try:
                    from agents.sauron import is_loaded, get_sauron
                    if is_loaded():
                        get_sauron().set_quantum_active(True)
                except Exception:
                    pass
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
                'frank': (
                    'frank <cmd> - Frankenstein commands + [FRANK] AI\n'
                    '  frank help            Full FRANK command guide (also shows at chat start)\n'
                    '  frank chat            Enter FRANK interactive AI chat mode\n'
                    '  frank ask <text>      Single-shot AI query (no history)\n'
                    '  frank status          AI health check (never loads model)\n'
                    '  frank agents          List discoverable agents\n'
                    '  frank reset           Clear conversation history\n'
                    '  frank unload          Free Phi-3.5 model from RAM (~2.5 GB)\n'
                    '  frank version/quote   Frankenstein info & quotes\n'
                    '\nIN-CHAT SHORTCUTS (once inside frank chat):\n'
                    '  !run <cmd>   Propose a terminal command for guarded execution\n'
                    '  !help        Full command guide (same as frank help)\n'
                    '  !commands    Dense tier reference for all 69+ commands\n'
                    '  !history     Show FRANK execution audit log for this session\n'
                    '  !status      Quick FRANK AI health check\n'
                    '  y / yes      Approve a pending TIER 2 (modify) OR Ring 2 quantum op\n'
                    '  CONFIRM      Approve a pending TIER 1 (destructive) command\n'
                    '  n / cancel   Reject any pending command or quantum operation\n'
                    '  exit / quit  Leave FRANK chat mode\n'
                    '\nAUTOMATIC EXECUTION:\n'
                    '  FRANK detects when a command is needed and proposes it via\n'
                    '  ::EXEC:: token in its response. For quantum ops, FRANK uses\n'
                    '  ::QUANTUM:: tokens — Ring 3 ops run instantly, Ring 2 need y/n.\n'
                    '\nCONTEXT AWARENESS:\n'
                    '  FRANK receives a live system context block on every message:\n'
                    '  active quantum state, saved states/circuits, session stats,\n'
                    '  storage usage, CPU/RAM. Ask "what states do I have?" and FRANK\n'
                    '  will answer from context without extra commands.'
                ),
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

30 provider adapters available!

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

30 provider adapters available.

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

INTELLIGENT ROUTER

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
  Hard limits enforced: CPU max 80%, RAM max 75%
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
                # Real-Time Adaptation (Phase 3 Step 7)
                'adapt-status': '''adapt-status - Display current adaptation status

REAL-TIME ADAPTATION

Shows monitoring status, resource usage, safety limits, and total adaptations.

EXAMPLE OUTPUT:
  ============================================================
  REAL-TIME ADAPTATION STATUS
  ============================================================
  Monitoring Active: YES
  Total Adaptations: 5
  Concurrent:        0
  CPU Usage:         24.3%
  RAM Usage:         45.1%

  Safety Limits:
    CPU:  24.3% / 80% (Safe: True)
    RAM:  45.1% / 75% (Safe: True)
  ============================================================
''',
                'adapt-patterns': '''adapt-patterns [task_type] - View learned adaptation patterns

USAGE:
  adapt-patterns              Show all patterns summary
  adapt-patterns quantum_sim  Show patterns for specific task type

Displays learned execution patterns including:
  - Provider success rates
  - Confidence scores
  - Resource profiles (CPU, RAM)
  - Execution counts
''',
                'adapt-performance': '''adapt-performance [provider_id] - View performance metrics

USAGE:
  adapt-performance            Show provider rankings
  adapt-performance ibm_q      Show metrics for specific provider

Displays:
  - Provider rankings by latency
  - Average metrics (latency, CPU, RAM)
  - Degradation alerts if present
  - Recent execution history
''',
                'adapt-insights': '''adapt-insights - Analyze adaptation patterns and effectiveness

Shows advanced analytics:
  - High-performing providers
  - Underperforming providers
  - Adaptation effectiveness metrics
  - Recent adaptation reasons
  - Success/failure patterns
''',
                'adapt-recommend': '''adapt-recommend <task_type> - Get provider recommendation

USAGE:
  adapt-recommend quantum_simulation

Returns:
  - Recommended provider ID
  - Confidence score (0-100%)
  - Expected success rate
  - Resource estimates (CPU, RAM, duration)
  - Reason for recommendation
''',
                'adapt-history': '''adapt-history [limit] - View adaptation history

USAGE:
  adapt-history      Show last 10 adaptations
  adapt-history 25   Show last 25 adaptations

Displays chronological log of:
  - Task IDs
  - Success/failure status
  - Adaptation reasons
  - Provider switches
  - Timestamps
''',
                'adapt-dashboard': '''adapt-dashboard - Display full adaptation dashboard

Shows complete real-time dashboard with:
  - Status panel (monitoring, CPU, RAM, safety)
  - Performance summary (top providers)
  - Learning summary (patterns learned)
  - Real-time updates

ASCII box-drawing visualization for terminal display.
''',
                # Permissions & Automation (Phase 3 Step 6)
                'permissions': '''permissions - Permission management system

PERMISSION MANAGEMENT

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

SETUP WIZARD

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

AUTOMATED WORKFLOWS

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

TASK SCHEDULER

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

INTELLIGENT WORKLOAD ROUTER

The router automatically selects the best quantum or classical
compute provider for your workload.

HOW IT WORKS:
  1. Analyzes your workload (qubits, memory, priority)
  2. Detects available hardware (CPU, GPU, tier)
  3. Checks resource safety (CPU < 80%, RAM < 75%)
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

  INITIALIZATION:
    qubit <n>       Initialize n qubits in |0> state
    qubit STATE     Initialize specific state (|+>, |0>, etc)
    reset           Reset to |0> state

  SINGLE-QUBIT GATES:
    h <q>           Hadamard gate on qubit q
    x/y/z <q>       Pauli gates
    s/t <q>         Phase gates (S = sqrt(Z), T = 4th-root(Z))
    rx/ry/rz <q> t  Rotation gates (use 'pi' for pi)

  TWO-QUBIT GATES:
    cx <c> <t>      CNOT gate (control c, target t)
    cz <c> <t>      Controlled-Z gate

  MULTI-CONTROLLED GATES (ENHANCED - 16 Qubit Support):
    mcx <ctrls> <t> Multi-Controlled X (MCX)
                    ENHANCED: numpy + scipy + qutip integration
                    Supports up to 16 qubits (15 controls + 1 target)

                    Examples:
                      mcx 0 1              -> CNOT (1 control)
                      mcx 0,1 2            -> Toffoli/CCNOT (2 controls)
                      mcx 0,1,2 3          -> C³X (3 controls)
                      mcx 0,1,2,3 4        -> C⁴X (4 controls)
                      mcx 0,1,2,3,4,5,6 7  -> C⁷X (7 controls)
                      mcx 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14 15 -> C¹⁵X (max)

                    Controls: comma-separated list (NO SPACES)
                    Performance: 1-2: <5ms | 3-7: ~50ms | 8+: ~200ms
                    Algorithm: Gate decomp (1-2) | NumPy (3-7) | SciPy sparse (8+)
                    Use for: Grover search, amplitude amplification, oracle design

  MEASUREMENT & VISUALIZATION:
    measure         Measure all qubits + auto-launch 3D Bloch sphere
    measure <shots> Specify number of shots (default: 1024)
    bloch           Launch 3D Bloch sphere (Three.js in browser)
    bloch2d         Matplotlib 2D Bloch sphere (X-Z projection)
                    Uses 90% RAM limit (elevated for visualization)
    bloch2d 3d      Matplotlib 3D interactive Bloch sphere
                    Uses 90% RAM limit (elevated for visualization)

  CIRCUITS:
    bell            Quick Bell state creation (2 qubits)
    ghz [n]         Quick GHZ state (n qubits, default 3)
    qft [n]         Quantum Fourier Transform

  EVOLUTION:
    evolve H t      Time evolution under Hamiltonian H for time t

  CONTROLS:
    viz off/on      Toggle auto-visualization
    back/exit       Return to main terminal

AUTO-VISUALIZATION:
  After each 'measure' command, the 3D Bloch sphere opens in browser.
  Use 'viz off' to disable, 'viz on' to enable.

PERFORMANCE NOTES (Tier 1: Dell i3 8th Gen, 8GB RAM):
  MCX Gates (numpy + scipy + qutip):
    - 1-2 controls: <5ms   (gate decomposition)
    - 3-7 controls: ~50ms  (numpy statevector)
    - 8-15 controls: ~200ms (scipy sparse matrices)
    - Maximum: 15 controls + 1 target = 16 qubits

  Visualization:
    - bloch (Three.js): No matplotlib, standard RAM usage
    - bloch2d (matplotlib): 90% RAM limit (elevated for Bloch UI)
    - General ops: 75% RAM limit (standard safety)

  Tips:
    - Use 'viz off' for batch operations with many measurements
    - Use bloch2d when RAM is 75-90% (elevated limit)
    - MCX with 8+ controls uses scipy for efficiency

EXAMPLES:
  # Create Bell state
  quantum
  qubit 2
  h 0
  cx 0 1
  measure

  # Create GHZ state with Toffoli
  quantum
  qubit 3
  h 0
  h 1
  mcx 0,1 2
  measure

  # Advanced: 4-qubit entanglement
  quantum
  qubit 4
  h 0
  h 1
  h 2
  mcx 0,1,2 3
  measure

  # Maximum: 16-qubit entanglement (C¹⁵X gate)
  quantum
  qubit 16
  h 0
  h 1
  h 2
  h 3
  h 4
  h 5
  h 6
  h 7
  h 8
  h 9
  h 10
  h 11
  h 12
  h 13
  h 14
  mcx 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14 15
  measure

  # Matplotlib Bloch sphere (2D/3D)
  quantum
  qubit 1
  rx 0 1.2
  bloch2d       # 2D projection with matplotlib (90% RAM limit)
  bloch2d 3d    # 3D interactive matplotlib (90% RAM limit)
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
                # Memory Management & Circuit Library (Pre-Phase 4)
                'memory': '''memory - Memory management commands

SUBCOMMANDS:
  memory                  Overview of all storage areas
  memory status           Detailed RAM + disk + Frankenstein usage
  memory view sessions    View session state and task history
  memory view logs        View computation log files
  memory view states      View saved quantum states
  memory view circuits    View saved circuits (same as 'circuit list')
  memory view config      View configuration files
  memory clear cache      Clear gate cache and temp files
  memory clear logs [N]   Delete old logs, keep last N (default: 10)
  memory clear states --confirm   Delete all saved quantum states
  memory clear all --confirm      Clear cache + logs + states
  memory export           Export full memory report to JSON

Storage Location: ~/.frankenstein/
Budget: 20 GB (quantum data) + 10 GB (system data) = 30 GB max
''',
                'circuit': '''circuit - Circuit library commands

SUBCOMMANDS:
  circuit list            List all saved circuits
  circuit save <name>     Save current quantum circuit from gate log
  circuit load <name>     Load circuit and replay gates on TrueSynthesisEngine
  circuit delete <name>   Delete circuit (add --confirm to execute)
  circuit export <name>   Export to OpenQASM 2.0 (.qasm file)
  circuit info <name>     Show detailed gate sequence and stats

WORKFLOW:
  1. Enter quantum mode:    quantum
  2. Build a circuit:       qubit 3 → h 0 → cx 0 1 → cx 0 2
  3. Return to terminal:    back
  4. Save the circuit:      circuit save my_ghz A 3-qubit GHZ state
  5. Later, reload it:      circuit load my_ghz
  6. Export for Qiskit:     circuit export my_ghz

Storage: ~/.frankenstein/synthesis_data/circuits/
QASM exports: ~/.frankenstein/synthesis_data/circuits/qasm/
''',
                'saves': 'saves - Show all saved quantum artifacts (states, circuits, computation logs)',
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

PROVIDERS (30 Quantum + Classical Adapters):
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

INTELLIGENT ROUTER:
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
  |  Safety: CPU max 80%, RAM max 75% enforced        |
  |  Details: help route  |  Topics: help routing     |
  +----------------------------------------------------+

PERMISSIONS AND AUTOMATION:
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

REAL-TIME ADAPTATION:
  help adapt-status        View current adaptation status
  help adapt-patterns      View learned patterns
  help adapt-performance   View performance metrics
  help adapt-insights      View adaptation analytics
  help adapt-recommend     Get provider recommendations
  help adapt-history       View adaptation history
  help adapt-dashboard     View full adaptation dashboard

  +----------------------------------------------------+
  |  REAL-TIME ADAPTATION QUICK START:                |
  |                                                    |
  |  adapt-status                                     |
  |    Show monitoring status, CPU/RAM, safety limits  |
  |                                                    |
  |  adapt-dashboard                                  |
  |    Full ASCII dashboard with all panels            |
  |                                                    |
  |  adapt-recommend quantum_simulation               |
  |    Get best provider for task type                 |
  |                                                    |
  |  adapt-performance                                |
  |    View provider rankings by latency               |
  |                                                    |
  |  adapt-insights                                   |
  |    Analyze high/low performers and effectiveness   |
  |                                                    |
  |  FEATURES:                                        |
  |  • EMA learning (30% new, 70% historical)         |
  |  • Multi-factor confidence scoring                |
  |  • 3-tier intelligent routing                     |
  |  • Provider health monitoring (4 states)          |
  |  • Automatic failover & degradation detection     |
  |  • SQLite + JSON persistence                      |
  |  • Safety: CPU max 80%, RAM max 75%               |
  |                                                    |
  |  Details: help adapt-status  |  help adapt-patterns|
  +----------------------------------------------------+

QUANTUM MODE:
  quantum         Enter quantum computing mode (or 'q')
  qubit <n>       Quick qubit initialization

  +----------------------------------------------------+
  |  QUANTUM MODE QUICK START:                        |
  |                                                    |
  |  1. Type 'quantum' or 'q' to enter quantum mode   |
  |  2. Initialize: qubit 3  (creates 3 qubits)       |
  |  3. Apply gates: h 0, h 1  (superposition)        |
  |  4. Multi-control: mcx 0,1 2  (Toffoli gate)      |
  |  5. Measure: measure  (auto-shows 3D Bloch!)      |
  |  6. Type 'back' to return to main terminal        |
  |                                                    |
  |  ENHANCED FEATURES (numpy + scipy + qutip):       |
  |    mcx 0,1,2 3         <- C³X (3 controls)        |
  |    mcx 0,1,2,3,4,5,6 7 <- C⁷X (7 controls, scipy) |
  |    Max: 16 qubits (15 controls + 1 target)        |
  |                                                    |
  |  VISUALIZATION OPTIONS:                           |
  |    bloch      <- 3D Three.js (browser)            |
  |    bloch2d    <- 2D matplotlib (90% RAM)          |
  |    bloch2d 3d <- 3D matplotlib (90% RAM)          |
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

MEMORY MANAGEMENT:
  memory                  Memory system overview
  memory status           Detailed storage + RAM usage
  memory view [area]      View stored data (sessions/logs/states/circuits/config)
  memory clear [area]     Clear cache/logs/states (requires --confirm for states)
  memory export           Export usage report to JSON

CIRCUIT LIBRARY:
  circuit list            List saved circuits
  circuit save <name>     Save current quantum circuit
  circuit load <name>     Load and replay circuit gates
  circuit delete <name>   Delete circuit (requires --confirm)
  circuit export <name>   Export to OpenQASM 2.0 (.qasm)
  circuit info <name>     Detailed circuit information

ARTIFACT OVERVIEW:
  saves                   Show all saved states, circuits, and computation logs

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
