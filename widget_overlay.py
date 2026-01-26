"""
FRANKENSTEIN 1.0 - Widget Overlay
Phase 1: Core Engine

Purpose: Git Bash style terminal interface - always-on-top command window
Platform: Windows (uses customtkinter)
Author: SynQC Project
"""

import threading
import time
import queue
import sys
from typing import Optional, Callable, List
from datetime import datetime

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    print("ERROR: customtkinter not installed. Run: pip install customtkinter")

# Terminal color scheme (Git Bash inspired)
COLORS = {
    "bg": "#0C0C0C",           # Dark background
    "fg": "#CCCCCC",           # Default text (light gray)
    "green": "#98C379",        # Success/prompt green
    "yellow": "#E5C07B",       # Warnings
    "red": "#E06C75",          # Errors
    "blue": "#61AFEF",         # Info/links
    "purple": "#C678DD",       # Special
    "cyan": "#56B6C2",         # Paths/system
    "input_bg": "#1E1E1E",     # Input field background
    "border": "#3C3C3C",       # Border color
}


class TerminalOutput:
    """Manages terminal output with colors and scrolling"""
    
    def __init__(self, text_widget: ctk.CTkTextbox):
        self.text = text_widget
        self._setup_tags()
        
    def _setup_tags(self):
        """Configure text tags for colors"""
        pass
        
    def write(self, message: str, color: str = "fg", newline: bool = True):
        """Write message to terminal"""
        self.text.configure(state="normal")
        if newline and not message.endswith("\n"):
            message += "\n"
        self.text.insert("end", message)
        self.text.configure(state="disabled")
        self.text.see("end")
        
    def write_prompt(self):
        """Write the command prompt"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prompt = f"[{timestamp}] frankenstein > "
        self.text.configure(state="normal")
        self.text.insert("end", prompt)
        self.text.configure(state="disabled")
        self.text.see("end")
        
    def clear(self):
        """Clear terminal output"""
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")


class FrankensteinWidget:
    """
    Git Bash style terminal widget for FRANKENSTEIN.
    Always-on-top, dark themed, command interface.
    """
    
    MODES = {
        "minimized": {"width": 400, "height": 50},
        "command": {"width": 600, "height": 300},
        "expanded": {"width": 800, "height": 500},
    }
    
    def __init__(self):
        if not CTK_AVAILABLE:
            raise RuntimeError("customtkinter required. Install with: pip install customtkinter")
            
        self._root: Optional[ctk.CTk] = None
        self._terminal: Optional[TerminalOutput] = None
        self._input_field: Optional[ctk.CTkEntry] = None
        self._status_label: Optional[ctk.CTkLabel] = None
        self._command_queue: queue.Queue = queue.Queue()
        self._command_handlers: dict = {}
        self._running = False
        self._mode = "command"
        self._command_history: List[str] = []
        self._history_index = 0
        
        self._register_builtins()
        
    def _register_builtins(self):
        """Register built-in terminal commands"""
        self._command_handlers = {
            "help": self._cmd_help,
            "clear": self._cmd_clear,
            "cls": self._cmd_clear,
            "status": self._cmd_status,
            "exit": self._cmd_exit,
            "quit": self._cmd_exit,
            "stop": self._cmd_emergency_stop,
            "mode": self._cmd_mode,
            "version": self._cmd_version,
            "about": self._cmd_about,
        }
        
    def create_window(self):
        """Create and configure the main window"""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        
        self._root = ctk.CTk()
        self._root.title("⚡ FRANKENSTEIN 1.0")
        
        mode_size = self.MODES[self._mode]
        self._root.geometry(f"{mode_size['width']}x{mode_size['height']}")
        self._root.configure(fg_color=COLORS["bg"])
        self._root.attributes("-topmost", True)
        self._root.minsize(300, 100)
        
        self._create_header()
        self._create_terminal()
        self._create_input()
        
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._root.bind("<Control-l>", lambda e: self._cmd_clear())
        self._root.bind("<Escape>", lambda e: self._minimize())
        
    def _create_header(self):
        """Create the header bar with status and controls"""
        header = ctk.CTkFrame(self._root, fg_color=COLORS["input_bg"], height=30)
        header.pack(fill="x", padx=2, pady=2)
        header.pack_propagate(False)
        
        title = ctk.CTkLabel(
            header, 
            text="⚡ FRANKENSTEIN 1.0",
            font=("Consolas", 12, "bold"),
            text_color=COLORS["green"]
        )
        title.pack(side="left", padx=10)
        
        self._status_label = ctk.CTkLabel(
            header,
            text="● READY",
            font=("Consolas", 10),
            text_color=COLORS["green"]
        )
        self._status_label.pack(side="left", padx=20)
        
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right", padx=5)
        
        min_btn = ctk.CTkButton(
            btn_frame, text="_", width=25, height=20,
            font=("Consolas", 12),
            fg_color=COLORS["border"],
            hover_color=COLORS["yellow"],
            command=self._minimize
        )
        min_btn.pack(side="left", padx=2)
        
        exp_btn = ctk.CTkButton(
            btn_frame, text="◻", width=25, height=20,
            font=("Consolas", 10),
            fg_color=COLORS["border"],
            hover_color=COLORS["blue"],
            command=self._toggle_size
        )
        exp_btn.pack(side="left", padx=2)
        
    def _create_terminal(self):
        """Create the terminal output area"""
        term_frame = ctk.CTkFrame(self._root, fg_color=COLORS["bg"])
        term_frame.pack(fill="both", expand=True, padx=5, pady=2)
        
        self._text_widget = ctk.CTkTextbox(
            term_frame,
            font=("Consolas", 11),
            fg_color=COLORS["bg"],
            text_color=COLORS["fg"],
            border_width=1,
            border_color=COLORS["border"],
            wrap="word"
        )
        self._text_widget.pack(fill="both", expand=True)
        self._text_widget.configure(state="disabled")
        
        self._terminal = TerminalOutput(self._text_widget)
        
    def _create_input(self):
        """Create the command input field"""
        input_frame = ctk.CTkFrame(self._root, fg_color=COLORS["input_bg"], height=40)
        input_frame.pack(fill="x", padx=5, pady=5)
        input_frame.pack_propagate(False)
        
        prompt = ctk.CTkLabel(
            input_frame,
            text="❯",
            font=("Consolas", 14, "bold"),
            text_color=COLORS["green"]
        )
        prompt.pack(side="left", padx=(10, 5))
        
        self._input_field = ctk.CTkEntry(
            input_frame,
            font=("Consolas", 12),
            fg_color=COLORS["input_bg"],
            text_color=COLORS["fg"],
            border_width=0,
            placeholder_text="Type command or query..."
        )
        self._input_field.pack(side="left", fill="x", expand=True, padx=5)
        
        self._input_field.bind("<Return>", self._on_submit)
        self._input_field.bind("<Up>", self._history_up)
        self._input_field.bind("<Down>", self._history_down)
        
        submit_btn = ctk.CTkButton(
            input_frame,
            text="→",
            width=40,
            font=("Consolas", 14),
            fg_color=COLORS["green"],
            hover_color=COLORS["cyan"],
            command=lambda: self._on_submit(None)
        )
        submit_btn.pack(side="right", padx=5)
        
    def _on_submit(self, event):
        """Handle command submission"""
        command = self._input_field.get().strip()
        if not command:
            return
            
        self._command_history.append(command)
        self._history_index = len(self._command_history)
        self._input_field.delete(0, "end")
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._terminal.write(f"[{timestamp}] > {command}", color="cyan")
        self._process_command(command)
        
    def _history_up(self, event):
        """Navigate command history up"""
        if self._command_history and self._history_index > 0:
            self._history_index -= 1
            self._input_field.delete(0, "end")
            self._input_field.insert(0, self._command_history[self._history_index])
            
    def _history_down(self, event):
        """Navigate command history down"""
        if self._history_index < len(self._command_history) - 1:
            self._history_index += 1
            self._input_field.delete(0, "end")
            self._input_field.insert(0, self._command_history[self._history_index])
        else:
            self._history_index = len(self._command_history)
            self._input_field.delete(0, "end")
            
    def _process_command(self, command: str):
        """Process a command"""
        parts = command.lower().split()
        if not parts:
            return
            
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        if cmd in self._command_handlers:
            try:
                self._command_handlers[cmd](args)
            except Exception as e:
                self._terminal.write(f"Error: {e}", color="red")
        else:
            self._terminal.write(f"Unknown command: {cmd}", color="yellow")
            self._terminal.write("Type 'help' for available commands.", color="fg")
            
    def _cmd_help(self, args=None):
        """Show help information"""
        help_text = """
