"""
FRANKENSTEIN 1.0 - Eye of Sauron: Search Tools
Phase 4 / Day 3: Tool Framework

File search (glob pattern) and content search (grep).
All operations are Ring 3 (SAFE) — read-only filesystem queries.
"""

import fnmatch
import logging
import os
import re
from pathlib import Path
from typing import Optional

from agents.sauron.permissions import PermissionLevel
from agents.sauron.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


# Max results returned per search to keep LLM context manageable
MAX_FILE_RESULTS = 200
MAX_GREP_RESULTS = 100
MAX_GREP_LINE_LEN = 300   # chars — truncate long lines in output
MAX_FILE_SIZE_GREP = 10_485_760  # 10 MB — skip larger files


class SearchTool(BaseTool):
    """
    Search operations for Eye of Sauron. All Ring 3 (SAFE).

    Actions:
      file_search    — find files/dirs by glob pattern under a root path
      content_search — grep file contents, return matches with line numbers
    """

    name = "search"
    description = (
        "File and content search: glob pattern matching (file_search) and "
        "grep-style content search with line numbers (content_search). "
        "Both Ring 3 (SAFE — no approval needed). Read-only."
    )
    permission_level = PermissionLevel.SAFE

    def execute(self, action: str = "file_search", **kwargs) -> ToolResult:
        dispatch = {
            "file_search":    self._file_search,
            "content_search": self._content_search,
        }
        if action not in dispatch:
            return ToolResult(
                success=False,
                error=f"Unknown search action '{action}'. Valid: {sorted(dispatch)}",
            )
        return dispatch[action](**kwargs)

    # ── file_search ────────────────────────────────────────────────────────────

    def _file_search(
        self,
        pattern: str = "*",
        root: str = ".",
        max_depth: Optional[int] = None,
        include_dirs: bool = True,
        **kwargs,
    ) -> ToolResult:
        """
        Recursively find files (and optionally dirs) matching a glob pattern
        under root. Returns sorted list of matching paths with metadata.

        Args:
            pattern    : Glob pattern, e.g. "*.py", "test_*", "**/*.json"
            root       : Directory to search under (default: current dir)
            max_depth  : Limit recursion depth (None = unlimited)
            include_dirs: Include matching directories in results (default True)
        """
        try:
            root_path = Path(root).resolve()
            if not root_path.exists():
                return ToolResult(success=False, error=f"Root path not found: {root}")
            if not root_path.is_dir():
                return ToolResult(success=False, error=f"Root must be a directory: {root}")

            matches = []
            skipped_permission = 0

            for dirpath, dirnames, filenames in os.walk(root_path):
                # Depth check
                if max_depth is not None:
                    rel = Path(dirpath).relative_to(root_path)
                    depth = len(rel.parts)
                    if depth > max_depth:
                        dirnames.clear()
                        continue

                # Sort for deterministic output; skip hidden
                dirnames.sort()

                current_dir = Path(dirpath)

                # Check files
                for fname in sorted(filenames):
                    if fnmatch.fnmatch(fname, pattern) or fnmatch.fnmatch(
                        str(current_dir / fname), pattern
                    ):
                        try:
                            fp = current_dir / fname
                            stat = fp.stat()
                            matches.append({
                                "path": str(fp),
                                "type": "file",
                                "size_bytes": stat.st_size,
                                "modified": stat.st_mtime,
                            })
                        except PermissionError:
                            skipped_permission += 1

                # Check dirs if requested
                if include_dirs:
                    for dname in dirnames:
                        if fnmatch.fnmatch(dname, pattern):
                            try:
                                dp = current_dir / dname
                                stat = dp.stat()
                                matches.append({
                                    "path": str(dp),
                                    "type": "dir",
                                    "size_bytes": None,
                                    "modified": stat.st_mtime,
                                })
                            except PermissionError:
                                skipped_permission += 1

                if len(matches) >= MAX_FILE_RESULTS:
                    matches = matches[:MAX_FILE_RESULTS]
                    truncated = True
                    break
            else:
                truncated = False

            summary_parts = [
                f"Found {len(matches)} match(es) for '{pattern}' under {str(root_path)}."
            ]
            if truncated:
                summary_parts.append(f"Results truncated at {MAX_FILE_RESULTS}.")
            if skipped_permission:
                summary_parts.append(f"{skipped_permission} path(s) skipped (permission denied).")

            return ToolResult(
                success=True,
                data={
                    "root": str(root_path),
                    "pattern": pattern,
                    "matches": matches,
                    "count": len(matches),
                    "truncated": truncated,
                    "skipped_permission": skipped_permission,
                },
                summary=" ".join(summary_parts),
            )

        except Exception as e:
            logger.error("file_search error: %s", e, exc_info=True)
            return ToolResult(success=False, error=str(e))

    # ── content_search ─────────────────────────────────────────────────────────

    def _content_search(
        self,
        pattern: str = "",
        root: str = ".",
        file_pattern: str = "*",
        case_sensitive: bool = True,
        max_depth: Optional[int] = None,
        context_lines: int = 0,
        **kwargs,
    ) -> ToolResult:
        """
        Grep file contents for a regex pattern. Returns matching lines with
        file path and line number.

        Args:
            pattern       : Regex pattern to search for
            root          : Directory to search under (default: current dir)
            file_pattern  : Glob filter for files to search (e.g. "*.py")
            case_sensitive: Case-sensitive match (default True)
            max_depth     : Limit recursion depth
            context_lines : Lines of context before/after each match (0 = match only)
        """
        if not pattern:
            return ToolResult(success=False, error="'pattern' is required for content_search")

        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            compiled = re.compile(pattern, flags)
        except re.error as e:
            return ToolResult(success=False, error=f"Invalid regex pattern: {e}")

        try:
            root_path = Path(root).resolve()
            if not root_path.exists():
                return ToolResult(success=False, error=f"Root path not found: {root}")
            if not root_path.is_dir():
                return ToolResult(success=False, error=f"Root must be a directory: {root}")

            results = []
            files_searched = 0
            files_skipped_size = 0
            files_skipped_binary = 0
            files_skipped_permission = 0
            total_matches = 0

            for dirpath, dirnames, filenames in os.walk(root_path):
                if max_depth is not None:
                    rel = Path(dirpath).relative_to(root_path)
                    if len(rel.parts) > max_depth:
                        dirnames.clear()
                        continue
                dirnames.sort()

                for fname in sorted(filenames):
                    if not fnmatch.fnmatch(fname, file_pattern):
                        continue

                    fp = Path(dirpath) / fname

                    try:
                        size = fp.stat().st_size
                    except PermissionError:
                        files_skipped_permission += 1
                        continue

                    if size > MAX_FILE_SIZE_GREP:
                        files_skipped_size += 1
                        continue

                    try:
                        text = fp.read_text(encoding="utf-8", errors="replace")
                    except PermissionError:
                        files_skipped_permission += 1
                        continue
                    except Exception:
                        files_skipped_binary += 1
                        continue

                    files_searched += 1
                    lines = text.splitlines()
                    file_hits = []

                    for lineno, line in enumerate(lines, start=1):
                        if compiled.search(line):
                            # Build context block
                            ctx_start = max(0, lineno - 1 - context_lines)
                            ctx_end = min(len(lines), lineno + context_lines)
                            ctx_block = []
                            for ci in range(ctx_start, ctx_end):
                                ctx_line = lines[ci]
                                if len(ctx_line) > MAX_GREP_LINE_LEN:
                                    ctx_line = ctx_line[:MAX_GREP_LINE_LEN] + "…"
                                ctx_block.append({
                                    "lineno": ci + 1,
                                    "text": ctx_line,
                                    "is_match": (ci + 1) == lineno,
                                })
                            file_hits.append({
                                "lineno": lineno,
                                "text": (
                                    line[:MAX_GREP_LINE_LEN] + "…"
                                    if len(line) > MAX_GREP_LINE_LEN
                                    else line
                                ),
                                "context": ctx_block if context_lines > 0 else [],
                            })
                            total_matches += 1

                    if file_hits:
                        results.append({
                            "file": str(fp),
                            "hit_count": len(file_hits),
                            "hits": file_hits,
                        })

                    if total_matches >= MAX_GREP_RESULTS:
                        break  # inner filenames loop

                if total_matches >= MAX_GREP_RESULTS:
                    truncated = True
                    break
            else:
                truncated = False

            summary_parts = [
                f"Pattern '{pattern}': {total_matches} match(es) in {len(results)} file(s) "
                f"({files_searched} searched)."
            ]
            if truncated:
                summary_parts.append(f"Truncated at {MAX_GREP_RESULTS} matches.")
            if files_skipped_size:
                summary_parts.append(f"{files_skipped_size} file(s) skipped (>10MB).")
            if files_skipped_binary:
                summary_parts.append(f"{files_skipped_binary} file(s) skipped (binary/unreadable).")
            if files_skipped_permission:
                summary_parts.append(f"{files_skipped_permission} file(s) skipped (permission denied).")

            return ToolResult(
                success=True,
                data={
                    "root": str(root_path),
                    "pattern": pattern,
                    "file_pattern": file_pattern,
                    "case_sensitive": case_sensitive,
                    "results": results,
                    "total_matches": total_matches,
                    "files_searched": files_searched,
                    "truncated": truncated,
                },
                summary=" ".join(summary_parts),
            )

        except Exception as e:
            logger.error("content_search error: %s", e, exc_info=True)
            return ToolResult(success=False, error=str(e))
