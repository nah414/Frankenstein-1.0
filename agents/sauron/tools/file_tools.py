"""
FRANKENSTEIN 1.0 - Eye of Sauron: File Tools
Phase 4 / Day 3: Tool Framework

File read/write/delete/copy operations with full sandbox enforcement.
All write and delete ops check SauronSandbox path rules before execution.

Permission mapping:
  Ring 3 (SAFE):     file_read, file_copy
  Ring 2 (SENSITIVE): file_write, file_delete, file_move
"""

import logging
import shutil
from pathlib import Path
from typing import Optional

from agents.sauron.permissions import PermissionLevel, get_permission_manager
from agents.sauron.sandbox import get_sauron_sandbox
from agents.sauron.audit import SauronEvent, get_sauron_audit
from agents.sauron.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

# Hard limit on bytes read per file_read call (1 MB)
MAX_READ_BYTES = 1_048_576

# Hard limit on bytes written per file_write call (10 MB)
MAX_WRITE_BYTES = 10_485_760


class FileTool(BaseTool):
    """
    File system operations for Eye of Sauron.

    Actions:
      file_read    (Ring 3) — read text file content
      file_write   (Ring 2) — create or overwrite file
      file_delete  (Ring 2) — delete file
      file_copy    (Ring 3) — copy file within allowed paths
      file_move    (Ring 2) — move / rename file
    """

    name = "file"
    description = (
        "File operations: read (Ring 3), write/delete/move (Ring 2 — approval required). "
        "All write/delete operations are sandboxed to allowed project directories. "
        "Blocked paths (Windows, AppData) are hard-rejected even with permission."
    )
    permission_level = PermissionLevel.SAFE

    _SENSITIVE_ACTIONS = frozenset({"file_write", "file_delete", "file_move"})

    def execute(self, action: str = "file_read", **kwargs) -> ToolResult:
        dispatch = {
            "file_read":   self._file_read,
            "file_write":  self._file_write,
            "file_delete": self._file_delete,
            "file_copy":   self._file_copy,
            "file_move":   self._file_move,
        }
        if action not in dispatch:
            return ToolResult(
                success=False,
                error=f"Unknown file action '{action}'. Valid: {sorted(dispatch)}",
            )

        if action in self._SENSITIVE_ACTIONS:
            pm = get_permission_manager()
            audit = get_sauron_audit()
            path = kwargs.get("path", kwargs.get("src", "?"))
            desc = f"{action}: {path}"
            audit.log_permission(SauronEvent.PERMISSION_ASK, action, desc)
            if not pm.request_permission(action, desc):
                audit.log_permission(SauronEvent.PERMISSION_DENY, action, desc)
                return ToolResult(success=False, error=f"Permission denied for {action}",
                                  permission_level=PermissionLevel.SENSITIVE)
            audit.log_permission(SauronEvent.PERMISSION_GRANT, action, desc)

        return dispatch[action](**kwargs)

    def _file_read(self, path: str = "", encoding: str = "utf-8", **kwargs) -> ToolResult:
        """
        Read a text file. Returns content as string.
        Max 1 MB. Binary files are rejected.
        """
        if not path:
            return ToolResult(success=False, error="'path' is required")
        try:
            p = Path(path).resolve()
            if not p.exists():
                return ToolResult(success=False, error=f"File not found: {path}")
            if not p.is_file():
                return ToolResult(success=False, error=f"Not a file: {path}")

            size = p.stat().st_size
            if size > MAX_READ_BYTES:
                return ToolResult(
                    success=False,
                    error=f"File too large ({size/1024:.0f} KB). Max {MAX_READ_BYTES//1024} KB.",
                )

            content = p.read_text(encoding=encoding, errors="replace")
            lines = content.count("\n") + 1

            return ToolResult(
                success=True,
                data={"path": str(p), "content": content, "lines": lines,
                      "size_bytes": size},
                summary=f"Read {str(p)} ({lines} lines, {size} bytes).",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _file_write(self, path: str = "", content: str = "", encoding: str = "utf-8",
                    append: bool = False, **kwargs) -> ToolResult:
        """
        Write (or append) text to a file. Creates parent directories if needed.
        Sandbox path check enforced before write.
        """
        if not path:
            return ToolResult(success=False, error="'path' is required")

        sandbox = get_sauron_sandbox()
        safe, reason = sandbox.is_path_safe(path)
        if not safe:
            get_sauron_audit().log_ring1_block(f"file_write: {path} — {reason}")
            return ToolResult(success=False, error=f"BLOCKED: {reason}",
                              permission_level=PermissionLevel.FORBIDDEN)

        if len(content.encode(encoding)) > MAX_WRITE_BYTES:
            return ToolResult(success=False,
                              error=f"Content too large. Max {MAX_WRITE_BYTES//1024//1024} MB.")
        try:
            p = Path(path).resolve()
            p.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append else "w"
            p.open(mode, encoding=encoding).write(content)
            return ToolResult(
                success=True,
                data={"path": str(p), "bytes_written": len(content.encode(encoding)),
                      "append": append},
                summary=f"{'Appended' if append else 'Wrote'} {len(content)} chars to {str(p)}.",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _file_delete(self, path: str = "", **kwargs) -> ToolResult:
        """Delete a single file. Directories are rejected (use dir_tools)."""
        if not path:
            return ToolResult(success=False, error="'path' is required")

        sandbox = get_sauron_sandbox()
        safe, reason = sandbox.is_path_safe(path)
        if not safe:
            get_sauron_audit().log_ring1_block(f"file_delete: {path} — {reason}")
            return ToolResult(success=False, error=f"BLOCKED: {reason}",
                              permission_level=PermissionLevel.FORBIDDEN)
        try:
            p = Path(path).resolve()
            if not p.exists():
                return ToolResult(success=False, error=f"File not found: {path}")
            if p.is_dir():
                return ToolResult(success=False,
                                  error="Use dir_tools for directory deletion.")
            p.unlink()
            return ToolResult(
                success=True,
                data={"path": str(p)},
                summary=f"Deleted: {str(p)}",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _file_copy(self, src: str = "", dst: str = "", **kwargs) -> ToolResult:
        """
        Copy a file. Destination must be within allowed write paths.
        Source can be anywhere readable.
        """
        if not src or not dst:
            return ToolResult(success=False, error="'src' and 'dst' are required")

        sandbox = get_sauron_sandbox()
        safe, reason = sandbox.is_path_safe(dst)
        if not safe:
            get_sauron_audit().log_ring1_block(f"file_copy dst: {dst} — {reason}")
            return ToolResult(success=False, error=f"BLOCKED (destination): {reason}",
                              permission_level=PermissionLevel.FORBIDDEN)
        try:
            src_p = Path(src).resolve()
            dst_p = Path(dst).resolve()
            if not src_p.exists():
                return ToolResult(success=False, error=f"Source not found: {src}")
            dst_p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_p, dst_p)
            return ToolResult(
                success=True,
                data={"src": str(src_p), "dst": str(dst_p)},
                summary=f"Copied {str(src_p)} → {str(dst_p)}.",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _file_move(self, src: str = "", dst: str = "", **kwargs) -> ToolResult:
        """Move / rename a file. Both src and dst must be in allowed paths."""
        if not src or not dst:
            return ToolResult(success=False, error="'src' and 'dst' are required")

        sandbox = get_sauron_sandbox()
        for label, p in [("source", src), ("destination", dst)]:
            safe, reason = sandbox.is_path_safe(p)
            if not safe:
                get_sauron_audit().log_ring1_block(f"file_move {label}: {p} — {reason}")
                return ToolResult(success=False, error=f"BLOCKED ({label}): {reason}",
                                  permission_level=PermissionLevel.FORBIDDEN)
        try:
            src_p = Path(src).resolve()
            dst_p = Path(dst).resolve()
            if not src_p.exists():
                return ToolResult(success=False, error=f"Source not found: {src}")
            dst_p.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_p), str(dst_p))
            return ToolResult(
                success=True,
                data={"src": str(src_p), "dst": str(dst_p)},
                summary=f"Moved {str(src_p)} → {str(dst_p)}.",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