╔══════════════════════════════════════════════════════════════╗
║                    FRANKENSTEIN 1.0 COMMANDS                  ║
╠══════════════════════════════════════════════════════════════╣
║  help          - Show this help message                       ║
║  status        - Show system status and resource usage        ║
║  clear / cls   - Clear terminal output                        ║
║  mode [size]   - Change window size (min/cmd/exp)            ║
║  version       - Show version information                     ║
║  about         - About FRANKENSTEIN                           ║
║  stop          - Emergency stop all operations                ║
║  exit / quit   - Close widget (Ctrl+Q)                       ║
╠══════════════════════════════════════════════════════════════╣
║  SHORTCUTS:  Ctrl+L = Clear  |  Esc = Minimize  |  ↑↓ = History║
╚══════════════════════════════════════════════════════════════╝
"""
        self._terminal.write(help_text)
        
    def _cmd_clear(self, args=None):
        """Clear terminal"""
        self._terminal.clear()
        self._show_banner()
        
    def _cmd_status(self, args=None):
        """Show system status"""
        try:
            from core import get_governor
            governor = get_governor()
            status = governor.get_status()
            
            safe_icon = "✅" if status['safe'] else "❌"
            throttle_icon = "🔻" if status.get('throttle_active') else "✓"
            
            status_text = f"""
