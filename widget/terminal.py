#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Terminal Widget
Phase 1: Core Engine

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
        }
    
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
        self._root.title("🧟 FRANKENSTEIN Terminal")
        self._root.geometry("700x500+100+100")
        self._root.minsize(500, 300)
        self._root.attributes("-topmost", True)
        
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
        """Build the terminal UI"""
        # Configure grid
        self._root.grid_columnconfigure(0, weight=1)
        self._root.grid_rowconfigure(0, weight=0)  # Header
        self._root.grid_rowconfigure(1, weight=1)  # Output
        self._root.grid_rowconfigure(2, weight=0)  # Input
        
        # Header frame
        header = ctk.CTkFrame(self._root, height=35, fg_color="#1a1a2e")
        header.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        header.grid_columnconfigure(1, weight=1)
        
        title = ctk.CTkLabel(
            header,
            text="🧟 FRANKENSTEIN 1.0 Terminal",
            font=("Consolas", 14, "bold"),
            text_color="#00ff88"
        )
        title.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # Status indicator
        self._status_label = ctk.CTkLabel(
            header,
            text="● READY",
            font=("Consolas", 11),
            text_color="#00ff88"
        )
        self._status_label.grid(row=0, column=2, padx=10, pady=5, sticky="e")
        
        # Output text area (scrollable)
        self._output_text = ctk.CTkTextbox(
            self._root,
            font=("Consolas", 11),
            fg_color="#0d1117",
            text_color="#c9d1d9",
            wrap="word",
            state="normal"
        )
        self._output_text.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        # Make output area read-only but allow selection/copy
        self._output_text.bind("<Key>", lambda e: "break" if e.keysym not in ["c", "C"] or not (e.state & 0x4) else None)
        self._output_text.bind("<Button-1>", lambda e: self._output_text.focus_set())
        
        # Right-click context menu for output
        self._setup_context_menu()
        
        # Input frame
        input_frame = ctk.CTkFrame(self._root, height=40, fg_color="#161b22")
        input_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        input_frame.grid_columnconfigure(1, weight=1)
        
        # Prompt label
        self._prompt_label = ctk.CTkLabel(
            input_frame,
            text=self._get_prompt(),
            font=("Consolas", 11, "bold"),
            text_color="#58a6ff"
        )
        self._prompt_label.grid(row=0, column=0, padx=(10, 5), pady=8, sticky="w")
        
        # Command input entry
        self._input_entry = ctk.CTkEntry(
            input_frame,
            font=("Consolas", 11),
            fg_color="#0d1117",
            text_color="#c9d1d9",
            border_color="#30363d",
            placeholder_text="Enter command...",
            height=30
        )
        self._input_entry.grid(row=0, column=1, padx=(0, 10), pady=8, sticky="ew")
        
        # Bind events for input
        self._input_entry.bind("<Return>", self._on_enter)
        self._input_entry.bind("<Up>", self._on_up_arrow)
        self._input_entry.bind("<Down>", self._on_down_arrow)
        self._input_entry.bind("<Tab>", self._on_tab_complete)
        self._input_entry.bind("<Escape>", lambda e: self._input_entry.delete(0, "end"))
        
        # Right-click for input entry
        self._input_entry.bind("<Button-3>", self._show_input_context_menu)
        
        # Robust focus handling to prevent "disappearing" input issue
        self._input_entry.bind("<FocusOut>", self._refocus_input)
        
        # Re-focus input when clicking anywhere in the window
        self._root.bind("<Button-1>", self._on_window_click)
        
        # Ensure window stays active on key press
        self._root.bind("<Key>", self._on_any_key)
        
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
        
        self._output_text.bind("<Button-3>", self._show_output_context_menu)
        
        # Input context menu (copy, cut, paste)
        self._input_menu = tk.Menu(self._root, tearoff=0, bg="#21262d", fg="#c9d1d9",
                                    activebackground="#30363d", activeforeground="#ffffff")
        self._input_menu.add_command(label="✂️ Cut", command=self._cut_input)
        self._input_menu.add_command(label="📋 Copy", command=self._copy_input)
        self._input_menu.add_command(label="📥 Paste", command=self._paste_input)
        self._input_menu.add_separator()
        self._input_menu.add_command(label="🗑️ Clear", command=lambda: self._input_entry.delete(0, "end"))
    
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
            if self._input_entry.selection_present():
                selected = self._input_entry.selection_get()
                self._root.clipboard_clear()
                self._root.clipboard_append(selected)
                self._input_entry.delete("sel.first", "sel.last")
        except Exception:
            pass
    
    def _copy_input(self):
        """Copy selected text from input"""
        try:
            if self._input_entry.selection_present():
                selected = self._input_entry.selection_get()
                self._root.clipboard_clear()
                self._root.clipboard_append(selected)
        except Exception:
            pass
    
    def _paste_input(self):
        """Paste text into input"""
        try:
            text = self._root.clipboard_get()
            # Remove newlines for single-line input
            text = text.replace('\n', ' ').replace('\r', '')
            self._input_entry.insert("insert", text)
        except Exception:
            pass
    
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
        """Handle Enter key - execute command"""
        command = self._input_entry.get().strip()
        self._input_entry.delete(0, "end")
        
        if command:
            self._history.add(command)
            self._execute_command(command)
        
        self._update_prompt()
        return "break"
    
    def _on_up_arrow(self, event=None):
        """Handle Up arrow - previous command"""
        prev_cmd = self._history.get_previous()
        if prev_cmd is not None:
            self._input_entry.delete(0, "end")
            self._input_entry.insert(0, prev_cmd)
        return "break"
    
    def _on_down_arrow(self, event=None):
        """Handle Down arrow - next command"""
        next_cmd = self._history.get_next()
        if next_cmd is not None:
            self._input_entry.delete(0, "end")
            self._input_entry.insert(0, next_cmd)
        return "break"
    
    def _on_tab_complete(self, event=None):
        """Handle Tab - basic path completion"""
        current = self._input_entry.get()
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
                    self._input_entry.delete(0, "end")
                    self._input_entry.insert(0, " ".join(parts))
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
    
    def _show_welcome(self):
        """Display welcome message like Git Bash"""
        welcome = f"""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   ⚡ FRANKENSTEIN 1.0 - Phase 1: Core Engine                    ║
║                                                                  ║
║   "Frankenstein, here to serve science."                        ║
║                                                                  ║
║   Git Bash-style Terminal Emulator for Windows 10+              ║
║   Type 'help' for available commands                            ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝

Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Working directory: {self._cwd}

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
        # Show the command with prompt
        self._write_output(f"{self._get_prompt()} {command_line}\n")
        
        # Parse command and arguments
        parts = self._parse_command(command_line)
        if not parts:
            return
        
        cmd = parts[0].lower()
        args = parts[1:]
        
        # Check if it's a built-in command
        if cmd in self._commands:
            try:
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
            self._status_label.configure(text="● RUNNING", text_color="#ffcc00")
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
            
            self._status_label.configure(text="● READY", text_color="#00ff88")
            
        except subprocess.TimeoutExpired:
            self._write_error("Command timed out after 30 seconds")
            self._status_label.configure(text="● READY", text_color="#00ff88")
        except Exception as e:
            self._write_error(f"Failed to execute: {e}")
            self._status_label.configure(text="● READY", text_color="#00ff88")

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
            from core import get_governor, get_memory
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
            self._write_output("Phase 1: Core Engine\n")
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
            }
            if cmd in help_text:
                self._write_output(f"\n{help_text[cmd]}\n\n")
            else:
                self._write_error(f"help: no help for '{cmd}'")
            return
        
        help_msg = """
╔══════════════════════════════════════════════════════════════════╗
║                    FRANKENSTEIN TERMINAL HELP                    ║
╚══════════════════════════════════════════════════════════════════╝

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
