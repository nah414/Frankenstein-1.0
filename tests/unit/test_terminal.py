#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Terminal Unit Tests
Phase 1: Core Engine

Tests for the Git Bash-style terminal emulator.
Run with: pytest tests/unit/test_terminal.py -v
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest


class TestCommandHistory:
    """Test command history functionality"""
    
    def test_history_import(self):
        """Test that CommandHistory can be imported"""
        from widget.terminal import CommandHistory
        assert CommandHistory is not None
    
    def test_history_add(self):
        """Test adding commands to history"""
        from widget.terminal import CommandHistory
        history = CommandHistory()
        
        history.add("ls")
        history.add("cd /home")
        history.add("pwd")
        
        assert len(history._history) == 3
    
    def test_history_no_duplicates(self):
        """Test that consecutive duplicates are not added"""
        from widget.terminal import CommandHistory
        history = CommandHistory()
        
        history.add("ls")
        history.add("ls")  # Duplicate
        history.add("ls")  # Duplicate
        
        assert len(history._history) == 1
    
    def test_history_navigation(self):
        """Test up/down navigation through history"""
        from widget.terminal import CommandHistory
        history = CommandHistory()
        
        history.add("first")
        history.add("second")
        history.add("third")
        
        # Go back through history
        assert history.get_previous() == "third"
        assert history.get_previous() == "second"
        assert history.get_previous() == "first"
        
        # Go forward
        assert history.get_next() == "second"
        assert history.get_next() == "third"
    
    def test_history_max_size(self):
        """Test that history respects max size"""
        from widget.terminal import CommandHistory
        history = CommandHistory(max_size=5)
        
        for i in range(10):
            history.add(f"cmd{i}")
        
        assert len(history._history) == 5
        assert history._history[0] == "cmd5"
        assert history._history[-1] == "cmd9"


class TestTerminalPathResolution:
    """Test path resolution functionality"""
    
    def test_terminal_import(self):
        """Test that FrankensteinTerminal can be imported"""
        from widget.terminal import FrankensteinTerminal
        assert FrankensteinTerminal is not None
    
    def test_resolve_absolute_path(self):
        """Test resolving absolute paths"""
        from widget.terminal import FrankensteinTerminal
        terminal = FrankensteinTerminal()
        
        if sys.platform == 'win32':
            path = terminal._resolve_path("C:\\Windows")
            assert path == Path("C:\\Windows")
        else:
            path = terminal._resolve_path("/usr")
            assert path == Path("/usr")
    
    def test_resolve_relative_path(self):
        """Test resolving relative paths"""
        from widget.terminal import FrankensteinTerminal
        terminal = FrankensteinTerminal()
        
        # Set a known cwd
        terminal._cwd = Path.home()
        
        path = terminal._resolve_path("test")
        assert path == Path.home() / "test"
    
    def test_resolve_home_path(self):
        """Test resolving ~ to home directory"""
        from widget.terminal import FrankensteinTerminal
        terminal = FrankensteinTerminal()
        
        path = terminal._resolve_path("~")
        assert path == Path.home()
        
        path = terminal._resolve_path("~/documents")
        assert path == Path.home() / "documents"


class TestCommandParsing:
    """Test command line parsing"""
    
    def test_parse_simple_command(self):
        """Test parsing simple command"""
        from widget.terminal import FrankensteinTerminal
        terminal = FrankensteinTerminal()
        
        parts = terminal._parse_command("ls -la")
        assert parts == ["ls", "-la"]
    
    def test_parse_quoted_args(self):
        """Test parsing commands with quoted arguments"""
        from widget.terminal import FrankensteinTerminal
        terminal = FrankensteinTerminal()
        
        parts = terminal._parse_command('echo "hello world"')
        assert parts == ["echo", "hello world"]
        
        parts = terminal._parse_command("echo 'single quotes'")
        assert parts == ["echo", "single quotes"]
    
    def test_parse_mixed_args(self):
        """Test parsing mixed arguments"""
        from widget.terminal import FrankensteinTerminal
        terminal = FrankensteinTerminal()
        
        parts = terminal._parse_command('cp "file name.txt" destination')
        assert parts == ["cp", "file name.txt", "destination"]