┌─────────────────────────────────────┐
│         SYSTEM STATUS               │
├─────────────────────────────────────┤
│  CPU Usage:    {status['cpu_percent']:5.1f}% / 80%        │
│  Memory:       {status['memory_percent']:5.1f}% / 70%        │
│  Safe:         {safe_icon}                       │
│  Throttle:     {throttle_icon}                       │
│  Governor:     {'Running' if status['running'] else 'Stopped'}              │
└─────────────────────────────────────┘
"""
            self._terminal.write(status_text)
            
            if status['safe']:
                self._status_label.configure(text="● READY", text_color=COLORS["green"])
            else:
                self._status_label.configure(text="● WARNING", text_color=COLORS["yellow"])
                
        except ImportError:
            self._terminal.write("Governor not available - core module not loaded", color="yellow")
        except Exception as e:
            self._terminal.write(f"Status error: {e}", color="red")
            
    def _cmd_exit(self, args=None):
        """Exit the widget"""
        self._on_close()
        
    def _cmd_emergency_stop(self, args=None):
        """Emergency stop"""
        try:
            from core import get_governor
            governor = get_governor()
            result = governor.emergency_stop()
            self._terminal.write(f"⚠️ EMERGENCY STOP: {result['status']}", color="red")
            self._status_label.configure(text="● STOPPED", text_color=COLORS["red"])
        except Exception as e:
            self._terminal.write(f"Emergency stop error: {e}", color="red")
            
    def _cmd_mode(self, args):
        """Change widget mode/size"""
        if not args:
            self._terminal.write(f"Current mode: {self._mode}")
            self._terminal.write("Available: minimized (min), command (cmd), expanded (exp)")
            return
            
        mode_map = {
            "min": "minimized", "minimized": "minimized",
            "cmd": "command", "command": "command",
            "exp": "expanded", "expanded": "expanded"
        }
        
        new_mode = mode_map.get(args[0].lower())
        if new_mode:
            self._set_mode(new_mode)
            self._terminal.write(f"Mode changed to: {new_mode}")
        else:
            self._terminal.write(f"Unknown mode: {args[0]}", color="yellow")
            
    def _cmd_version(self, args=None):
        """Show version"""
        self._terminal.write("FRANKENSTEIN 1.0.0 - Phase 1 Core Engine")
        self._terminal.write("Python: " + sys.version.split()[0])
        
    def _cmd_about(self, args=None):
        """Show about info"""
        about_text = """
╔══════════════════════════════════════════════════════════════╗
║              ⚡ FRANKENSTEIN 1.0 ⚡                           ║
║     "It's alive... and ready to serve science."              ║
╠══════════════════════════════════════════════════════════════╣
║  Physics-grounded AI Desktop Assistant                        ║
║  Predictive Synthesis Engine (NOT Generative AI)             ║
║                                                               ║
║  Core Innovation: Schrödinger equation wave evolution        ║
║  + Lorentz transformations for physics-valid outputs         ║
╚══════════════════════════════════════════════════════════════╝
"""
        self._terminal.write(about_text)
        
    def _set_mode(self, mode: str):
        """Set widget mode and resize"""
        if mode in self.MODES:
            self._mode = mode
            size = self.MODES[mode]
            self._root.geometry(f"{size['width']}x{size['height']}")
            
    def _toggle_size(self):
        """Toggle between command and expanded mode"""
        if self._mode == "command":
            self._set_mode("expanded")
        else:
            self._set_mode("command")
            
    def _minimize(self):
        """Minimize window"""
        if self._root:
            self._root.iconify()
            
    def _on_close(self):
        """Handle window close"""
        self._running = False
        if self._root:
            self._root.quit()
            self._root.destroy()
            
    def _show_banner(self):
        """Show startup banner"""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║              ⚡ FRANKENSTEIN 1.0 ⚡                           ║
║           Physics-Grounded AI Assistant                       ║
║                                                               ║
║  Type 'help' for commands | 'status' for system info         ║
╚══════════════════════════════════════════════════════════════╝
"""
        self._terminal.write(banner, color="green")
        
    def run(self):
        """Run the widget main loop"""
        self._running = True
        self.create_window()
        self._show_banner()
        self._input_field.focus_set()
        self._root.mainloop()
        

_widget: Optional[FrankensteinWidget] = None

def get_widget() -> FrankensteinWidget:
    """Get or create the global widget instance"""
    global _widget
    if _widget is None:
        _widget = FrankensteinWidget()
    return _widget

def launch_widget():
    """Launch the widget - main entry point"""
    widget = get_widget()
    widget.run()


if __name__ == "__main__":
    launch_widget()
