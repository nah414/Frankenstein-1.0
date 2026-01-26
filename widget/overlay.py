"""
FRANKENSTEIN 1.0 - Widget Overlay
Phase 2: With Security Integration

Features:
- Git Bash style terminal
- Right-click context menu (copy/paste)
- Security alerts display
- Proper keyboard handling
"""

import sys
import traceback
from typing import Optional, List
from datetime import datetime

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    print("ERROR: customtkinter not installed. Run: pip install customtkinter")

COLORS = {
    "bg": "#0C0C0C",
    "fg": "#CCCCCC",
    "green": "#98C379",
    "yellow": "#E5C07B",
    "red": "#E06C75",
    "blue": "#61AFEF",
    "cyan": "#56B6C2",
    "input_bg": "#1E1E1E",
    "border": "#3C3C3C",
}


class TerminalOutput:
    def __init__(self, text_widget):
        self.text = text_widget

    def write(self, message: str, level: str = "info"):
        try:
            self.text.configure(state="normal")
            if not message.endswith("\n"):
                message += "\n"
            self.text.insert("end", message)
            self.text.configure(state="disabled")
            self.text.see("end")
        except Exception as e:
            print(f"Write error: {e}")

    def write_security(self, message: str, threat_level: str = "info"):
        prefix = {
            "info": "[SECURITY]",
            "warn": "[SECURITY WARNING]",
            "error": "[SECURITY ALERT]",
            "block": "[BLOCKED]"
        }.get(threat_level, "[SECURITY]")
        self.write(f"{prefix} {message}")

    def clear(self):
        try:
            self.text.configure(state="normal")
            self.text.delete("1.0", "end")
            self.text.configure(state="disabled")
        except:
            pass


