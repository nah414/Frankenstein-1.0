"""
FRANKENSTEIN 1.0 - Eye of Sauron: Directory Tools
Phase 4 / Day 3: Tool Framework

Directory listing, creation, navigation, and tree view.
All operations are Ring 3 (SAFE) — read-only or creation within allowed paths.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from agents.sauron.permissions import PermissionLevel
from agents.sauron.sandbox import get_sauron_sandbox
from agents.sauron.audit import get_sauron_audit
from agents.sauron.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

# Max entries returned in a single dir_list
MAX_LIST_ENTRIES = 200

# Max depth for dir_tree
MAX_TREE_DEPTH = 5


class DirTool(BaseTool):
    """
    Directory operations for Eye of Sauron. All Ring 3 (SAFE).

    Actions:
      dir_list      — list directory contents with metadata
      dir_create    — create directory (allowed paths only)
      dir_navigate  — resolve and validate a path (no side effects)
      dir_tree      — recursive tree listing with depth limit
    """

    name = "dir"
    description = (
        "Directory operations: list, create, navigate, tree. "
        "All Ring 3 (SAFE — no approval needed). "
        "dir_create is restricted to allowed project directories."
    )
    permission_level = PermissionLevel.SAFE

    def execute(self, action: str = "dir_list", **kwargs) -> ToolResult:
        dispatch = {
            "dir_list":     self._dir_list,
            "dir_create":   self._dir_create,
            "dir_navigate": self._dir_navigate,
            "dir_tree":     self._dir_tree,
        }
        if action not in dispatch:
            return ToolResult(
                success=False,
                error=f"Unknown dir action '{action}'. Valid: {sorted(dispatch)}",
            )
        return dispatch[action](**kwargs)

    def _dir_list(self, path: str = ".", show_hidden: bool = False, **kwargs) -> ToolResult:
        """
        List directory contents. Returns sorted list of entries with metadata.
        Hidden files (dot-files) excluded by default.
        """
        try:
            p = Path(path).resolve()
            if not p.exists():
                return ToolResult(success=False, error=f"Path not found: {path}")
            if not p.is_dir():
                return ToolResult(success=False, error=f"Not a directory: {path}")

            entries = []
            count = 0
            for item in sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
                if not show_hidden and item.name.startswith("."):
                    continue
                if count >= MAX_LIST_ENTRIES:
                    entries.append({"name": f"... ({MAX_LIST_ENTRIES}+ entries, truncated)",
                                    "type": "info"})
                    break
                try:
                    stat = item.stat()
                    entries.append({
                        "name":     item.name,
                        "type":     "dir" if item.is_dir() else "file",
                        "size_bytes": stat.st_size if item.is_file() else None,
                        "modified": stat.st_mtime,
                    })
                    count += 1
                except PermissionError:
                    entries.append({"name": item.name, "type": "unknown", "error": "permission denied"})

            dirs  = sum(1 for e in entries if e.get("type") == "dir")
            files = sum(1 for e in entries if e.get("type") == "file")

            return ToolResult(
                success=True,
                data={"path": str(p), "entries": entries, "dirs": dirs, "files": files},
                summary=f"{str(p)}: {dirs} dirs, {files} files.",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _dir_create(self, path: str = "", **kwargs) -> ToolResult:
        """
        Create directory (and parents). Path must be within allowed write dirs.
        """
        if not path:
            return ToolResult(success=False, error="'path' is required")

        sandbox = get_sauron_sandbox()
        safe, reason = sandbox.is_path_safe(path)
        if not safe:
            get_sauron_audit().log_ring1_block(f"dir_create: {path} — {reason}")
            return ToolResult(success=False, error=f"BLOCKED: {reason}",
                              permission_level=PermissionLevel.FORBIDDEN)
        try:
            p = Path(path).resolve()
            p.mkdir(parents=True, exist_ok=True)
            return ToolResult(
                success=True,
                data={"path": str(p), "created": not p.existed if hasattr(p, "existed") else True},
                summary=f"Directory ready: {str(p)}",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _dir_navigate(self, path: str = ".", **kwargs) -> ToolResult:
        """
        Resolve a path and return its absolute form.
        No filesystem modification — pure path resolution.
        """
        try:
            p = Path(path).resolve()
            exists = p.exists()
            return ToolResult(
                success=True,
                data={
                    "path":    str(p),
                    "exists":  exists,
                    "is_dir":  p.is_dir() if exists else None,
                    "is_file": p.is_file() if exists else None,
                    "parent":  str(p.parent),
                    "name":    p.name,
                },
                summary=f"Resolved: {str(p)} ({'exists' if exists else 'does not exist'})",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _dir_tree(
        self,
        path: str = ".",
        depth: int = 2,
        show_hidden: bool = False,
        **kwargs,
    ) -> ToolResult:
        """
        Recursive directory tree listing. Max depth capped at MAX_TREE_DEPTH.
        Returns both a structured list and a text representation.
        """
        depth = min(int(depth), MAX_TREE_DEPTH)
        try:
            p = Path(path).resolve()
            if not p.exists():
                return ToolResult(success=False, error=f"Path not found: {path}")

            tree_lines = []
            tree_data = []
            self._build_tree(p, depth, 0, "", tree_lines, tree_data, show_hidden)

            return ToolResult(
                success=True,
                data={"path": str(p), "depth": depth, "tree": tree_data},
                summary=f"Tree of {str(p)} (depth {depth}):\n" + "\n".join(tree_lines[:80]),
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _build_tree(
        self, path: Path, max_depth: int, current_depth: int,
        prefix: str, lines: list, data: list, show_hidden: bool,
    ):
        if current_depth > max_depth:
            return
        try:
            children = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        except PermissionError:
            return

        for i, child in enumerate(children):
            if not show_hidden and child.name.startswith("."):
                continue
            is_last = (i == len(children) - 1)
            connector = "└── " if is_last else "├── "
            icon = "📁 " if child.is_dir() else "📄 "
            lines.append(f"{prefix}{connector}{icon}{child.name}")
            data.append({
                "name": child.name,
                "type": "dir" if child.is_dir() else "file",
                "depth": current_depth,
            })
            if child.is_dir() and current_depth < max_depth:
                extension = "    " if is_last else "│   "
                self._build_tree(
                    child, max_depth, current_depth + 1,
                    prefix + extension, lines, data, show_hidden,
                )
