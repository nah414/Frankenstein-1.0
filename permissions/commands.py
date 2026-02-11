#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Permission Management Terminal Commands
Phase 3, Step 6: Monster Terminal commands for permissions and roles

Commands:
  permissions              Show current role and permission summary
  permissions set-role <role>     Set user role (Admin/User/Agent/ReadOnly)
  permissions check <action>      Check if action is allowed
  permissions providers           Show accessible providers
  permissions audit <days>        Show audit log for past N days
  permissions reset               Reset to default permissions
  setup                           Run interactive setup wizard

All imports are lazy-loaded. Supports all 28 quantum and classical providers.
"""

from typing import List, Callable


def handle_permissions_command(args: List[str], write_output: Callable):
    """
    Handle the 'permissions' command — manage user roles and permissions.

    Usage:
      permissions                   Show current role and permissions
      permissions set-role <role>   Set user role
      permissions check <action>    Check if action is allowed
      permissions providers         Show accessible providers
      permissions audit <days>      Show audit log
      permissions reset             Reset to defaults
    """
    if not args:
        _show_permission_summary(write_output)
        return

    subcmd = args[0].lower()

    if subcmd == "set-role":
        _handle_set_role(args[1:], write_output)
    elif subcmd == "check":
        _handle_check_permission(args[1:], write_output)
    elif subcmd == "providers":
        _handle_show_providers(write_output)
    elif subcmd == "audit":
        _handle_show_audit(args[1:], write_output)
    elif subcmd == "reset":
        _handle_reset_permissions(write_output)
    else:
        write_output(_permissions_usage())


def handle_setup_command(args: List[str], write_output: Callable):
    """
    Handle the 'setup' command — run interactive setup wizard.

    Usage:
      setup                 Run interactive setup wizard
      setup --default       Use default configuration (Admin, all enabled)
    """
    use_default = "--default" in args

    if use_default:
        _setup_default_config(write_output)
    else:
        _run_interactive_setup(write_output)


# ============================================================================
# Permission Summary
# ============================================================================

def _show_permission_summary(write_output: Callable):
    """Show current role and permission summary."""
    from permissions.permission_manager import get_permission_manager
    from permissions.rbac import get_permissions

    pm = get_permission_manager()
    role = pm.get_user_role()
    perms = get_permissions(role)

    lines = [
        "",
        "=" * 70,
        "  FRANKENSTEIN 1.0 — PERMISSION SUMMARY",
        "=" * 70,
        "",
        f"  Current Role: {role}",
        "",
        "  PERMISSIONS:",
    ]

    # Categorize permissions
    categories = {
        "Quantum Operations": [],
        "Classical Operations": [],
        "System Management": [],
        "Security & Audit": []
    }

    for perm in sorted(perms):
        if "quantum" in perm:
            categories["Quantum Operations"].append(f"    ✓ {perm}")
        elif "classical" in perm:
            categories["Classical Operations"].append(f"    ✓ {perm}")
        elif "credential" in perm or "audit" in perm:
            categories["Security & Audit"].append(f"    ✓ {perm}")
        else:
            categories["System Management"].append(f"    ✓ {perm}")

    for category, perms_list in categories.items():
        if perms_list:
            lines.append(f"\n  {category}:")
            lines.extend(perms_list)

    lines.extend([
        "",
        f"  Total Permissions: {len(perms)}",
        "",
        "  Use 'permissions providers' to see accessible providers",
        "  Use 'permissions audit 7' to see activity from past 7 days",
        "",
        "=" * 70,
        ""
    ])

    write_output("\n".join(lines))


# ============================================================================
# Set Role
# ============================================================================

def _handle_set_role(args: List[str], write_output: Callable):
    """Set user role."""
    if not args:
        write_output("\n  ❌ Usage: permissions set-role <role>\n")
        write_output("     Roles: Admin, User, Agent, ReadOnly\n\n")
        return

    role = args[0]
    valid_roles = ["Admin", "User", "Agent", "ReadOnly"]

    if role not in valid_roles:
        write_output(f"\n  ❌ Invalid role: {role}\n")
        write_output(f"     Valid roles: {', '.join(valid_roles)}\n\n")
        return

    try:
        from permissions.permission_manager import get_permission_manager
        pm = get_permission_manager()
        pm.set_user_role(role)

        write_output(f"\n  ✅ Role changed to: {role}\n")
        write_output("     Use 'permissions' to see your new permissions\n\n")
    except Exception as e:
        write_output(f"\n  ❌ Error setting role: {e}\n\n")


# ============================================================================
# Check Permission
# ============================================================================

def _handle_check_permission(args: List[str], write_output: Callable):
    """Check if a specific action is allowed."""
    if not args:
        write_output("\n  ❌ Usage: permissions check <action>\n")
        write_output("     Example: permissions check quantum_job_submit\n\n")
        return

    action = args[0]

    try:
        from permissions.permission_manager import get_permission_manager
        pm = get_permission_manager()
        role = pm.get_user_role()
        allowed = pm.check_permission(role, action)

        status = "✅ ALLOWED" if allowed else "❌ DENIED"
        write_output(f"\n  {status}\n")
        write_output(f"  Role:   {role}\n")
        write_output(f"  Action: {action}\n\n")
    except Exception as e:
        write_output(f"\n  ❌ Error checking permission: {e}\n\n")


# ============================================================================
# Show Accessible Providers
# ============================================================================

def _handle_show_providers(write_output: Callable):
    """Show providers accessible to current user."""
    from permissions.permission_manager import get_permission_manager
    from permissions.rbac import get_provider_access, get_quantum_providers, get_classical_providers

    pm = get_permission_manager()
    role = pm.get_user_role()
    accessible = get_provider_access(role)

    # Split into quantum and classical
    quantum_list = get_quantum_providers()
    classical_list = get_classical_providers()

    accessible_quantum = [p for p in quantum_list if p in accessible]
    accessible_classical = [p for p in classical_list if p in accessible]

    lines = [
        "",
        "=" * 70,
        f"  ACCESSIBLE PROVIDERS — Role: {role}",
        "=" * 70,
        "",
        f"  QUANTUM PROVIDERS ({len(accessible_quantum)}/15):"
    ]

    if accessible_quantum:
        for provider in accessible_quantum:
            lines.append(f"    ✓ {provider}")
    else:
        lines.append("    (none)")

    lines.append("")
    lines.append(f"  CLASSICAL PROVIDERS ({len(accessible_classical)}/13):")

    if accessible_classical:
        for provider in accessible_classical:
            lines.append(f"    ✓ {provider}")
    else:
        lines.append("    (none)")

    lines.extend([
        "",
        f"  Total Accessible: {len(accessible)}/28",
        "",
        "=" * 70,
        ""
    ])

    write_output("\n".join(lines))


# ============================================================================
# Show Audit Log
# ============================================================================

def _handle_show_audit(args: List[str], write_output: Callable):
    """Show audit log for past N days."""
    days = 7  # Default
    if args:
        try:
            days = int(args[0])
        except ValueError:
            write_output("\n  ❌ Invalid number of days\n\n")
            return

    try:
        from permissions.audit_logger import get_audit_logger

        logger = get_audit_logger()
        entries = logger.get_recent_actions(days=days)

        if not entries:
            write_output(f"\n  No audit log entries in the past {days} days\n\n")
            return

        lines = [
            "",
            "=" * 70,
            f"  AUDIT LOG — Past {days} Days ({len(entries)} entries)",
            "=" * 70,
            ""
        ]

        # Show most recent 50 entries
        for entry in entries[:50]:
            timestamp = entry.get("timestamp", "Unknown")
            role = entry.get("user_role", "Unknown")
            action = entry.get("action", "Unknown")
            result = entry.get("result", "Unknown")
            provider = entry.get("provider_name", "")

            result_icon = "✓" if result == "success" else "✗"
            provider_str = f" [{provider}]" if provider else ""

            lines.append(f"  {result_icon} {timestamp[:19]} | {role:10s} | {action}{provider_str}")

        if len(entries) > 50:
            lines.append(f"\n  ... and {len(entries) - 50} more entries")

        lines.extend([
            "",
            "=" * 70,
            ""
        ])

        write_output("\n".join(lines))
    except Exception as e:
        write_output(f"\n  ❌ Error reading audit log: {e}\n\n")


# ============================================================================
# Reset Permissions
# ============================================================================

def _handle_reset_permissions(write_output: Callable):
    """Reset permissions to default (Admin, all enabled)."""
    try:
        from permissions.permission_manager import get_permission_manager

        pm = get_permission_manager()
        pm.reset_to_defaults()

        write_output("\n  ✅ Permissions reset to defaults\n")
        write_output("     Role: Admin\n")
        write_output("     All providers enabled\n")
        write_output("     All workflows enabled\n\n")
    except Exception as e:
        write_output(f"\n  ❌ Error resetting permissions: {e}\n\n")


# ============================================================================
# Setup Wizard
# ============================================================================

def _run_interactive_setup(write_output: Callable):
    """Run interactive setup wizard."""
    try:
        from permissions.setup_wizard import run_setup_wizard

        write_output("\n  Starting interactive setup wizard...\n\n")
        config = run_setup_wizard()

        if config:
            write_output("\n  ✅ Setup complete!\n")
            write_output(f"     Role: {config['user_role']}\n")
            write_output("     Use 'permissions' to see your configuration\n\n")
        else:
            write_output("\n  Setup cancelled.\n\n")
    except Exception as e:
        write_output(f"\n  ❌ Error running setup: {e}\n\n")


def _setup_default_config(write_output: Callable):
    """Use default configuration."""
    try:
        from permissions.setup_wizard import SetupWizard

        wizard = SetupWizard()
        config = wizard.get_default_config()
        wizard._save_config(config)

        write_output("\n  ✅ Default configuration applied\n")
        write_output("     Role: Admin\n")
        write_output("     All 28 providers enabled\n")
        write_output("     All 6 workflows enabled\n\n")
    except Exception as e:
        write_output(f"\n  ❌ Error applying default config: {e}\n\n")


# ============================================================================
# Help Text
# ============================================================================

def _permissions_usage() -> str:
    """Return permissions command usage."""
    return """
  PERMISSIONS COMMANDS:

  permissions                   Show current role and permission summary
  permissions set-role <role>   Set user role (Admin/User/Agent/ReadOnly)
  permissions check <action>    Check if specific action is allowed
  permissions providers         Show accessible providers (quantum + classical)
  permissions audit <days>      Show audit log for past N days (default: 7)
  permissions reset             Reset to default permissions (Admin, all enabled)

  SETUP WIZARD:

  setup                         Run interactive setup wizard
  setup --default               Apply default configuration (skip wizard)

  EXAMPLES:

  permissions                   # Show current permissions
  permissions set-role User     # Switch to User role
  permissions check quantum_job_submit  # Check quantum job permission
  permissions providers         # List accessible providers
  permissions audit 30          # Show audit log for past 30 days
  setup                         # Run interactive setup

"""