class FrankensteinWidget:
    MODES = {
        "command": {"width": 700, "height": 400},
        "expanded": {"width": 950, "height": 600},
    }

    def __init__(self):
        if not CTK_AVAILABLE:
            raise RuntimeError("customtkinter required")
        self._root = None
        self._terminal = None
        self._input_field = None
        self._text_widget = None
        self._status_label = None
        self._command_handlers = {}
        self._running = False
        self._mode = "command"
        self._command_history = []
        self._history_index = 0
        self._security_shield = None
        self._register_builtins()

    def _register_builtins(self):
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
            "test": self._cmd_test,
            "security": self._cmd_security,
        }

    def set_security_shield(self, shield):
        self._security_shield = shield

    def create_window(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self._root = ctk.CTk()
        self._root.title("FRANKENSTEIN 1.0")

        size = self.MODES[self._mode]
        self._root.geometry(f"{size['width']}x{size['height']}")
        self._root.configure(fg_color=COLORS["bg"])
        self._root.attributes("-topmost", True)
        self._root.minsize(500, 300)

        self._create_header()
        self._create_terminal()
        self._create_input()

        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._root.bind("<Control-l>", lambda e: self._cmd_clear())
        self._root.bind("<Control-q>", lambda e: self._on_close())

    def _create_header(self):
        header = ctk.CTkFrame(self._root, fg_color=COLORS["input_bg"], height=38)
        header.pack(fill="x", padx=2, pady=2)
        header.pack_propagate(False)

        title = ctk.CTkLabel(header, text="[F] FRANKENSTEIN 1.0",
                            font=("Consolas", 12, "bold"), text_color=COLORS["green"])
        title.pack(side="left", padx=10)

        self._status_label = ctk.CTkLabel(header, text="READY",
                                         font=("Consolas", 10), text_color=COLORS["green"])
        self._status_label.pack(side="left", padx=20)

        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right", padx=5)

        ctk.CTkButton(btn_frame, text="[ ]", width=30, height=24,
                     font=("Consolas", 10), fg_color=COLORS["border"],
                     command=self._toggle_size).pack(side="left", padx=2)

        ctk.CTkButton(btn_frame, text="_", width=30, height=24,
                     font=("Consolas", 12), fg_color=COLORS["border"],
                     command=self._minimize).pack(side="left", padx=2)

    def _create_terminal(self):
        term_frame = ctk.CTkFrame(self._root, fg_color=COLORS["bg"])
        term_frame.pack(fill="both", expand=True, padx=5, pady=2)

        self._text_widget = ctk.CTkTextbox(term_frame, font=("Consolas", 11),
                                          fg_color=COLORS["bg"], text_color=COLORS["fg"],
                                          border_width=1, border_color=COLORS["border"])
        self._text_widget.pack(fill="both", expand=True)
        self._text_widget.configure(state="disabled")

        self._create_context_menu()
        self._terminal = TerminalOutput(self._text_widget)

    def _create_context_menu(self):
        import tkinter as tk
        self._context_menu = tk.Menu(self._root, tearoff=0,
                                    bg=COLORS["input_bg"], fg=COLORS["fg"])
        self._context_menu.add_command(label="Copy", command=self._copy)
        self._context_menu.add_command(label="Paste", command=self._paste)
        self._context_menu.add_separator()
        self._context_menu.add_command(label="Clear", command=self._cmd_clear)
        self._text_widget.bind("<Button-3>", self._show_menu)

    def _show_menu(self, e):
        self._context_menu.tk_popup(e.x_root, e.y_root)

    def _copy(self):
        try:
            self._text_widget.configure(state="normal")
            sel = self._text_widget.selection_get()
            self._root.clipboard_clear()
            self._root.clipboard_append(sel)
            self._text_widget.configure(state="disabled")
        except:
            pass

    def _paste(self):
        try:
            text = self._root.clipboard_get()
            self._input_field.insert("end", text)
        except:
            pass

    def _create_input(self):
        input_frame = ctk.CTkFrame(self._root, fg_color=COLORS["input_bg"], height=48)
        input_frame.pack(fill="x", padx=5, pady=5)
        input_frame.pack_propagate(False)

        ctk.CTkLabel(input_frame, text=">", font=("Consolas", 14, "bold"),
                    text_color=COLORS["green"]).pack(side="left", padx=(10, 5))

        self._input_field = ctk.CTkEntry(input_frame, font=("Consolas", 12),
                                        fg_color=COLORS["input_bg"], text_color=COLORS["fg"],
                                        border_width=1, border_color=COLORS["border"],
                                        placeholder_text="Type command (help for list)")
        self._input_field.pack(side="left", fill="x", expand=True, padx=5, pady=8)

        self._input_field.bind("<Return>", self._on_submit)
        self._input_field.bind("<Up>", self._history_up)
        self._input_field.bind("<Down>", self._history_down)
        self._input_field.bind("<Button-3>", lambda e: self._show_input_menu(e))

        ctk.CTkButton(input_frame, text="Run", width=50, font=("Consolas", 11),
                     fg_color=COLORS["green"], command=lambda: self._on_submit(None)
                     ).pack(side="right", padx=5, pady=8)

    def _show_input_menu(self, e):
        import tkinter as tk
        menu = tk.Menu(self._root, tearoff=0, bg=COLORS["input_bg"], fg=COLORS["fg"])
        menu.add_command(label="Paste", command=self._paste)
        menu.add_command(label="Clear", command=lambda: self._input_field.delete(0, "end"))
        menu.tk_popup(e.x_root, e.y_root)

    def _on_submit(self, event):
        try:
            cmd = self._input_field.get().strip()
            if not cmd:
                return "break"
            self._command_history.append(cmd)
            self._history_index = len(self._command_history)
            self._input_field.delete(0, "end")

            ts = datetime.now().strftime("%H:%M:%S")
            self._terminal.write(f"[{ts}] > {cmd}")

            # Security check before processing
            if self._security_shield:
                is_safe, reason = self._security_shield.check_input(cmd)
                if not is_safe:
                    self._terminal.write_security(reason, "block")
                    return "break"

            self._process_command(cmd)
        except Exception as e:
            self._terminal.write(f"[ERROR] {e}")
        return "break"

    def _history_up(self, e):
        if self._command_history and self._history_index > 0:
            self._history_index -= 1
            self._input_field.delete(0, "end")
            self._input_field.insert(0, self._command_history[self._history_index])
        return "break"

    def _history_down(self, e):
        if self._history_index < len(self._command_history) - 1:
            self._history_index += 1
            self._input_field.delete(0, "end")
            self._input_field.insert(0, self._command_history[self._history_index])
        else:
            self._history_index = len(self._command_history)
            self._input_field.delete(0, "end")
        return "break"

    def _process_command(self, command: str):
        parts = command.split()
        if not parts:
            return
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        if cmd in self._command_handlers:
            try:
                self._command_handlers[cmd](args)
            except Exception as e:
                self._terminal.write(f"[ERROR] {e}")
        else:
            self._terminal.write(f"Unknown: {cmd}. Type 'help' for commands.")

    def _cmd_help(self, args=None):
        self._terminal.write("""
+----------------------------------------------------------+
|                FRANKENSTEIN 1.0 COMMANDS                  |
+----------------------------------------------------------+
| help       - Show this help                               |
| status     - System status                                |
| security   - Security status                              |
| clear/cls  - Clear terminal                               |
| mode       - Change window size (cmd/exp)                 |
| version    - Version info                                 |
| about      - About FRANKENSTEIN                           |
| test       - Test terminal                                |
| stop       - Emergency stop                               |
| exit/quit  - Close                                        |
+----------------------------------------------------------+
| Ctrl+L=Clear | Ctrl+Q=Quit | Right-click=Copy/Paste      |
+----------------------------------------------------------+
""")

    def _cmd_clear(self, args=None):
        self._terminal.clear()
        self._show_banner()

    def _cmd_test(self, args=None):
        self._terminal.write("[TEST] Terminal OK")
        self._terminal.write(f"[TEST] Python {sys.version.split()[0]}")

    def _cmd_status(self, args=None):
        try:
            from core import get_governor
            gov = get_governor()
            s = gov.get_status()
            self._terminal.write(f"""
+----------------------------------+
|          SYSTEM STATUS           |
+----------------------------------+
| CPU:     {s['cpu_percent']:5.1f}% / 80%           |
| Memory:  {s['memory_percent']:5.1f}% / 70%           |
| Safe:    {'YES' if s['safe'] else 'NO':<20} |
| Governor: {'Running' if s['running'] else 'Stopped':<19} |
+----------------------------------+
""")
        except:
            self._terminal.write("[WARN] Governor not loaded")

    def _cmd_security(self, args=None):
        if self._security_shield:
            status = self._security_shield.get_status()
            self._terminal.write(f"""
+----------------------------------+
|        SECURITY STATUS           |
+----------------------------------+
| Shield:    {status.get('active', 'Unknown'):<19} |
| Threats:   {status.get('threats_blocked', 0):<19} |
| Last scan: {status.get('last_scan', 'Never'):<19} |
+----------------------------------+
""")
        else:
            self._terminal.write("[INFO] Security shield not initialized")

    def _cmd_exit(self, args=None):
        self._on_close()

    def _cmd_emergency_stop(self, args=None):
        try:
            from core import get_governor
            gov = get_governor()
            gov.emergency_stop()
            self._terminal.write("[EMERGENCY] System stopped")
            self._status_label.configure(text="STOPPED", text_color=COLORS["red"])
        except Exception as e:
            self._terminal.write(f"[ERROR] {e}")

    def _cmd_mode(self, args):
        if not args:
            self._terminal.write(f"Current: {self._mode}. Options: cmd, exp")
            return
        m = args[0].lower()
        if m in ["cmd", "command"]:
            self._set_mode("command")
        elif m in ["exp", "expanded"]:
            self._set_mode("expanded")
        else:
            self._terminal.write(f"Unknown mode: {m}")

    def _cmd_version(self, args=None):
        self._terminal.write("FRANKENSTEIN 1.0.0 - Phase 2")
        self._terminal.write(f"Python {sys.version.split()[0]}")

    def _cmd_about(self, args=None):
        self._terminal.write("""
+----------------------------------------------------------+
|              FRANKENSTEIN 1.0                             |
|     "It's alive... and ready to serve science."           |
+----------------------------------------------------------+
| Physics-grounded AI Desktop Assistant                     |
| Predictive Synthesis Engine - NOT generative AI           |
+----------------------------------------------------------+
""")

    def _set_mode(self, mode):
        self._mode = mode
        size = self.MODES[mode]
        self._root.geometry(f"{size['width']}x{size['height']}")
        self._terminal.write(f"Mode: {mode}")

    def _toggle_size(self):
        self._set_mode("expanded" if self._mode == "command" else "command")

    def _minimize(self):
        self._root.iconify()

    def _on_close(self):
        self._running = False
        try:
            self._root.quit()
            self._root.destroy()
        except:
            pass

    def _show_banner(self):
        self._terminal.write("""
+----------------------------------------------------------+
|              FRANKENSTEIN 1.0                             |
|           Physics-Grounded AI Assistant                   |
|                                                           |
|  Type 'help' for commands | Right-click for menu          |
+----------------------------------------------------------+
""")

    def run(self):
        self._running = True
        self.create_window()
        self._show_banner()
        self._terminal.write("[OK] Widget ready")
        self._root.after(100, lambda: self._input_field.focus_set())
        self._root.mainloop()


_widget = None

def get_widget():
    global _widget
    if _widget is None:
        _widget = FrankensteinWidget()
    return _widget

def launch_widget():
    get_widget().run()

if __name__ == "__main__":
    launch_widget()
