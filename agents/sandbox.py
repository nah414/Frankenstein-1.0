"""
FRANKENSTEIN Agents - Sandbox Execution
Isolated environment for running agents safely
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager


class Sandbox:
    """
    Sandbox environment for agent execution.
    Provides isolated workspace with resource limits.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path.home() / ".frankenstein" / "sandbox"
        self.workspace = self.base_dir / "workspace"
        self.temp_dir = self.base_dir / "temp"
        self.output_dir = self.base_dir / "output"

        # Create directories
        for d in [self.workspace, self.temp_dir, self.output_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # Allowed paths for file access
        self._allowed_paths = [self.workspace, self.temp_dir, self.output_dir]

    def is_path_allowed(self, path: Path) -> bool:
        """Check if a path is within allowed sandbox directories"""
        path = Path(path).resolve()
        return any(
            str(path).startswith(str(allowed.resolve()))
            for allowed in self._allowed_paths
        )

    def get_workspace_path(self, filename: str) -> Path:
        """Get a safe path within workspace"""
        # Prevent path traversal
        safe_name = os.path.basename(filename)
        return self.workspace / safe_name

    @contextmanager
    def temp_workspace(self):
        """Create temporary workspace that auto-cleans"""
        temp_path = Path(tempfile.mkdtemp(dir=self.temp_dir))
        try:
            yield temp_path
        finally:
            shutil.rmtree(temp_path, ignore_errors=True)

    def cleanup_old_files(self, max_age_hours: int = 24):
        """Clean up old temporary files"""
        import time
        cutoff = time.time() - (max_age_hours * 3600)

        for path in self.temp_dir.iterdir():
            if path.stat().st_mtime < cutoff:
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink(missing_ok=True)

    def get_status(self) -> Dict[str, Any]:
        """Get sandbox status"""
        def dir_size(path):
            total = 0
            for p in path.rglob("*"):
                if p.is_file():
                    total += p.stat().st_size
            return total

        return {
            "workspace_size_mb": dir_size(self.workspace) / (1024 * 1024),
            "temp_size_mb": dir_size(self.temp_dir) / (1024 * 1024),
            "output_size_mb": dir_size(self.output_dir) / (1024 * 1024),
        }


# Global sandbox
_sandbox: Optional[Sandbox] = None

def get_sandbox() -> Sandbox:
    global _sandbox
    if _sandbox is None:
        _sandbox = Sandbox()
    return _sandbox
