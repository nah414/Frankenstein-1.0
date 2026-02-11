#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Automation Terminal Commands
Phase 3, Step 6: Monster Terminal commands for automation and scheduling

Commands:
  automation               Show automation status
  automation start         Start all enabled workflows
  automation stop          Stop all workflows
  automation status        Show workflow execution status
  automation run <name>    Run specific workflow immediately
  automation enable <name> Enable a workflow
  automation disable <name> Disable a workflow
  automation consent <name> Grant termination consent for workflow
  scheduler                Show scheduler status
  scheduler tasks          List all scheduled tasks
  scheduler pause <id>     Pause a scheduled task
  scheduler resume <id>    Resume a paused task

All imports are lazy-loaded. Supports 6 automated workflows across 28 providers.
"""

from typing import List, Callable


def handle_automation_command(args: List[str], write_output: Callable):
    """
    Handle the 'automation' command — manage automated workflows.

    Usage:
      automation                Show automation status
      automation start          Start all enabled workflows
      automation stop           Stop all workflows
      automation status         Show detailed workflow status
      automation run <name>     Run specific workflow
      automation enable <name>  Enable a workflow
      automation disable <name> Disable a workflow
      automation consent <name> Grant termination consent
    """
    if not args:
        _show_automation_summary(write_output)
        return

    subcmd = args[0].lower()

    if subcmd == "start":
        _handle_start_automation(write_output)
    elif subcmd == "stop":
        _handle_stop_automation(write_output)
    elif subcmd == "status":
        _handle_automation_status(write_output)
    elif subcmd == "run":
        _handle_run_workflow(args[1:], write_output)
    elif subcmd == "enable":
        _handle_enable_workflow(args[1:], write_output)
    elif subcmd == "disable":
        _handle_disable_workflow(args[1:], write_output)
    elif subcmd == "consent":
        _handle_grant_consent(args[1:], write_output)
    elif subcmd == "revoke":
        _handle_revoke_consent(args[1:], write_output)
    else:
        write_output(_automation_usage())


def handle_scheduler_command(args: List[str], write_output: Callable):
    """
    Handle the 'scheduler' command — manage task scheduler.

    Usage:
      scheduler               Show scheduler status
      scheduler tasks         List all scheduled tasks
      scheduler pause <id>    Pause a task
      scheduler resume <id>   Resume a task
      scheduler stop          Stop scheduler
    """
    if not args:
        _show_scheduler_summary(write_output)
        return

    subcmd = args[0].lower()

    if subcmd == "tasks":
        _handle_list_tasks(write_output)
    elif subcmd == "pause":
        _handle_pause_task(args[1:], write_output)
    elif subcmd == "resume":
        _handle_resume_task(args[1:], write_output)
    elif subcmd == "stop":
        _handle_stop_scheduler(write_output)
    else:
        write_output(_scheduler_usage())


# ============================================================================
# Automation Summary
# ============================================================================

def _show_automation_summary(write_output: Callable):
    """Show automation status summary."""
    from automation.workflow_engine import get_workflow_engine
    from permissions.permission_manager import get_permission_manager

    engine = get_workflow_engine()
    pm = get_permission_manager()
    config = pm.config

    automation_enabled = config.get("automation_enabled", False)
    workflows = config.get("automated_workflows", {})

    lines = [
        "",
        "=" * 70,
        "  FRANKENSTEIN 1.0 — AUTOMATION STATUS",
        "=" * 70,
        "",
        f"  Automation: {'ENABLED' if automation_enabled else 'DISABLED'}",
        "",
        "  WORKFLOWS:",
        ""
    ]

    workflow_info = [
        ("optimize_quantum_queue", "Quantum Job Queue Optimization", "15 quantum providers"),
        ("optimize_classical_queue", "Classical Compute Queue Optimization", "13 classical providers"),
        ("check_credential_expiry", "Credential Expiry Warnings", "All 28 providers"),
        ("generate_resource_report", "Resource Usage Reporting", "All 28 providers"),
        ("monitor_provider_health", "Provider Health Monitoring", "All 28 providers"),
        ("auto_tune_hardware", "Hardware Optimization Auto-Tuning", "13 classical providers"),
    ]

    for workflow_id, name, scope in workflow_info:
        enabled = workflows.get(workflow_id, False)
        status_icon = "🟢" if enabled else "⚪"
        consent_status = "✓" if engine.user_consent_to_terminate.get(workflow_id, False) else "○"

        lines.append(f"  {status_icon} {name}")
        lines.append(f"     Scope: {scope}")
        lines.append(f"     Consent: {consent_status} (termination on resource limits)")
        lines.append("")

    lines.extend([
        "  Resource Limits:",
        "    CPU:  80% max",
        "    RAM:  75% max",
        "",
        "  Use 'automation start' to begin workflows",
        "  Use 'automation run <name>' to run a specific workflow",
        "",
        "=" * 70,
        ""
    ])

    write_output("\n".join(lines))


# ============================================================================
# Start/Stop Automation
# ============================================================================

def _handle_start_automation(write_output: Callable):
    """Start all enabled workflows."""
    from automation.scheduler import get_scheduler
    from permissions.permission_manager import get_permission_manager

    try:
        pm = get_permission_manager()
        config = pm.config

        if not config.get("automation_enabled", False):
            write_output("\n  ⚠️  Automation is disabled in configuration\n")
            write_output("     Run 'setup' to enable automation\n\n")
            return

        scheduler = get_scheduler()
        scheduler.start()

        write_output("\n  ✅ Automation started\n")
        write_output("     All enabled workflows are now running\n")
        write_output("     Use 'automation status' to monitor execution\n\n")
    except Exception as e:
        write_output(f"\n  ❌ Error starting automation: {e}\n\n")


def _handle_stop_automation(write_output: Callable):
    """Stop all workflows."""
    from automation.scheduler import get_scheduler

    try:
        scheduler = get_scheduler()
        scheduler.stop()

        write_output("\n  ✅ Automation stopped\n")
        write_output("     All workflows have been paused\n\n")
    except Exception as e:
        write_output(f"\n  ❌ Error stopping automation: {e}\n\n")


# ============================================================================
# Workflow Status
# ============================================================================

def _handle_automation_status(write_output: Callable):
    """Show detailed workflow execution status."""
    from automation.scheduler import get_scheduler

    try:
        scheduler = get_scheduler()
        tasks = scheduler.get_active_tasks()

        lines = [
            "",
            "=" * 70,
            f"  WORKFLOW EXECUTION STATUS — {len(tasks)} Active Tasks",
            "=" * 70,
            ""
        ]

        if not tasks:
            lines.append("  No active tasks")
        else:
            for task in tasks:
                status_icon = {
                    "pending": "⏳",
                    "running": "🔄",
                    "completed": "✅",
                    "failed": "❌",
                    "paused": "⏸️",
                    "skipped": "⏭️"
                }.get(task.status.value, "❓")

                lines.append(f"  {status_icon} {task.task_id}")
                lines.append(f"     Status: {task.status.value}")
                lines.append(f"     Type: {task.schedule_type.value}")
                lines.append(f"     Run Count: {task.run_count}")
                if task.error_count > 0:
                    lines.append(f"     Errors: {task.error_count}")
                if task.last_run:
                    lines.append(f"     Last Run: {task.last_run}")
                lines.append("")

        lines.extend([
            "=" * 70,
            ""
        ])

        write_output("\n".join(lines))
    except Exception as e:
        write_output(f"\n  ❌ Error getting workflow status: {e}\n\n")


# ============================================================================
# Run Specific Workflow
# ============================================================================

def _handle_run_workflow(args: List[str], write_output: Callable):
    """Run a specific workflow immediately."""
    if not args:
        write_output("\n  ❌ Usage: automation run <workflow_name>\n")
        write_output("     Workflows: quantum_queue, classical_queue, credentials,\n")
        write_output("                resource_report, health_monitor, hardware_tune\n\n")
        return

    workflow_map = {
        "quantum_queue": "optimize_quantum_queue",
        "classical_queue": "optimize_classical_queue",
        "credentials": "check_credential_expiry",
        "resource_report": "generate_resource_report",
        "health_monitor": "monitor_provider_health",
        "hardware_tune": "auto_tune_hardware"
    }

    workflow_name = args[0].lower()
    if workflow_name not in workflow_map:
        write_output(f"\n  ❌ Unknown workflow: {workflow_name}\n\n")
        return

    try:
        from automation.workflow_engine import get_workflow_engine

        engine = get_workflow_engine()
        method_name = workflow_map[workflow_name]
        method = getattr(engine, method_name)

        write_output(f"\n  🔄 Running {workflow_name}...\n")
        result = method()

        status = result.get("status", "unknown")
        if status == "success":
            write_output(f"  ✅ {workflow_name} completed successfully\n")
            if "providers_checked" in result:
                write_output(f"     Providers checked: {result['providers_checked']}\n")
        elif status == "denied":
            write_output(f"  ❌ Permission denied: {result.get('reason', 'Unknown')}\n")
        elif status == "paused":
            write_output(f"  ⏸️  Workflow paused: {result.get('reason', 'Unknown')}\n")
        else:
            write_output(f"  ⚠️  Status: {status}\n")

        write_output("\n")
    except Exception as e:
        write_output(f"\n  ❌ Error running workflow: {e}\n\n")


# ============================================================================
# Enable/Disable Workflow
# ============================================================================

def _handle_enable_workflow(args: List[str], write_output: Callable):
    """Enable a workflow."""
    if not args:
        write_output("\n  ❌ Usage: automation enable <workflow_name>\n\n")
        return

    # This would update the configuration
    write_output(f"\n  ℹ️  Workflow enable/disable configuration\n")
    write_output("     Run 'setup' to modify workflow settings\n\n")


def _handle_disable_workflow(args: List[str], write_output: Callable):
    """Disable a workflow."""
    if not args:
        write_output("\n  ❌ Usage: automation disable <workflow_name>\n\n")
        return

    write_output(f"\n  ℹ️  Workflow enable/disable configuration\n")
    write_output("     Run 'setup' to modify workflow settings\n\n")


# ============================================================================
# Grant/Revoke Termination Consent
# ============================================================================

def _handle_grant_consent(args: List[str], write_output: Callable):
    """Grant termination consent for a workflow."""
    if not args:
        write_output("\n  ❌ Usage: automation consent <workflow_name>\n\n")
        return

    workflow_name = args[0]

    try:
        from automation.workflow_engine import get_workflow_engine

        engine = get_workflow_engine()
        engine.grant_termination_consent(workflow_name)

        write_output(f"\n  ✅ Termination consent granted for: {workflow_name}\n")
        write_output("     Workflow can now self-terminate if resources approach limits\n\n")
    except Exception as e:
        write_output(f"\n  ❌ Error granting consent: {e}\n\n")


def _handle_revoke_consent(args: List[str], write_output: Callable):
    """Revoke termination consent for a workflow."""
    if not args:
        write_output("\n  ❌ Usage: automation revoke <workflow_name>\n\n")
        return

    workflow_name = args[0]

    try:
        from automation.workflow_engine import get_workflow_engine

        engine = get_workflow_engine()
        engine.revoke_termination_consent(workflow_name)

        write_output(f"\n  ✅ Termination consent revoked for: {workflow_name}\n")
        write_output("     Workflow will warn and ask permission before terminating\n\n")
    except Exception as e:
        write_output(f"\n  ❌ Error revoking consent: {e}\n\n")


# ============================================================================
# Scheduler Commands
# ============================================================================

def _show_scheduler_summary(write_output: Callable):
    """Show scheduler status summary."""
    from automation.scheduler import get_scheduler

    try:
        scheduler = get_scheduler()
        running = scheduler.is_running()
        all_tasks = scheduler.get_all_tasks()
        active_tasks = scheduler.get_active_tasks()

        lines = [
            "",
            "=" * 70,
            "  TASK SCHEDULER STATUS",
            "=" * 70,
            "",
            f"  Scheduler: {'RUNNING' if running else 'STOPPED'}",
            f"  Total Tasks: {len(all_tasks)}",
            f"  Active Tasks: {len(active_tasks)}",
            "",
            "  Resource Limits:",
            "    CPU: 80% max",
            "    RAM: 75% max",
            "    Max Concurrent Tasks: 5",
            "",
            "  Use 'scheduler tasks' to list all tasks",
            "",
            "=" * 70,
            ""
        ]

        write_output("\n".join(lines))
    except Exception as e:
        write_output(f"\n  ❌ Error getting scheduler status: {e}\n\n")


def _handle_list_tasks(write_output: Callable):
    """List all scheduled tasks."""
    from automation.scheduler import get_scheduler

    try:
        scheduler = get_scheduler()
        tasks = scheduler.get_all_tasks()

        lines = [
            "",
            "=" * 70,
            f"  SCHEDULED TASKS ({len(tasks)} total)",
            "=" * 70,
            ""
        ]

        if not tasks:
            lines.append("  No scheduled tasks")
        else:
            for task in tasks:
                status_icon = {
                    "pending": "⏳",
                    "running": "🔄",
                    "completed": "✅",
                    "failed": "❌",
                    "paused": "⏸️",
                    "skipped": "⏭️"
                }.get(task.status.value, "❓")

                lines.append(f"  {status_icon} {task.task_id}")
                lines.append(f"     Type: {task.schedule_type.value}")
                if task.schedule_type.value == "recurring":
                    lines.append(f"     Interval: {task.interval_seconds}s")
                lines.append(f"     Run Count: {task.run_count}")
                lines.append(f"     Status: {task.status.value}")
                if task.target_providers:
                    lines.append(f"     Providers: {', '.join(task.target_providers[:3])}{' ...' if len(task.target_providers) > 3 else ''}")
                lines.append("")

        lines.extend([
            "=" * 70,
            ""
        ])

        write_output("\n".join(lines))
    except Exception as e:
        write_output(f"\n  ❌ Error listing tasks: {e}\n\n")


def _handle_pause_task(args: List[str], write_output: Callable):
    """Pause a scheduled task."""
    if not args:
        write_output("\n  ❌ Usage: scheduler pause <task_id>\n\n")
        return

    task_id = args[0]

    try:
        from automation.scheduler import get_scheduler

        scheduler = get_scheduler()
        scheduler.pause_task(task_id)

        write_output(f"\n  ⏸️  Task paused: {task_id}\n\n")
    except KeyError:
        write_output(f"\n  ❌ Task not found: {task_id}\n\n")
    except Exception as e:
        write_output(f"\n  ❌ Error pausing task: {e}\n\n")


def _handle_resume_task(args: List[str], write_output: Callable):
    """Resume a paused task."""
    if not args:
        write_output("\n  ❌ Usage: scheduler resume <task_id>\n\n")
        return

    task_id = args[0]

    try:
        from automation.scheduler import get_scheduler

        scheduler = get_scheduler()
        scheduler.resume_task(task_id)

        write_output(f"\n  ▶️  Task resumed: {task_id}\n\n")
    except KeyError:
        write_output(f"\n  ❌ Task not found: {task_id}\n\n")
    except Exception as e:
        write_output(f"\n  ❌ Error resuming task: {e}\n\n")


def _handle_stop_scheduler(write_output: Callable):
    """Stop the task scheduler."""
    from automation.scheduler import get_scheduler

    try:
        scheduler = get_scheduler()
        scheduler.stop()

        write_output("\n  ⏹️  Scheduler stopped\n\n")
    except Exception as e:
        write_output(f"\n  ❌ Error stopping scheduler: {e}\n\n")


# ============================================================================
# Help Text
# ============================================================================

def _automation_usage() -> str:
    """Return automation command usage."""
    return """
  AUTOMATION COMMANDS:

  automation                Show automation status and enabled workflows
  automation start          Start all enabled workflows
  automation stop           Stop all workflows
  automation status         Show detailed workflow execution status
  automation run <name>     Run specific workflow immediately
  automation consent <name> Grant termination consent for workflow
  automation revoke <name>  Revoke termination consent

  WORKFLOW NAMES:

  quantum_queue            Quantum Job Queue Optimization (15 providers)
  classical_queue          Classical Compute Queue Optimization (13 providers)
  credentials              Credential Expiry Warnings (all 28 providers)
  resource_report          Resource Usage Reporting (all 28 providers)
  health_monitor           Provider Health Monitoring (all 28 providers)
  hardware_tune            Hardware Optimization Auto-Tuning (13 providers)

  EXAMPLES:

  automation                        # Show status
  automation start                  # Start all workflows
  automation run quantum_queue      # Run quantum optimization now
  automation consent quantum_queue  # Grant termination consent

"""


def _scheduler_usage() -> str:
    """Return scheduler command usage."""
    return """
  SCHEDULER COMMANDS:

  scheduler               Show scheduler status
  scheduler tasks         List all scheduled tasks
  scheduler pause <id>    Pause a specific task
  scheduler resume <id>   Resume a paused task
  scheduler stop          Stop the scheduler

  EXAMPLES:

  scheduler                           # Show status
  scheduler tasks                     # List all tasks
  scheduler pause optimize_quantum_queue  # Pause quantum optimization
  scheduler resume optimize_quantum_queue # Resume quantum optimization

"""
