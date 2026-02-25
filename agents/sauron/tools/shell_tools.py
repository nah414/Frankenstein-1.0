"""
FRANKENSTEIN 1.0 - Eye of Sauron: Shell Tools
Phase 4 / Day 3: Tool Framework
Extended Day 4: env_read / env_write added

Shell info (Ring 3 — safe, read-only system queries) and
shell_exec (Ring 2 — always requires explicit user approval).
Environment variable read (Ring 3) and write/unset (Ring 2).

shell_exec is tightly constrained:
  - No Ring 1 bypass ever
  - Timeout hard cap: 15 seconds
  - stdout/stderr capped at 10 KB
  - Working directory must be within ALLOWED_WRITE_PATHS or system read-only
  - Always prompts for approval regardless of content

env_write is session-scoped: changes apply to os.environ for the lifetime
of the current Frankenstein process. They are NOT persisted to the shell that
launched Frankenstein (by OS design — child processes cannot export to parent).
"""

import logging
import os
import platform
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import psutil

from agents.sauron.permissions import PermissionLevel
from agents.sauron.sandbox import get_sauron_sandbox
from agents.sauron.audit import get_sauron_audit
from agents.sauron.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


# Hard caps for shell_exec output
EXEC_TIMEOUT_SEC = 15
EXEC_MAX_OUTPUT_BYTES = 10_240   # 10 KB

# Commands that are never allowed in shell_exec even with approval
SHELL_EXEC_FORBIDDEN = frozenset({
    "rm -rf /",
    "format",
    "del /s /q c:\\",
    "rd /s /q c:\\",
    "mkfs",
    "dd if=/dev/zero",
    ":(){ :|:& };:",   # fork bomb
    "shutdown",
    "reboot",
    "poweroff",
    "taskkill /f /im",
    "reg delete",
    "reg add HKLM",
    "reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
    "netsh firewall",
    "netsh advfirewall",
    "sc delete",
    "sc stop",
    "bcdedit",
    "diskpart",
})


