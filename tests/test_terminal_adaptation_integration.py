"""
Test Suite for Terminal-Adaptation Integration

Verifies that adaptation commands are properly integrated
into the Frankenstein Terminal.
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_terminal_imports():
    """Test that terminal can import adaptation modules."""
    try:
        from widget.terminal import FrankensteinTerminal
        from agents.adaptation import get_adaptation_commands
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")


def test_adaptation_commands_in_registry():
    """Test that adaptation commands are registered in terminal."""
    from widget.terminal import FrankensteinTerminal

    terminal = FrankensteinTerminal()

    # Check all adaptation commands are registered
    adaptation_commands = [
        'adapt-status',
        'adapt-patterns',
        'adapt-performance',
        'adapt-insights',
        'adapt-recommend',
        'adapt-history',
        'adapt-dashboard'
    ]

    for cmd in adaptation_commands:
        assert cmd in terminal._commands, f"Command {cmd} not registered"


def test_adaptation_command_handlers_exist():
    """Test that all command handlers are implemented."""
    from widget.terminal import FrankensteinTerminal

    terminal = FrankensteinTerminal()

    # Check handler methods exist
    assert hasattr(terminal, '_cmd_adapt_status')
    assert hasattr(terminal, '_cmd_adapt_patterns')
    assert hasattr(terminal, '_cmd_adapt_performance')
    assert hasattr(terminal, '_cmd_adapt_insights')
    assert hasattr(terminal, '_cmd_adapt_recommend')
    assert hasattr(terminal, '_cmd_adapt_history')
    assert hasattr(terminal, '_cmd_adapt_dashboard')
    assert hasattr(terminal, '_ensure_adaptation_commands')


def test_ensure_adaptation_commands():
    """Test lazy-loading of adaptation commands."""
    from widget.terminal import FrankensteinTerminal

    terminal = FrankensteinTerminal()

    # Initially None
    assert terminal._adaptation_commands is None

    # After ensuring, should be loaded
    commands = terminal._ensure_adaptation_commands()
    assert commands is not None
    assert terminal._adaptation_commands is not None


def test_adaptation_commands_singleton():
    """Test that adaptation commands are singleton."""
    from widget.terminal import FrankensteinTerminal

    terminal = FrankensteinTerminal()

    # Get commands twice
    cmd1 = terminal._ensure_adaptation_commands()
    cmd2 = terminal._ensure_adaptation_commands()

    # Should be same instance
    assert cmd1 is cmd2


def test_adaptation_commands_have_required_methods():
    """Test that adaptation commands have all required methods."""
    from widget.terminal import FrankensteinTerminal

    terminal = FrankensteinTerminal()
    commands = terminal._ensure_adaptation_commands()

    # Check all command methods exist
    assert hasattr(commands, 'cmd_adapt_status')
    assert hasattr(commands, 'cmd_adapt_patterns')
    assert hasattr(commands, 'cmd_adapt_performance')
    assert hasattr(commands, 'cmd_adapt_insights')
    assert hasattr(commands, 'cmd_adapt_recommend')
    assert hasattr(commands, 'cmd_adapt_history')


def test_terminal_help_includes_adaptation():
    """Test that help text includes adaptation commands."""
    from widget.terminal import FrankensteinTerminal

    terminal = FrankensteinTerminal()

    # Mock output capture
    output_lines = []

    def mock_write(text):
        output_lines.append(text)

    terminal._write_output = mock_write

    # Call help
    terminal._cmd_help([])

    # Join all output
    full_output = '\n'.join(output_lines)

    # Check for adaptation section
    assert 'REAL-TIME ADAPTATION' in full_output
    assert 'adapt-status' in full_output
    assert 'adapt-dashboard' in full_output
    assert 'EMA learning' in full_output or 'FEATURES' in full_output


def test_terminal_help_adaptation_commands():
    """Test help for individual adaptation commands."""
    from widget.terminal import FrankensteinTerminal

    terminal = FrankensteinTerminal()

    # Mock output capture
    output_lines = []

    def mock_write(text):
        output_lines.append(text)

    terminal._write_output = mock_write

    # Test help for each command
    commands_to_test = [
        'adapt-status',
        'adapt-patterns',
        'adapt-performance',
        'adapt-dashboard'
    ]

    for cmd in commands_to_test:
        output_lines.clear()
        terminal._cmd_help([cmd])

        full_output = '\n'.join(output_lines)
        assert len(full_output) > 0, f"No help text for {cmd}"
        assert cmd in full_output.lower() or 'adapt' in full_output.lower()


def test_terminal_integration_no_errors():
    """Test that terminal can be created without errors."""
    from widget.terminal import FrankensteinTerminal

    # Should not raise any exceptions
    terminal = FrankensteinTerminal()

    assert terminal is not None
    assert terminal._adaptation_commands is None  # Lazy-loaded
    assert '_ensure_adaptation_commands' in dir(terminal)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
