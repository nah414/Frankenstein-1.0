"""
FRANKENSTEIN 1.0 - Eye of Sauron: Code Tools
Phase 4 / Day 4: Development Tools

Source code reading, editing, formatting, linting, execution, and testing.
Replaces the terminal's nano/vim/notepad/code/python/source commands with
a structured, permission-enforced tool surface.

Ring 3 (SAFE — no prompt, free execution):
    code_read          — view source file with line numbers and optional range
    code_format        — run black --check --diff (shows changes, no file write)
    code_lint          — run flake8 or pylint and return output (read only)

Ring 2 (SENSITIVE — always prompts for approval):
    code_edit          — inline string replacement: old_string → new_string
    code_format_apply  — run black to reformat a file (modifies the file)
    code_run           — execute a Python script or -c snippet
    code_test          — run pytest on a path, file, or function

Sandbox:
    code_edit and code_format_apply are restricted to ALLOWED_WRITE_PATHS.
    code_read has no path restriction (read-only).
    code_run and code_test require Ring 2 approval per call; cwd is unrestricted
    as execution is controlled by the approval prompt, not filesystem boundaries.

Limits:
    READ_MAX_LINES   = 500  lines per code_read call
    EXEC_TIMEOUT_SEC = 30   seconds for code_run / code_test / formatters
    EXEC_MAX_BYTES   = 50   KB output cap for all subprocess calls
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from agents.sauron.permissions import PermissionLevel, get_permission_manager
from agents.sauron.sandbox import get_sauron_sandbox
from agents.sauron.audit import SauronEvent, get_sauron_audit
from agents.sauron.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


# ── Limits ─────────────────────────────────────────────────────────────────────

READ_MAX_LINES   = 500
EXEC_TIMEOUT_SEC = 30
EXEC_MAX_BYTES   = 51_200   # 50 KB


# ── Code Tool ──────────────────────────────────────────────────────────────────

class CodeTool(BaseTool):
    """
    Source code operations for Eye of Sauron.

    Dispatch via action= parameter. Ring 3 actions execute freely.
    Ring 2 actions call _approve() and block until the user answers Y/n.
    File writes are additionally sandbox-checked against ALLOWED_WRITE_PATHS.
    """

    name = "code"
    description = (
        "Source code operations. "
        "Ring 3 (free): code_read (view with line numbers), "
        "code_format (black --check, no file change), code_lint (flake8/pylint). "
        "Ring 2 (approval): code_edit (inline old→new replacement), "
        "code_format_apply (black reformat), code_run (python script/-c), "
        "code_test (pytest)."
    )
    permission_level = PermissionLevel.SAFE  # base; Ring 2 actions self-manage

    def execute(self, action: str = "code_read", **kwargs) -> ToolResult:
        dispatch = {
            # ── Ring 3: reads / checks ─────────────────────────────────────────
            "code_read":         self._code_read,
            "code_format":       self._code_format_check,
            "code_lint":         self._code_lint,
            # ── Ring 2: writes / execution ─────────────────────────────────────
            "code_edit":         self._code_edit,
            "code_format_apply": self._code_format_apply,
            "code_run":          self._code_run,
            "code_test":         self._code_test,
        }
        if action not in dispatch:
            return ToolResult(
                success=False,
                error=f"Unknown code action '{action}'. Valid: {sorted(dispatch)}",
            )
        return dispatch[action](**kwargs)

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _approve(self, action_name: str, description: str) -> bool:
        """Request Ring 2 approval. Blocks until the user answers Y/n."""
        audit = get_sauron_audit()
        pm    = get_permission_manager()
        audit.log_permission(SauronEvent.PERMISSION_ASK, action_name, description)
        approved = pm.request_permission(action_name, description)
        event = SauronEvent.PERMISSION_GRANT if approved else SauronEvent.PERMISSION_DENY
        audit.log_permission(event, action_name, description)
        return approved

    def _run_subprocess(
        self,
        args: List[str],
        cwd: Optional[str] = None,
    ) -> ToolResult:
        """
        Run a subprocess with standard limits. Used by format, lint, run, test.
        Returns a ToolResult with stdout, stderr, and returncode in data.
        """
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=cwd,
                timeout=EXEC_TIMEOUT_SEC,
            )
            stdout = (result.stdout or "")[:EXEC_MAX_BYTES]
            stderr = (result.stderr or "")[:EXEC_MAX_BYTES]

            # Append truncation notice if output was cut
            if len(result.stdout or "") > EXEC_MAX_BYTES:
                stdout += f"\n[stdout truncated at {EXEC_MAX_BYTES // 1024} KB]"
            if len(result.stderr or "") > EXEC_MAX_BYTES:
                stderr += f"\n[stderr truncated at {EXEC_MAX_BYTES // 1024} KB]"

            success = result.returncode == 0
            return ToolResult(
                success=success,
                data={
                    "stdout":     stdout,
                    "stderr":     stderr,
                    "returncode": result.returncode,
                    "command":    " ".join(str(a) for a in args),
                },
                error=None if success else (
                    f"Process exited with code {result.returncode}"
                ),
                summary=(
                    f"returncode={result.returncode}, "
                    f"stdout={len(stdout)}B, stderr={len(stderr)}B"
                ),
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                error=f"Process timed out after {EXEC_TIMEOUT_SEC}s: {args[0]}",
            )
        except FileNotFoundError:
            return ToolResult(
                success=False,
                error=f"Command not found: '{args[0]}'. Is it installed?",
            )
        except Exception as e:
            logger.error("CodeTool subprocess error: %s", e, exc_info=True)
            return ToolResult(success=False, error=str(e))

    def _resolve_file(self, path: str) -> tuple:
        """
        Resolve a path string to a Path object.
        Returns (Path, None) on success or (None, ToolResult) on error.
        """
        if not path:
            return None, ToolResult(success=False, error="'path' is required.")
        try:
            resolved = Path(path).resolve()
        except Exception as e:
            return None, ToolResult(success=False, error=f"Invalid path '{path}': {e}")
        return resolved, None

    # ── Ring 3: Read / Check Operations ───────────────────────────────────────

    def _code_read(
        self,
        path: str = "",
        start_line: int = 1,
        end_line: Optional[int] = None,
        **_,
    ) -> ToolResult:
        """
        Read a source file with line numbers. Ring 3 — free.

        Returns up to READ_MAX_LINES (500) lines per call. Use start_line /
        end_line to page through large files.

        Args:
            path       : File path (absolute, or relative to cwd)
            start_line : First line to return (1-indexed, default 1)
            end_line   : Last line to return inclusive (default start + 499)

        Data keys: path, total_lines, start_line, end_line, content (numbered),
                   suffix, has_more (bool).
        """
        file_path, err = self._resolve_file(path)
        if err:
            return err

        if not file_path.exists():
            return ToolResult(success=False, error=f"File not found: {file_path}")
        if not file_path.is_file():
            return ToolResult(success=False, error=f"Not a regular file: {file_path}")

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return ToolResult(success=False, error=f"Cannot read '{file_path}': {e}")

        all_lines = content.splitlines()
        total     = len(all_lines)

        # Clamp range
        start = max(1, int(start_line))
        if end_line is not None:
            end = min(total, int(end_line))
        else:
            end = min(total, start + READ_MAX_LINES - 1)
        # Never exceed the per-call maximum regardless of explicit end_line
        end = min(end, start + READ_MAX_LINES - 1)

        selected = all_lines[start - 1 : end]
        numbered = "\n".join(
            f"{start + i:>6}: {line}" for i, line in enumerate(selected)
        )

        has_more = end < total
        summary  = (
            f"{file_path.name}: lines {start}–{end}/{total}"
            + (" [more lines available — use start_line to continue]" if has_more else "")
        )

        return ToolResult(
            success=True,
            data={
                "path":        str(file_path),
                "total_lines": total,
                "start_line":  start,
                "end_line":    end,
                "content":     numbered,
                "suffix":      file_path.suffix,
                "has_more":    has_more,
            },
            summary=summary,
        )

    def _code_format_check(self, path: str = "", **_) -> ToolResult:
        """
        Run black --check --diff on a file. Shows what would change.
        Ring 3 — free. No file modification occurs.

        Returns exit code 0 if already well-formatted, 1 with diff if not.

        Args:
            path : Path to the Python file to check
        """
        file_path, err = self._resolve_file(path)
        if err:
            return err
        if not file_path.exists():
            return ToolResult(success=False, error=f"File not found: {file_path}")

        return self._run_subprocess(
            [sys.executable, "-m", "black", "--check", "--diff", str(file_path)]
        )

    def _code_lint(
        self,
        path: str = "",
        tool: str = "flake8",
        extra_args: Optional[List[str]] = None,
        **_,
    ) -> ToolResult:
        """
        Run flake8 or pylint on a file or directory. Ring 3 — free (read only).

        Args:
            path      : File or directory to analyse
            tool      : "flake8" (default, fast) or "pylint" (deep analysis)
            extra_args: Additional tool arguments (e.g. ["--max-line-length=100"])

        Note: A non-zero exit code from these tools indicates style/error issues
              in the target code, not a failure of the tool itself. Check
              result.data["stdout"] for the findings.
        """
        if tool not in ("flake8", "pylint"):
            return ToolResult(
                success=False,
                error="'tool' must be 'flake8' or 'pylint'.",
            )

        file_path, err = self._resolve_file(path)
        if err:
            return err
        if not file_path.exists():
            return ToolResult(success=False, error=f"Path not found: {file_path}")

        args = [sys.executable, "-m", tool, str(file_path)]
        if extra_args:
            args.extend(extra_args)

        result = self._run_subprocess(args)
        # Lint tools return non-zero when findings exist — that's expected,
        # not an execution failure. Set success=True so the caller gets the output.
        if not result.success and result.data and result.data.get("returncode") in (1, 2):
            result.success = True
            result.error   = None
        return result

    # ── Ring 2: Write / Execution Operations ──────────────────────────────────

    def _code_edit(
        self,
        path: str = "",
        old_string: str = "",
        new_string: str = "",
        replace_all: bool = False,
        **_,
    ) -> ToolResult:
        """
        Inline string replacement in a source file. Ring 2 — approval required.

        old_string must match exactly once in the file unless replace_all=True.
        If it matches zero times, the operation is rejected (no guessing).
        If it matches more than once and replace_all=False, the operation is
        rejected with a count — narrow down old_string or use replace_all=True.

        File must be within ALLOWED_WRITE_PATHS (sandbox enforced).

        Args:
            path        : Target file path
            old_string  : Exact string to find (whitespace matters)
            new_string  : Replacement string (can be empty string to delete)
            replace_all : Replace every occurrence (default False)
        """
        if not old_string:
            return ToolResult(success=False, error="'old_string' is required for code_edit.")

        file_path, err = self._resolve_file(path)
        if err:
            return err

        # Sandbox: file writes must be within allowed directories
        sandbox = get_sauron_sandbox()
        if not sandbox.is_write_allowed(file_path):
            get_sauron_audit().log_ring1_block(
                f"code_edit outside allowed paths: {file_path}"
            )
            return ToolResult(
                success=False,
                error=(
                    f"BLOCKED: '{file_path}' is outside allowed write directories. "
                    f"code_edit is restricted to the Frankenstein project directories."
                ),
                permission_level=PermissionLevel.FORBIDDEN,
            )

        if not file_path.exists():
            return ToolResult(success=False, error=f"File not found: {file_path}")

        try:
            original = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return ToolResult(success=False, error=f"Cannot read '{file_path}': {e}")

        # Occurrence check — fail fast before prompting
        count = original.count(old_string)
        if count == 0:
            return ToolResult(
                success=False,
                error=(
                    f"'old_string' not found in {file_path.name}. "
                    "Check exact whitespace and indentation."
                ),
            )
        if count > 1 and not replace_all:
            return ToolResult(
                success=False,
                error=(
                    f"'old_string' found {count} times in {file_path.name}. "
                    "Provide a longer, unique context string or set replace_all=True."
                ),
            )

        # Build prompt description
        old_preview = old_string[:60].replace("\n", "↵")
        new_preview = new_string[:60].replace("\n", "↵") if new_string else "(deleted)"
        occurrences = f"all {count} occurrences" if replace_all else "1 occurrence"
        desc = (
            f"Edit {file_path.name}: replace {occurrences} of "
            f"'{old_preview}' → '{new_preview}'"
        )

        if not self._approve("code_edit", desc):
            return ToolResult(
                success=False,
                error="code_edit denied by user.",
                permission_level=PermissionLevel.SENSITIVE,
            )

        # Apply replacement
        if replace_all:
            modified = original.replace(old_string, new_string)
        else:
            modified = original.replace(old_string, new_string, 1)

        try:
            file_path.write_text(modified, encoding="utf-8")
        except Exception as e:
            return ToolResult(success=False, error=f"Cannot write '{file_path}': {e}")

        summary = (
            f"Edited {file_path.name}: replaced {occurrences}. "
            f"Size: {len(original)} → {len(modified)} bytes."
        )
        return ToolResult(
            success=True,
            data={
                "path":         str(file_path),
                "replacements": count if replace_all else 1,
                "size_before":  len(original),
                "size_after":   len(modified),
            },
            summary=summary,
            permission_level=PermissionLevel.SENSITIVE,
        )

    def _code_format_apply(self, path: str = "", **_) -> ToolResult:
        """
        Run black to reformat a file in-place. Ring 2 — approval required.
        File must be within ALLOWED_WRITE_PATHS.

        Args:
            path : Path to the Python file to reformat
        """
        file_path, err = self._resolve_file(path)
        if err:
            return err

        sandbox = get_sauron_sandbox()
        if not sandbox.is_write_allowed(file_path):
            return ToolResult(
                success=False,
                error=(
                    f"BLOCKED: '{file_path}' is outside allowed write directories."
                ),
                permission_level=PermissionLevel.FORBIDDEN,
            )

        if not file_path.exists():
            return ToolResult(success=False, error=f"File not found: {file_path}")

        if not self._approve(
            "code_format_apply",
            f"Run black formatter on '{file_path.name}' (file will be modified)",
        ):
            return ToolResult(
                success=False,
                error="code_format_apply denied by user.",
                permission_level=PermissionLevel.SENSITIVE,
            )

        return self._run_subprocess(
            [sys.executable, "-m", "black", str(file_path)]
        )

    def _code_run(
        self,
        path: Optional[str] = None,
        code: Optional[str] = None,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        **_,
    ) -> ToolResult:
        """
        Execute a Python script or inline code snippet. Ring 2 — approval.

        Provide exactly one of 'path' (script file) or 'code' (inline string).
        This replaces the terminal's 'python' and 'source' commands for .py files.

        Args:
            path : Path to a .py script to execute
            code : Inline Python code (passed as python -c '...')
            args : Additional CLI arguments for the script (ignored with 'code')
            cwd  : Working directory for execution (default: current directory)
        """
        if not path and not code:
            return ToolResult(
                success=False,
                error="Provide 'path' (script file) or 'code' (inline snippet), not neither.",
            )
        if path and code:
            return ToolResult(
                success=False,
                error="Provide 'path' or 'code', not both.",
            )

        exec_args = [sys.executable]

        if code:
            exec_args.extend(["-c", code])
            preview = code[:80].replace("\n", "↵")
            desc = f"python -c '{preview}'" + ("..." if len(code) > 80 else "")
        else:
            file_path, err = self._resolve_file(path)
            if err:
                return err
            if not file_path.exists():
                return ToolResult(success=False, error=f"Script not found: {file_path}")
            exec_args.append(str(file_path))
            if args:
                exec_args.extend(str(a) for a in args)
            arg_str = " " + " ".join(str(a) for a in args) if args else ""
            desc    = f"python {file_path.name}{arg_str}"

        if cwd:
            run_cwd = str(Path(cwd).resolve())
        else:
            run_cwd = None

        if not self._approve("code_run", f"Execute: {desc}"):
            return ToolResult(
                success=False,
                error="code_run denied by user.",
                permission_level=PermissionLevel.SENSITIVE,
            )

        return self._run_subprocess(exec_args, cwd=run_cwd)

    def _code_test(
        self,
        path: str = ".",
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        **_,
    ) -> ToolResult:
        """
        Run pytest on a path, file, or specific test function. Ring 2 — approval.

        This replaces the terminal's 'python -m pytest' invocations.

        Args:
            path : pytest target — directory, file, or file::TestClass::test_method
            args : Additional pytest arguments (e.g. ["-v", "-x", "--tb=short"])
            cwd  : Working directory for pytest execution

        Examples:
            action="code_test", path="tests/unit"
            action="code_test", path="tests/test_sauron_engine.py::test_health_check"
            action="code_test", path=".", args=["-v", "--tb=short"]
        """
        test_args = [sys.executable, "-m", "pytest", path]
        if args:
            test_args.extend(str(a) for a in args)

        extra = (" " + " ".join(str(a) for a in args)) if args else ""
        desc  = f"pytest {path}{extra}"

        if cwd:
            run_cwd = str(Path(cwd).resolve())
        else:
            run_cwd = None

        if not self._approve("code_test", desc):
            return ToolResult(
                success=False,
                error="code_test denied by user.",
                permission_level=PermissionLevel.SENSITIVE,
            )

        result = self._run_subprocess(test_args, cwd=run_cwd)
        # pytest exits 1 when tests fail — that's a test result, not a tool failure.
        # Keep success=False so the caller knows tests didn't all pass, but make
        # sure the output is returned so Sauron can report which tests failed.
        return result
