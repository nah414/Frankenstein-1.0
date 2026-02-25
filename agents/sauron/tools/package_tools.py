"""
FRANKENSTEIN 1.0 - Eye of Sauron: Package Tools
Phase 4 / Day 4: Development Tools

pip, npm, and conda package manager operations.
Replaces the terminal's pip/npm/conda pass-through commands with a structured,
permission-enforced surface that distinguishes read-only queries from installs.

Ring 3 (SAFE — no prompt, free execution):
    pip_list, pip_show, pip_freeze, pip_check
    npm_list, npm_outdated
    conda_list, conda_env_list

Ring 2 (SENSITIVE — always prompts for approval):
    pip_install, pip_uninstall, pip_upgrade
    npm_install, npm_uninstall, npm_run
    conda_install, conda_create, conda_remove

Limits:
    EXEC_TIMEOUT = 120s  (package downloads can be slow)
    MAX_OUTPUT   = 100 KB
"""

import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from agents.sauron.permissions import PermissionLevel, get_permission_manager
from agents.sauron.audit import SauronEvent, get_sauron_audit
from agents.sauron.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


# ── Limits ─────────────────────────────────────────────────────────────────────

EXEC_TIMEOUT    = 120       # Package downloads can be slow
MAX_OUTPUT_BYTES = 102_400  # 100 KB


# ── Package Tool ───────────────────────────────────────────────────────────────

