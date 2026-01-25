"""
FRANKENSTEIN 1.0 - Widget Overlay
Phase 1: Core Engine

Purpose: Always-on-top command & status window
Platform: Windows (uses customtkinter)
"""

import threading
import time
from typing import Optional, Dict, Any

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    print("⚠️ customtkinter not installed. Widget disabled.")

from core import get_governor, get_memory, get_orchestrator


class WidgetMode:
    """Widget display modes"""
    MINIMIZED = (300, 40)   # Status bar only
    COMMAND = (300, 200)    # Command input
    WORKFLOW = (300, 400)   # Full workflow view
    EXPANDED = (400, 600)   # Complete interface


class FrankensteinWidget:
    """
    The always-visible command window.

    Features:
    - Always-on-top across all applications
    - Resource status display
    - Command input
    - Quick actions
    """

    def __init__(self):
        self._root: Optional[ctk.CTk] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._mode = WidgetMode.COMMAND

        # UI elements
        self._status_label = None
        self._cpu_label = None
        self._memory_label = None
        self._command_entry = None

    def start(self) -> bool:
        """Start the widget in a separate thread"""
        if not CTK_AVAILABLE:
            return False

        if self._running:
            return False

        self._running = True
        self._thread = threading.Thread(target=self._run_widget, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        """Stop the widget"""
        self._running = False
        if self._root:
            try:
                self._root.quit()
            except Exception:
                pass

    def _run_widget(self):
        """Main widget loop - runs in separate thread"""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._root = ctk.CTk()
        self._root.title("⚡ FRANKENSTEIN 1.0")
        self._root.geometry(f"{self._mode[0]}x{self._mode[1]}+50+50")
        self._root.attributes("-topmost", True)
        self._root.resizable(False, False)

        # Prevent closing - minimize instead
        self._root.protocol("WM_DELETE_WINDOW", self._minimize)

        self._build_ui()
        self._start_update_loop()

        self._root.mainloop()

    def _build_ui(self):
        """Build the widget UI"""
        # Header frame
        header = ctk.CTkFrame(self._root, height=30)
        header.pack(fill="x", padx=5, pady=5)

        title = ctk.CTkLabel(
            header,
            text="⚡ FRANKENSTEIN 1.0",
            font=("Segoe UI", 12, "bold")
        )
        title.pack(side="left", padx=5)

        # Status indicator
        self._status_label = ctk.CTkLabel(
            header,
            text="🟢 READY",
            font=("Segoe UI", 10)
        )
        self._status_label.pack(side="right", padx=5)

        # Resource frame
        resource_frame = ctk.CTkFrame(self._root)
        resource_frame.pack(fill="x", padx=5, pady=5)

        self._cpu_label = ctk.CTkLabel(
            resource_frame,
            text="CPU: ---%",
            font=("Consolas", 10)
        )
        self._cpu_label.pack(side="left", padx=10)

        self._memory_label = ctk.CTkLabel(
            resource_frame,
            text="RAM: ---%",
            font=("Consolas", 10)
        )
        self._memory_label.pack(side="left", padx=10)

        # Command input
        command_frame = ctk.CTkFrame(self._root)
        command_frame.pack(fill="x", padx=5, pady=5)

        self._command_entry = ctk.CTkEntry(
            command_frame,
            placeholder_text="Enter command...",
            width=220
        )
        self._command_entry.pack(side="left", padx=5)
        self._command_entry.bind("<Return>", self._on_command)

        run_btn = ctk.CTkButton(
            command_frame,
            text="▶",
            width=40,
            command=lambda: self._on_command(None)
        )
        run_btn.pack(side="left", padx=5)

        # Quick actions
        actions_frame = ctk.CTkFrame(self._root)
        actions_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkButton(
            actions_frame,
            text="📊 Status",
            width=80,
            command=self._show_status
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            actions_frame,
            text="🛑 Stop",
            width=80,
            fg_color="red",
            hover_color="darkred",
            command=self._emergency_stop
        ).pack(side="left", padx=2)

    def _start_update_loop(self):
        """Start the status update loop"""
        self._update_status()

    def _update_status(self):
        """Update resource display"""
        if not self._running or not self._root:
            return

        try:
            governor = get_governor()
            status = governor.get_status()

            # Update labels
            self._cpu_label.configure(text=f"CPU: {status['cpu_percent']:.0f}%")
            self._memory_label.configure(text=f"RAM: {status['memory_percent']:.0f}%")

            # Update status indicator
            if status['safe']:
                self._status_label.configure(text="🟢 READY")
            else:
                self._status_label.configure(text="🟡 THROTTLED")

        except Exception as e:
            pass

        # Schedule next update
        if self._running:
            self._root.after(1000, self._update_status)

    def _on_command(self, event):
        """Handle command input"""
        if not self._command_entry:
            return

        command = self._command_entry.get().strip()
        if not command:
            return

        self._command_entry.delete(0, 'end')

        # Process command
        if command.lower() in ['status', 'stats']:
            self._show_status()
        elif command.lower() in ['stop', 'halt', 'emergency']:
            self._emergency_stop()
        else:
            # Submit as task
            orchestrator = get_orchestrator()
            from core import TaskType
            task_id = orchestrator.submit(
                TaskType.CLASSICAL,
                {"command": command}
            )
            print(f"Task submitted: {task_id}")

    def _show_status(self):
        """Show detailed status"""
        governor = get_governor()
        memory = get_memory()

        status = governor.get_status()
        session = memory.get_session_stats()
        orchestrator = get_orchestrator()
        queue_status = orchestrator.get_queue_status()

        print("\n" + "=" * 50)
        print("⚡ FRANKENSTEIN 1.0 STATUS")
        print("=" * 50)
        print(f"\n🖥️  SYSTEM:")
        print(f"  CPU: {status['cpu_percent']}%")
        print(f"  RAM: {status['memory_percent']}% ({status['memory_used_gb']:.1f}GB used)")
        print(f"  Safe: {'✓' if status['safe'] else '✗'}")
        print(f"  Throttle: {status['throttle_level']}")

        print(f"\n📊 SESSION:")
        print(f"  Uptime: {session.get('uptime_human', 'N/A')}")
        print(f"  Tasks: {session.get('task_count', 0)} total, {session.get('successful_tasks', 0)} successful")
        print(f"  Success Rate: {session.get('success_rate_percent', 0):.1f}%")

        print(f"\n⚙️  QUEUE:")
        print(f"  Running: {'Yes' if queue_status['running'] else 'No'}")
        print(f"  Active Tasks: {queue_status['active_tasks']}")
        print(f"  Queue Size: {queue_status['queue_size']}")
        print("=" * 50 + "\n")

    def _emergency_stop(self):
        """Emergency stop - halt all operations"""
        print("🛑 EMERGENCY STOP INITIATED")
        governor = get_governor()
        orchestrator = get_orchestrator()

        result = governor.emergency_stop()
        orchestrator.stop(wait=False)

        print(f"Status: {result['status']}")
        print(f"Timestamp: {result['timestamp']}")

    def _minimize(self):
        """Minimize widget instead of closing"""
        if self._root:
            self._root.iconify()


# Global widget instance
_widget: Optional[FrankensteinWidget] = None

def get_widget() -> FrankensteinWidget:
    """Get or create the global widget instance"""
    global _widget
    if _widget is None:
        _widget = FrankensteinWidget()
    return _widget