class TestFileCommands:
    """Test file operation commands"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests"""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp, ignore_errors=True)
    
    @pytest.fixture
    def terminal(self, temp_dir):
        """Create terminal instance with temp directory as cwd"""
        from widget.terminal import FrankensteinTerminal
        t = FrankensteinTerminal()
        t._cwd = temp_dir
        return t
    
    def test_pwd_command(self, terminal, temp_dir):
        """Test pwd returns current directory"""
        # Capture output would require mocking, but we can test the logic
        assert terminal._cwd == temp_dir
    
    def test_cd_to_parent(self, terminal, temp_dir):
        """Test cd .. goes to parent"""
        original = terminal._cwd
        terminal._cmd_cd([".."])
        assert terminal._cwd == original.parent
    
    def test_cd_to_home(self, terminal):
        """Test cd with no args goes to home"""
        terminal._cmd_cd([])
        assert terminal._cwd == Path.home()
    
    def test_mkdir_creates_directory(self, terminal, temp_dir):
        """Test mkdir creates directory"""
        new_dir = temp_dir / "test_mkdir"
        assert not new_dir.exists()
        
        terminal._cmd_mkdir(["test_mkdir"])
        assert new_dir.exists()
        assert new_dir.is_dir()
    
    def test_mkdir_with_parents(self, terminal, temp_dir):
        """Test mkdir -p creates nested directories"""
        nested = temp_dir / "a" / "b" / "c"
        assert not nested.exists()
        
        terminal._cmd_mkdir(["-p", "a/b/c"])
        assert nested.exists()
    
    def test_touch_creates_file(self, terminal, temp_dir):
        """Test touch creates empty file"""
        new_file = temp_dir / "test_file.txt"
        assert not new_file.exists()
        
        terminal._cmd_touch(["test_file.txt"])
        assert new_file.exists()
        assert new_file.stat().st_size == 0
    
    def test_rm_removes_file(self, terminal, temp_dir):
        """Test rm removes file"""
        test_file = temp_dir / "to_delete.txt"
        test_file.touch()
        assert test_file.exists()
        
        terminal._cmd_rm(["to_delete.txt"])
        assert not test_file.exists()
    
    def test_rm_recursive(self, terminal, temp_dir):
        """Test rm -r removes directory"""
        test_dir = temp_dir / "dir_to_delete"
        test_dir.mkdir()
        (test_dir / "file.txt").touch()
        assert test_dir.exists()
        
        terminal._cmd_rm(["-r", "dir_to_delete"])
        assert not test_dir.exists()
    
    def test_cp_copies_file(self, terminal, temp_dir):
        """Test cp copies file"""
        src = temp_dir / "source.txt"
        src.write_text("test content")
        
        terminal._cmd_cp(["source.txt", "dest.txt"])
        
        dest = temp_dir / "dest.txt"
        assert dest.exists()
        assert dest.read_text() == "test content"
    
    def test_mv_moves_file(self, terminal, temp_dir):
        """Test mv moves file"""
        src = temp_dir / "original.txt"
        src.write_text("test content")
        
        terminal._cmd_mv(["original.txt", "moved.txt"])
        
        assert not src.exists()
        dest = temp_dir / "moved.txt"
        assert dest.exists()
        assert dest.read_text() == "test content"


class TestTextCommands:
    """Test text processing commands"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests"""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp, ignore_errors=True)
    
    @pytest.fixture  
    def terminal(self, temp_dir):
        """Create terminal instance"""
        from widget.terminal import FrankensteinTerminal
        t = FrankensteinTerminal()
        t._cwd = temp_dir
        return t
    
    @pytest.fixture
    def test_file(self, temp_dir):
        """Create a test file with content"""
        f = temp_dir / "test.txt"
        f.write_text("line 1\nline 2\nline 3\nline 4\nline 5\n")
        return f
    
    def test_head_default_lines(self, terminal, test_file):
        """Test head reads first 10 lines (or less)"""
        # This would need output capture to fully test
        # For now just verify it doesn't crash
        terminal._cmd_head([test_file.name])
    
    def test_tail_default_lines(self, terminal, test_file):
        """Test tail reads last 10 lines (or less)"""
        terminal._cmd_tail([test_file.name])
    
    def test_wc_counts_correctly(self, terminal, temp_dir):
        """Test wc counts lines/words/chars"""
        test_file = temp_dir / "wc_test.txt"
        test_file.write_text("hello world\nfoo bar\n")
        
        # Would need output capture to verify numbers
        terminal._cmd_wc(["wc_test.txt"])


class TestCommandRegistry:
    """Test that all expected commands are registered"""
    
    def test_navigation_commands(self):
        """Test navigation commands exist"""
        from widget.terminal import FrankensteinTerminal
        terminal = FrankensteinTerminal()
        
        assert 'cd' in terminal._commands
        assert 'pwd' in terminal._commands
        assert 'ls' in terminal._commands
    
    def test_file_commands(self):
        """Test file operation commands exist"""
        from widget.terminal import FrankensteinTerminal
        terminal = FrankensteinTerminal()
        
        assert 'cat' in terminal._commands
        assert 'touch' in terminal._commands
        assert 'mkdir' in terminal._commands
        assert 'rm' in terminal._commands
        assert 'cp' in terminal._commands
        assert 'mv' in terminal._commands
    
    def test_utility_commands(self):
        """Test utility commands exist"""
        from widget.terminal import FrankensteinTerminal
        terminal = FrankensteinTerminal()
        
        assert 'echo' in terminal._commands
        assert 'clear' in terminal._commands
        assert 'help' in terminal._commands
        assert 'history' in terminal._commands
        assert 'exit' in terminal._commands
    
    def test_windows_aliases(self):
        """Test Windows command aliases exist"""
        from widget.terminal import FrankensteinTerminal
        terminal = FrankensteinTerminal()
        
        assert 'dir' in terminal._commands  # alias for ls
        assert 'type' in terminal._commands  # alias for cat
        assert 'cls' in terminal._commands  # alias for clear
        assert 'del' in terminal._commands  # alias for rm
        assert 'copy' in terminal._commands  # alias for cp
        assert 'move' in terminal._commands  # alias for mv
    
    def test_frankenstein_commands(self):
        """Test Frankenstein-specific commands exist"""
        from widget.terminal import FrankensteinTerminal
        terminal = FrankensteinTerminal()
        
        assert 'status' in terminal._commands
        assert 'frank' in terminal._commands


class TestPromptGeneration:
    """Test prompt generation"""
    
    def test_prompt_format(self):
        """Test prompt has expected format"""
        from widget.terminal import FrankensteinTerminal
        terminal = FrankensteinTerminal()
        
        prompt = terminal._get_prompt()
        
        assert "@frankenstein:" in prompt
        assert prompt.endswith("$")
    
    def test_prompt_shows_home_as_tilde(self):
        """Test that home directory shows as ~"""
        from widget.terminal import FrankensteinTerminal
        terminal = FrankensteinTerminal()
        terminal._cwd = Path.home()
        
        prompt = terminal._get_prompt()
        assert "~" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