class PackageTool(BaseTool):
    """
    Package manager operations (pip, npm, conda) for Eye of Sauron.

    Ring 3 actions are query-only and execute freely.
    Ring 2 actions modify the system and always require approval.
    """

    name = "package"
    description = (
        "Package manager operations (pip, npm, conda). "
        "Ring 3 (free): pip_list, pip_show, pip_freeze, pip_check, "
        "npm_list, npm_outdated, conda_list, conda_env_list. "
        "Ring 2 (approval): pip_install, pip_uninstall, pip_upgrade, "
        "npm_install, npm_uninstall, npm_run, "
        "conda_install, conda_create, conda_remove."
    )
    permission_level = PermissionLevel.SAFE  # base; Ring 2 actions self-manage

    def execute(self, action: str = "", **kwargs) -> ToolResult:
        if not action:
            return ToolResult(
                success=False,
                error=f"'action' is required. Valid actions: {sorted(self._dispatch().keys())}",
            )
        dispatch = self._dispatch()
        if action not in dispatch:
            return ToolResult(
                success=False,
                error=f"Unknown action '{action}'. Valid: {sorted(dispatch.keys())}",
            )
        return dispatch[action](**kwargs)

    def _dispatch(self) -> dict:
        return {
            # pip — Ring 3
            "pip_list":       self._pip_list,
            "pip_show":       self._pip_show,
            "pip_freeze":     self._pip_freeze,
            "pip_check":      self._pip_check,
            # pip — Ring 2
            "pip_install":    self._pip_install,
            "pip_uninstall":  self._pip_uninstall,
            "pip_upgrade":    self._pip_upgrade,
            # npm — Ring 3
            "npm_list":       self._npm_list,
            "npm_outdated":   self._npm_outdated,
            # npm — Ring 2
            "npm_install":    self._npm_install,
            "npm_uninstall":  self._npm_uninstall,
            "npm_run":        self._npm_run,
            # conda — Ring 3
            "conda_list":     self._conda_list,
            "conda_env_list": self._conda_env_list,
            # conda — Ring 2
            "conda_install":  self._conda_install,
            "conda_create":   self._conda_create,
            "conda_remove":   self._conda_remove,
        }

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

    def _run(self, args: List[str], cwd: Optional[str] = None) -> ToolResult:
        """Run a subprocess with standard package-manager limits."""
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=cwd,
                timeout=EXEC_TIMEOUT,
            )
            stdout = (result.stdout or "")[:MAX_OUTPUT_BYTES]
            stderr = (result.stderr or "")[:MAX_OUTPUT_BYTES]

            if len(result.stdout or "") > MAX_OUTPUT_BYTES:
                stdout += f"\n[stdout truncated at {MAX_OUTPUT_BYTES // 1024} KB]"
            if len(result.stderr or "") > MAX_OUTPUT_BYTES:
                stderr += f"\n[stderr truncated at {MAX_OUTPUT_BYTES // 1024} KB]"

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
                    f"Process exited with code {result.returncode}: {stderr[:200]}"
                ),
                summary=f"returncode={result.returncode}, stdout={len(stdout)}B",
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                error=f"Command timed out after {EXEC_TIMEOUT}s: {args[0]}",
            )
        except FileNotFoundError:
            return ToolResult(
                success=False,
                error=f"Command not found: '{args[0]}'. Is it installed and on PATH?",
            )
        except Exception as e:
            logger.error("PackageTool subprocess error: %s", e, exc_info=True)
            return ToolResult(success=False, error=str(e))

    def _npm_bin(self) -> Optional[str]:
        """Return the npm binary path, or None if not installed."""
        return shutil.which("npm")

    def _conda_bin(self) -> Optional[str]:
        """Return the conda binary path, or None if not installed."""
        return shutil.which("conda")

    def _require_npm(self) -> tuple:
        """Return (npm_path, None) or (None, ToolResult) if npm not found."""
        npm = self._npm_bin()
        if not npm:
            return None, ToolResult(
                success=False,
                error="npm not found in PATH. Is Node.js installed?",
            )
        return npm, None

    def _require_conda(self) -> tuple:
        """Return (conda_path, None) or (None, ToolResult) if conda not found."""
        conda = self._conda_bin()
        if not conda:
            return None, ToolResult(
                success=False,
                error="conda not found in PATH. Is Anaconda/Miniconda installed?",
            )
        return conda, None

    # ── pip: Ring 3 ────────────────────────────────────────────────────────────

    def _pip_list(self, format: str = "columns", **_) -> ToolResult:
        """
        pip list (Ring 3 — free). Lists all installed Python packages.

        Args:
            format : "columns" (default), "json", or "freeze"
        """
        args = [sys.executable, "-m", "pip", "list"]
        if format == "json":
            args.extend(["--format", "json"])
        elif format == "freeze":
            return self._pip_freeze()
        return self._run(args)

    def _pip_show(self, package: str = "", **_) -> ToolResult:
        """
        pip show <package> (Ring 3 — free). Shows package metadata.

        Args:
            package : Package name to inspect (required)
        """
        if not package:
            return ToolResult(success=False, error="'package' is required for pip_show.")
        return self._run([sys.executable, "-m", "pip", "show", package])

    def _pip_freeze(self, **_) -> ToolResult:
        """pip freeze (Ring 3 — free). Outputs requirements.txt format."""
        return self._run([sys.executable, "-m", "pip", "freeze"])

    def _pip_check(self, **_) -> ToolResult:
        """pip check (Ring 3 — free). Verifies dependency compatibility."""
        return self._run([sys.executable, "-m", "pip", "check"])

    # ── pip: Ring 2 ────────────────────────────────────────────────────────────

    def _pip_install(
        self,
        packages: Optional[List[str]] = None,
        requirements: Optional[str] = None,
        editable: bool = False,
        extra_args: Optional[List[str]] = None,
        **_,
    ) -> ToolResult:
        """
        pip install (Ring 2 — approval).

        Args:
            packages     : List of package names/specifiers (e.g. ["numpy>=2.0", "scipy"])
            requirements : Path to requirements file (-r flag; mutually exclusive with packages)
            editable     : Install in editable mode (-e flag; use with packages=["."])
            extra_args   : Additional pip install args (e.g. ["--no-deps"])
        """
        if not packages and not requirements:
            return ToolResult(
                success=False,
                error="Provide 'packages' list or 'requirements' file path.",
            )
        if packages and requirements:
            return ToolResult(
                success=False,
                error="Provide either 'packages' or 'requirements', not both.",
            )

        args = [sys.executable, "-m", "pip", "install"]
        if editable:
            args.append("-e")
        if requirements:
            args.extend(["-r", requirements])
            desc = f"pip install -r {requirements}"
        else:
            args.extend(packages)
            desc = f"pip install {' '.join(packages)}"
        if extra_args:
            args.extend(extra_args)

        if not self._approve("pip_install", desc):
            return ToolResult(
                success=False,
                error="pip_install denied by user.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        return self._run(args)

    def _pip_uninstall(self, packages: Optional[List[str]] = None, **_) -> ToolResult:
        """
        pip uninstall (Ring 2 — approval). Passes -y to skip interactive prompt.

        Args:
            packages : List of package names to remove (required)
        """
        if not packages:
            return ToolResult(
                success=False,
                error="'packages' list is required for pip_uninstall.",
            )

        desc = f"pip uninstall {' '.join(packages)}"
        if not self._approve("pip_uninstall", desc):
            return ToolResult(
                success=False,
                error="pip_uninstall denied by user.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        return self._run([sys.executable, "-m", "pip", "uninstall", "-y"] + list(packages))

    def _pip_upgrade(self, packages: Optional[List[str]] = None, **_) -> ToolResult:
        """
        pip install --upgrade (Ring 2 — approval).

        Args:
            packages : List of package names to upgrade (required)
        """
        if not packages:
            return ToolResult(
                success=False,
                error="'packages' list is required for pip_upgrade.",
            )

        desc = f"pip install --upgrade {' '.join(packages)}"
        if not self._approve("pip_upgrade", desc):
            return ToolResult(
                success=False,
                error="pip_upgrade denied by user.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        return self._run(
            [sys.executable, "-m", "pip", "install", "--upgrade"] + list(packages)
        )

    # ── npm: Ring 3 ────────────────────────────────────────────────────────────

    def _npm_list(
        self,
        cwd: Optional[str] = None,
        depth: int = 0,
        global_: bool = False,
        **_,
    ) -> ToolResult:
        """
        npm list (Ring 3 — free). Lists installed Node packages.

        Args:
            cwd    : Project directory (default: current directory)
            depth  : Dependency depth to display (default 0 = top-level only)
            global_: List globally installed packages (-g)
        """
        npm, err = self._require_npm()
        if err:
            return err

        args = [npm, "list", f"--depth={depth}"]
        if global_:
            args.append("-g")
        return self._run(args, cwd=cwd)

    def _npm_outdated(self, cwd: Optional[str] = None, **_) -> ToolResult:
        """
        npm outdated (Ring 3 — free). Lists packages with available updates.

        Args:
            cwd : Project directory (default: current directory)
        """
        npm, err = self._require_npm()
        if err:
            return err
        return self._run([npm, "outdated"], cwd=cwd)

    # ── npm: Ring 2 ────────────────────────────────────────────────────────────

    def _npm_install(
        self,
        packages: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        save_dev: bool = False,
        global_: bool = False,
        **_,
    ) -> ToolResult:
        """
        npm install (Ring 2 — approval).

        Args:
            packages : Specific packages to install (omit to install from package.json)
            cwd      : Project directory
            save_dev : Save as devDependency (--save-dev)
            global_  : Install globally (-g)
        """
        npm, err = self._require_npm()
        if err:
            return err

        args = [npm, "install"]
        if global_:
            args.append("-g")
        if save_dev:
            args.append("--save-dev")
        if packages:
            args.extend(packages)
            desc = f"npm install {' '.join(packages)}" + (" -g" if global_ else "")
        else:
            desc = "npm install (from package.json)" + (f" in {cwd}" if cwd else "")

        if not self._approve("npm_install", desc):
            return ToolResult(
                success=False,
                error="npm_install denied by user.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        return self._run(args, cwd=cwd)

    def _npm_uninstall(
        self,
        packages: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        global_: bool = False,
        **_,
    ) -> ToolResult:
        """
        npm uninstall (Ring 2 — approval).

        Args:
            packages : Package names to remove (required)
            cwd      : Project directory
            global_  : Uninstall globally (-g)
        """
        if not packages:
            return ToolResult(
                success=False,
                error="'packages' list is required for npm_uninstall.",
            )

        npm, err = self._require_npm()
        if err:
            return err

        args = [npm, "uninstall"]
        if global_:
            args.append("-g")
        args.extend(packages)

        desc = f"npm uninstall {' '.join(packages)}" + (" -g" if global_ else "")
        if not self._approve("npm_uninstall", desc):
            return ToolResult(
                success=False,
                error="npm_uninstall denied by user.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        return self._run(args, cwd=cwd)

    def _npm_run(self, script: str = "", cwd: Optional[str] = None, **_) -> ToolResult:
        """
        npm run <script> (Ring 2 — approval).
        Replaces the terminal's 'npm run' pass-through.

        Args:
            script : Script name from package.json (required)
            cwd    : Project directory
        """
        if not script:
            return ToolResult(
                success=False,
                error="'script' is required for npm_run.",
            )

        npm, err = self._require_npm()
        if err:
            return err

        cwd_note = f" in {cwd}" if cwd else ""
        desc = f"npm run {script}{cwd_note}"
        if not self._approve("npm_run", desc):
            return ToolResult(
                success=False,
                error="npm_run denied by user.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        return self._run([npm, "run", script], cwd=cwd)

    # ── conda: Ring 3 ──────────────────────────────────────────────────────────

    def _conda_list(self, env: Optional[str] = None, **_) -> ToolResult:
        """
        conda list (Ring 3 — free). Lists packages in an environment.

        Args:
            env : Environment name (default: active environment)
        """
        conda, err = self._require_conda()
        if err:
            return err

        args = [conda, "list"]
        if env:
            args.extend(["-n", env])
        return self._run(args)

    def _conda_env_list(self, **_) -> ToolResult:
        """conda env list (Ring 3 — free). Lists all conda environments."""
        conda, err = self._require_conda()
        if err:
            return err
        return self._run([conda, "env", "list"])

    # ── conda: Ring 2 ──────────────────────────────────────────────────────────

    def _conda_install(
        self,
        packages: Optional[List[str]] = None,
        env: Optional[str] = None,
        channel: Optional[str] = None,
        **_,
    ) -> ToolResult:
        """
        conda install (Ring 2 — approval).

        Args:
            packages : Package names to install (required)
            env      : Target environment name (default: active)
            channel  : Conda channel to use (e.g. "conda-forge")
        """
        if not packages:
            return ToolResult(
                success=False,
                error="'packages' list is required for conda_install.",
            )

        conda, err = self._require_conda()
        if err:
            return err

        args = [conda, "install", "-y"]
        if env:
            args.extend(["-n", env])
        if channel:
            args.extend(["-c", channel])
        args.extend(packages)

        env_note     = f" in env '{env}'" if env else ""
        channel_note = f" from channel '{channel}'" if channel else ""
        desc = f"conda install {' '.join(packages)}{env_note}{channel_note}"
        if not self._approve("conda_install", desc):
            return ToolResult(
                success=False,
                error="conda_install denied by user.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        return self._run(args)

    def _conda_create(
        self,
        env: str = "",
        packages: Optional[List[str]] = None,
        python_version: Optional[str] = None,
        **_,
    ) -> ToolResult:
        """
        conda create (Ring 2 — approval). Creates a new conda environment.

        Args:
            env            : New environment name (required)
            packages       : Packages to install in the new environment
            python_version : Python version (e.g. "3.11")
        """
        if not env:
            return ToolResult(
                success=False,
                error="'env' (environment name) is required for conda_create.",
            )

        conda, err = self._require_conda()
        if err:
            return err

        args = [conda, "create", "-y", "-n", env]
        if python_version:
            args.append(f"python={python_version}")
        if packages:
            args.extend(packages)

        py_note  = f" python={python_version}" if python_version else ""
        pkg_note = f" + {' '.join(packages)}" if packages else ""
        desc = f"conda create -n {env}{py_note}{pkg_note}"
        if not self._approve("conda_create", desc):
            return ToolResult(
                success=False,
                error="conda_create denied by user.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        return self._run(args)

    def _conda_remove(self, env: str = "", **_) -> ToolResult:
        """
        conda remove --all (Ring 2 — approval).
        Removes an entire conda environment. Irreversible.

        Args:
            env : Environment name to remove (required)
        """
        if not env:
            return ToolResult(
                success=False,
                error="'env' is required for conda_remove.",
            )

        conda, err = self._require_conda()
        if err:
            return err

        if not self._approve(
            "conda_remove",
            f"Remove conda environment '{env}' entirely ⚠️  — this is irreversible",
        ):
            return ToolResult(
                success=False,
                error="conda_remove denied by user.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        return self._run([conda, "remove", "-y", "-n", env, "--all"])