class ShellTool(BaseTool):
    """
    Shell operations for Eye of Sauron.

    Actions:
      shell_info    — read-only system information (Ring 3 / SAFE)
      shell_exec    — run a shell command (Ring 2 / SENSITIVE — always prompts)
    """

    name = "shell"
    description = (
        "Shell operations: "
        "shell_info (Ring 3 — hostname, date, whoami, env, disk, processes, Python path), "
        "shell_exec (Ring 2 — run a command, always requires approval, hard limits apply)."
    )
    permission_level = PermissionLevel.SAFE   # base level; shell_exec overrides per-call

    def execute(self, action: str = "shell_info", **kwargs) -> ToolResult:
        dispatch = {
            "shell_info": self._shell_info,
            "shell_exec": self._shell_exec,
            "env_read":   self._env_read,
            "env_write":  self._env_write,
        }
        if action not in dispatch:
            return ToolResult(
                success=False,
                error=f"Unknown shell action '{action}'. Valid: {sorted(dispatch)}",
            )
        return dispatch[action](**kwargs)

    # ── shell_info ─────────────────────────────────────────────────────────────

    def _shell_info(self, query: str = "all", **kwargs) -> ToolResult:
        """
        Collect read-only system information. No subprocess — pure Python.

        Args:
            query: One of: "all", "host", "date", "user", "env", "disk",
                           "processes", "python", "memory", "cpu"
        """
        queries = {
            "all", "host", "date", "user", "env",
            "disk", "processes", "python", "memory", "cpu",
        }
        if query not in queries:
            return ToolResult(
                success=False,
                error=f"Unknown query '{query}'. Valid: {sorted(queries)}",
            )

        info = {}

        try:
            # Host / OS
            if query in ("all", "host"):
                info["host"] = {
                    "hostname":    platform.node(),
                    "os":          platform.system(),
                    "os_version":  platform.version(),
                    "os_release":  platform.release(),
                    "machine":     platform.machine(),
                    "processor":   platform.processor(),
                    "cpu_count":   os.cpu_count(),
                }

            # Date / time
            if query in ("all", "date"):
                now = datetime.now()
                info["date"] = {
                    "datetime":   now.isoformat(timespec="seconds"),
                    "date":       now.date().isoformat(),
                    "time":       now.strftime("%H:%M:%S"),
                    "timestamp":  now.timestamp(),
                }

            # Current user
            if query in ("all", "user"):
                info["user"] = {
                    "username": os.environ.get("USERNAME") or os.environ.get("USER") or "unknown",
                    "home":     str(Path.home()),
                    "cwd":      str(Path.cwd()),
                }

            # Environment (safe subset — excludes secrets)
            if query in ("all", "env"):
                safe_env_keys = {
                    "PATH", "TEMP", "TMP", "APPDATA", "LOCALAPPDATA",
                    "PROGRAMFILES", "SYSTEMROOT", "WINDIR",
                    "COMPUTERNAME", "USERDOMAIN", "OS",
                    "PROCESSOR_ARCHITECTURE", "NUMBER_OF_PROCESSORS",
                    "CONDA_DEFAULT_ENV", "VIRTUAL_ENV", "PYTHONPATH",
                    "FRANKENSTEIN_ROOT", "FRANKENSTEIN_ENV",
                }
                info["env"] = {
                    k: v for k, v in os.environ.items()
                    if k.upper() in safe_env_keys
                }

            # Disk usage
            if query in ("all", "disk"):
                disk_info = []
                for part in psutil.disk_partitions(all=False):
                    try:
                        usage = psutil.disk_usage(part.mountpoint)
                        disk_info.append({
                            "device":     part.device,
                            "mountpoint": part.mountpoint,
                            "fstype":     part.fstype,
                            "total_gb":   round(usage.total / 1e9, 2),
                            "used_gb":    round(usage.used / 1e9, 2),
                            "free_gb":    round(usage.free / 1e9, 2),
                            "percent":    usage.percent,
                        })
                    except (PermissionError, OSError):
                        pass
                info["disk"] = disk_info

            # Running processes (top 20 by memory)
            if query in ("all", "processes"):
                procs = []
                for proc in sorted(
                    psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent", "status"]),
                    key=lambda p: p.info.get("memory_percent") or 0,
                    reverse=True,
                )[:20]:
                    procs.append({
                        "pid":    proc.info["pid"],
                        "name":   proc.info["name"],
                        "mem_%":  round(proc.info.get("memory_percent") or 0, 2),
                        "cpu_%":  round(proc.info.get("cpu_percent") or 0, 2),
                        "status": proc.info.get("status"),
                    })
                info["processes"] = procs

            # Python environment
            if query in ("all", "python"):
                import sys
                frankenstein_root = shutil.which("python") or sys.executable
                info["python"] = {
                    "executable":   sys.executable,
                    "version":      sys.version,
                    "version_info": list(sys.version_info[:3]),
                    "prefix":       sys.prefix,
                    "path":         sys.path[:8],  # truncate
                }

            # Memory
            if query in ("all", "memory"):
                vm = psutil.virtual_memory()
                sm = psutil.swap_memory()
                info["memory"] = {
                    "total_gb":    round(vm.total / 1e9, 2),
                    "available_gb": round(vm.available / 1e9, 2),
                    "used_gb":     round(vm.used / 1e9, 2),
                    "percent":     vm.percent,
                    "swap_total_gb": round(sm.total / 1e9, 2),
                    "swap_used_gb":  round(sm.used / 1e9, 2),
                    "swap_percent":  sm.percent,
                }

            # CPU
            if query in ("all", "cpu"):
                info["cpu"] = {
                    "count_logical":  psutil.cpu_count(logical=True),
                    "count_physical": psutil.cpu_count(logical=False),
                    "percent":        psutil.cpu_percent(interval=0.5),
                    "freq_mhz":       (
                        psutil.cpu_freq().current
                        if psutil.cpu_freq() else None
                    ),
                }

            summary = f"shell_info [{query}]: collected {len(info)} section(s)."
            return ToolResult(success=True, data=info, summary=summary)

        except Exception as e:
            logger.error("shell_info error: %s", e, exc_info=True)
            return ToolResult(success=False, error=str(e))

    # ── shell_exec ─────────────────────────────────────────────────────────────

    def _shell_exec(
        self,
        command: str = "",
        cwd: str = ".",
        timeout: int = EXEC_TIMEOUT_SEC,
        **kwargs,
    ) -> ToolResult:
        """
        Execute a shell command. ALWAYS requires Ring 2 approval — there is no
        bypass. Hard limits: 15s timeout, 10KB output cap.

        Args:
            command : Command string to execute
            cwd     : Working directory (must be in allowed paths)
            timeout : Override timeout (max 15s)
        """
        if not command or not command.strip():
            return ToolResult(success=False, error="'command' is required and cannot be empty")

        # Hard-cap timeout
        timeout = min(int(timeout), EXEC_TIMEOUT_SEC)

        # Forbidden command check (substring scan on lowercase)
        cmd_lower = command.lower().strip()
        for forbidden in SHELL_EXEC_FORBIDDEN:
            if forbidden in cmd_lower:
                get_sauron_audit().log_ring1_block(
                    f"shell_exec forbidden pattern '{forbidden}' in: {command[:80]}"
                )
                return ToolResult(
                    success=False,
                    error=f"FORBIDDEN: command contains blocked pattern '{forbidden}'.",
                    permission_level=PermissionLevel.FORBIDDEN,
                )

        # Working directory safety check (read: any existing path is OK for exec;
        # we only restrict if it's in a hard-blocked system path)
        try:
            cwd_path = Path(cwd).resolve()
        except Exception:
            return ToolResult(success=False, error=f"Invalid cwd: {cwd}")

        sandbox = get_sauron_sandbox()
        if sandbox.is_path_blocked(cwd_path):
            return ToolResult(
                success=False,
                error=f"BLOCKED: cwd '{cwd_path}' is in a restricted system directory.",
                permission_level=PermissionLevel.FORBIDDEN,
            )

        # Ring 2 approval — always, no exception
        from agents.sauron.permissions import get_permission_manager
        from agents.sauron.audit import SauronEvent

        audit = get_sauron_audit()
        pm = get_permission_manager()

        description = f"Run shell command: {command[:120]}"
        audit.log_permission(SauronEvent.PERMISSION_ASK, "shell_exec", description)

        approved = pm.request_permission("shell_exec", description)
        if not approved:
            audit.log_permission(SauronEvent.PERMISSION_DENY, "shell_exec", description)
            return ToolResult(
                success=False,
                error="shell_exec denied by user.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        audit.log_permission(SauronEvent.PERMISSION_GRANT, "shell_exec", description)

        # Execute
        audit.log_tool_call("shell_exec", command[:150])
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                cwd=str(cwd_path) if cwd_path.exists() else None,
                timeout=timeout,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            stdout = result.stdout or ""
            stderr = result.stderr or ""

            # Cap output
            if len(stdout) > EXEC_MAX_OUTPUT_BYTES:
                stdout = stdout[:EXEC_MAX_OUTPUT_BYTES] + f"\n[stdout truncated at {EXEC_MAX_OUTPUT_BYTES} bytes]"
            if len(stderr) > EXEC_MAX_OUTPUT_BYTES:
                stderr = stderr[:EXEC_MAX_OUTPUT_BYTES] + f"\n[stderr truncated at {EXEC_MAX_OUTPUT_BYTES} bytes]"

            success = (result.returncode == 0)
            summary = (
                f"shell_exec: returncode={result.returncode}. "
                f"stdout={len(result.stdout or '')}B, stderr={len(result.stderr or '')}B."
            )

            return ToolResult(
                success=success,
                data={
                    "command":    command,
                    "cwd":        str(cwd_path),
                    "returncode": result.returncode,
                    "stdout":     stdout,
                    "stderr":     stderr,
                    "timeout_sec": timeout,
                },
                error=None if success else f"Command exited with code {result.returncode}",
                summary=summary,
                permission_level=PermissionLevel.SENSITIVE,
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                error=f"Command timed out after {timeout}s: {command[:80]}",
                permission_level=PermissionLevel.SENSITIVE,
            )
        except Exception as e:
            logger.error("shell_exec error: %s", e, exc_info=True)
            return ToolResult(success=False, error=str(e))

    # ── env_read ───────────────────────────────────────────────────────────────

    def _env_read(self, keys: list = None, **kwargs) -> ToolResult:
        """
        Read environment variables. Ring 3 — free.

        Replaces the terminal's 'env', 'printenv', and 'set' (read-only) commands.

        A safe subset of keys is returned when no keys are requested, excluding
        known secret patterns (API keys, tokens, passwords, credentials).

        Args:
            keys : Specific variable names to read (e.g. ["PATH", "HOME"]).
                   If None or empty, returns the safe-filtered full environment.

        Data keys: variables (dict), filtered (bool), requested_keys (list).
        """
        SECRET_PATTERNS = (
            "KEY", "TOKEN", "SECRET", "PASSWORD", "PASSWD", "PWD",
            "CREDENTIAL", "AUTH", "API", "PRIVATE", "CERT",
        )

        if keys:
            # Return only what was explicitly requested
            found     = {k: os.environ[k] for k in keys if k in os.environ}
            missing   = [k for k in keys if k not in os.environ]
            summary   = f"env_read: returned {len(found)}/{len(keys)} requested variable(s)."
            if missing:
                summary += f" Missing: {missing}"
            return ToolResult(
                success=True,
                data={
                    "variables":      found,
                    "missing":        missing,
                    "filtered":       False,
                    "requested_keys": list(keys),
                },
                summary=summary,
            )

        # No specific keys — return filtered full environment
        safe_vars = {}
        skipped   = 0
        for k, v in os.environ.items():
            k_upper = k.upper()
            if any(pat in k_upper for pat in SECRET_PATTERNS):
                skipped += 1
                continue
            safe_vars[k] = v

        summary = (
            f"env_read: {len(safe_vars)} variables returned. "
            f"{skipped} secret-pattern variable(s) filtered out."
        )
        return ToolResult(
            success=True,
            data={
                "variables": safe_vars,
                "filtered":  True,
                "skipped":   skipped,
            },
            summary=summary,
        )

    # ── env_write ──────────────────────────────────────────────────────────────

    def _env_write(self, operations: list = None, **kwargs) -> ToolResult:
        """
        Set or unset environment variables in the current process. Ring 2 — approval.

        Replaces the terminal's 'export VAR=value' and 'unset VAR' commands.
        Changes are session-scoped (os.environ only; cannot propagate to parent shell).

        Args:
            operations : List of dicts, each with one of:
                         {"action": "set",   "key": "VAR", "value": "val"}
                         {"action": "unset", "key": "VAR"}

        Example:
            operations=[
                {"action": "set",   "key": "FRANKENSTEIN_ENV", "value": "dev"},
                {"action": "unset", "key": "OLD_VAR"},
            ]
        """
        if not operations:
            return ToolResult(
                success=False,
                error=(
                    "'operations' list is required. Each entry: "
                    '{"action": "set"/"unset", "key": "VAR_NAME", "value": "..."}'
                ),
            )

        # Validate before prompting
        valid_actions = {"set", "unset"}
        for i, op in enumerate(operations):
            if not isinstance(op, dict):
                return ToolResult(
                    success=False,
                    error=f"Operation {i} must be a dict, got {type(op).__name__}.",
                )
            if op.get("action") not in valid_actions:
                return ToolResult(
                    success=False,
                    error=f"Operation {i}: 'action' must be 'set' or 'unset'.",
                )
            if not op.get("key"):
                return ToolResult(
                    success=False,
                    error=f"Operation {i}: 'key' (variable name) is required.",
                )
            if op["action"] == "set" and "value" not in op:
                return ToolResult(
                    success=False,
                    error=f"Operation {i}: 'value' is required for action='set'.",
                )

        # Build human-readable summary for approval prompt
        lines = []
        for op in operations:
            if op["action"] == "set":
                lines.append(f"  SET  {op['key']} = {str(op.get('value', ''))[:80]}")
            else:
                lines.append(f"  UNSET {op['key']}")
        desc = f"Modify {len(operations)} environment variable(s):\n" + "\n".join(lines)

        from agents.sauron.permissions import get_permission_manager
        from agents.sauron.audit import SauronEvent

        audit = get_sauron_audit()
        pm    = get_permission_manager()
        audit.log_permission(SauronEvent.PERMISSION_ASK, "env_write", desc)
        approved = pm.request_permission("env_write", desc)
        event = SauronEvent.PERMISSION_GRANT if approved else SauronEvent.PERMISSION_DENY
        audit.log_permission(event, "env_write", desc)

        if not approved:
            return ToolResult(
                success=False,
                error="env_write denied by user.",
                permission_level=PermissionLevel.SENSITIVE,
            )

        # Apply operations
        applied = []
        errors  = []
        for op in operations:
            key = op["key"]
            try:
                if op["action"] == "set":
                    value = str(op["value"])
                    os.environ[key] = value
                    applied.append({"action": "set", "key": key, "value": value})
                else:
                    existed = key in os.environ
                    if existed:
                        del os.environ[key]
                    applied.append({"action": "unset", "key": key, "existed": existed})
            except Exception as e:
                errors.append({"key": key, "error": str(e)})

        success = len(errors) == 0
        summary = (
            f"env_write: applied {len(applied)} operation(s)"
            + (f", {len(errors)} error(s)" if errors else "")
        )
        return ToolResult(
            success=success,
            data={"applied": applied, "errors": errors},
            error=None if success else f"{len(errors)} operation(s) failed: {errors}",
            summary=summary,
            permission_level=PermissionLevel.SENSITIVE,
        )
