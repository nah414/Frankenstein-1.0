"""
FRANKENSTEIN 1.0 - Eye of Sauron: Git Tools
Phase 4 / Day 4: Development Tools

Full Git coverage — mirrors the Frankenstein terminal's git command surface plus
a universal fallback (git_any) that passes any unknown subcommand to the system
git binary with Ring 2 approval.

Ring 3 (SAFE — no prompt, free execution):
    git_status, git_log, git_diff, git_branch, git_remote,
    git_show, git_stash_list, git_tag_list

Ring 2 (SENSITIVE — always prompts for approval):
    git_add, git_commit, git_push, git_pull, git_fetch,
    git_clone, git_checkout, git_reset, git_merge, git_rebase,
    git_stash, git_create_tag, git_delete_tag, git_any (fallback)

Limits:
    Local ops   : 30s timeout, 50 KB output cap
    Network ops : 60s timeout, 100 KB output cap (push/pull/fetch/clone)
"""

import logging
import subprocess
from pathlib import Path
from typing import List, Optional

from agents.sauron.permissions import PermissionLevel, get_permission_manager
from agents.sauron.audit import SauronEvent, get_sauron_audit
from agents.sauron.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


# ── Limits ─────────────────────────────────────────────────────────────────────

LOCAL_TIMEOUT   = 30
NETWORK_TIMEOUT = 60
LOCAL_CAP       = 51_200    # 50 KB
NETWORK_CAP     = 102_400   # 100 KB

NETWORK_SUBCOMMANDS = frozenset({"clone", "push", "pull", "fetch"})


# ── Git Tool ───────────────────────────────────────────────────────────────────

class GitTool(BaseTool):
    """
    Full Git operations for Eye of Sauron.

    Dispatch via action= parameter. Ring 3 actions execute freely.
    Ring 2 actions call _approve() which blocks until the user answers Y/n.
    The git_any fallback covers any subcommand not in the explicit list.
    """

    name = "git"
    description = (
        "Full Git operations. "
        "Ring 3 (free): git_status, git_log, git_diff, git_branch, git_remote, "
        "git_show, git_stash_list, git_tag_list. "
        "Ring 2 (approval): git_add, git_commit, git_push, git_pull, git_fetch, "
        "git_clone, git_checkout, git_reset, git_merge, git_rebase, "
        "git_stash, git_create_tag, git_delete_tag, git_any (universal fallback)."
    )
    permission_level = PermissionLevel.SAFE  # base; Ring 2 actions self-manage

    def execute(self, action: str = "git_status", **kwargs) -> ToolResult:
        dispatch = {
            # ── Ring 3: reads ──────────────────────────────────────────────────
            "git_status":     self._git_status,
            "git_log":        self._git_log,
            "git_diff":       self._git_diff,
            "git_branch":     self._git_branch,
            "git_remote":     self._git_remote,
            "git_show":       self._git_show,
            "git_stash_list": self._git_stash_list,
            "git_tag_list":   self._git_tag_list,
            # ── Ring 2: writes / network ───────────────────────────────────────
            "git_add":        self._git_add,
            "git_commit":     self._git_commit,
            "git_push":       self._git_push,
            "git_pull":       self._git_pull,
            "git_fetch":      self._git_fetch,
            "git_clone":      self._git_clone,
            "git_checkout":   self._git_checkout,
            "git_reset":      self._git_reset,
            "git_merge":      self._git_merge,
            "git_rebase":     self._git_rebase,
            "git_stash":      self._git_stash,
            "git_create_tag": self._git_create_tag,
            "git_delete_tag": self._git_delete_tag,
            "git_any":        self._git_any,
        }
        if action not in dispatch:
            return ToolResult(
                success=False,
                error=f"Unknown git action '{action}'. Valid: {sorted(dispatch)}",
            )
        return dispatch[action](**kwargs)

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _run_git(
        self,
        args: List[str],
        cwd: Optional[str] = None,
        network: bool = False,
    ) -> ToolResult:
        """
        Run a git subprocess and return a ToolResult.
        cwd defaults to Path.cwd() if not provided.
        Applies output cap and timeout based on whether this is a network op.
        """
        cwd_path = Path(cwd).resolve() if cwd else Path.cwd()
        timeout = NETWORK_TIMEOUT if network else LOCAL_TIMEOUT
        cap     = NETWORK_CAP     if network else LOCAL_CAP

        try:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(cwd_path),
                timeout=timeout,
            )
            stdout = result.stdout or ""
            stderr = result.stderr or ""

            if len(stdout) > cap:
                stdout = stdout[:cap] + f"\n[stdout truncated at {cap // 1024} KB]"
            if len(stderr) > cap:
                stderr = stderr[:cap] + f"\n[stderr truncated at {cap // 1024} KB]"

            success = result.returncode == 0
            return ToolResult(
                success=success,
                data={
                    "stdout":     stdout,
                    "stderr":     stderr,
                    "returncode": result.returncode,
                    "args":       args,
                    "cwd":        str(cwd_path),
                },
                error=None if success else (
                    f"git exited with code {result.returncode}: {stderr[:200]}"
                ),
                summary=f"git {args[0] if args else '?'}: rc={result.returncode}",
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                error=f"git {args[0] if args else '?'} timed out after {timeout}s",
            )
        except FileNotFoundError:
            return ToolResult(
                success=False,
                error="git binary not found. Is git installed and on PATH?",
            )
        except Exception as e:
            logger.error("git subprocess error: %s", e, exc_info=True)
            return ToolResult(success=False, error=str(e))

    def _approve(self, action_name: str, description: str) -> bool:
        """
        Request Ring 2 approval at the terminal. Blocks until answered.
        Returns True if approved, False if denied.
        """
        audit = get_sauron_audit()
        pm    = get_permission_manager()
        audit.log_permission(SauronEvent.PERMISSION_ASK, action_name, description)
        approved = pm.request_permission(action_name, description)
        event = SauronEvent.PERMISSION_GRANT if approved else SauronEvent.PERMISSION_DENY
        audit.log_permission(event, action_name, description)
        return approved

    def _cwd_str(self, cwd: Optional[str]) -> str:
        """Resolve cwd to an absolute string for display in prompts."""
        return str(Path(cwd).resolve() if cwd else Path.cwd())

    # ── Ring 3: Read Operations ────────────────────────────────────────────────

    def _git_status(self, cwd: Optional[str] = None, **_) -> ToolResult:
        """
        git status (Ring 3 — free). Returns both structured dict and raw output.

        Structured data keys: branch, staged, modified, untracked, clean.
        """
        result = self._run_git(["status", "--porcelain", "-b"], cwd=cwd)
        if not result.success:
            return result

        raw = result.data["stdout"].strip()
        lines = raw.split("\n") if raw else []
        branch_line = lines[0][3:] if lines and lines[0].startswith("##") else "unknown"

        staged, modified, untracked = [], [], []
        for line in lines[1:]:
            if not line.strip():
                continue
            st, fname = line[:2], line[3:]
            if st[0] in "MARCDU":
                staged.append({"status": st[0], "file": fname})
            elif st[1] == "M":
                modified.append(fname)
            elif st == "??":
                untracked.append(fname)

        data = {
            "branch":    branch_line,
            "staged":    staged,
            "modified":  modified,
            "untracked": untracked,
            "clean":     not (staged or modified or untracked),
            "raw":       raw,
        }
        summary = (
            f"Branch: {branch_line} | "
            f"staged={len(staged)}, modified={len(modified)}, untracked={len(untracked)}"
        )
        return ToolResult(success=True, data=data, summary=summary)

    def _git_log(
        self,
        cwd: Optional[str] = None,
        n: int = 20,
        graph: bool = True,
        oneline: bool = True,
        extra_args: Optional[List[str]] = None,
        **_,
    ) -> ToolResult:
        """
        git log (Ring 3 — free).

        Args:
            n          : Number of commits to show (default 20)
            graph      : Show ASCII graph (default True)
            oneline    : One line per commit (default True)
            extra_args : Additional git log args (e.g. ["--author=Adam"])
        """
        args = ["log", f"-{n}", "--decorate"]
        if graph:
            args.append("--graph")
        if oneline:
            args.append("--oneline")
        if extra_args:
            args.extend(extra_args)
        return self._run_git(args, cwd=cwd)

    def _git_diff(
        self,
        cwd: Optional[str] = None,
        staged: bool = False,
        file: Optional[str] = None,
        ref: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        **_,
    ) -> ToolResult:
        """
        git diff (Ring 3 — free).

        Args:
            staged     : Show staged changes (--cached)
            file       : Limit diff to a single file
            ref        : Compare against a specific commit/branch
            extra_args : Additional git diff args
        """
        args = ["diff"]
        if staged:
            args.append("--cached")
        if ref:
            args.append(ref)
        if extra_args:
            args.extend(extra_args)
        if file:
            args.extend(["--", file])
        return self._run_git(args, cwd=cwd)

    def _git_branch(
        self,
        cwd: Optional[str] = None,
        all: bool = True,
        verbose: bool = True,
        **_,
    ) -> ToolResult:
        """
        git branch (Ring 3 — free). Lists local and remote branches.

        Args:
            all     : Include remote branches (-a, default True)
            verbose : Show last commit per branch (-v, default True)
        """
        args = ["branch"]
        if all:
            args.append("-a")
        if verbose:
            args.append("-v")
        return self._run_git(args, cwd=cwd)

    def _git_remote(
        self,
        cwd: Optional[str] = None,
        verbose: bool = True,
        **_,
    ) -> ToolResult:
        """git remote -v (Ring 3 — free). Lists configured remotes."""
        args = ["remote"]
        if verbose:
            args.append("-v")
        return self._run_git(args, cwd=cwd)

    def _git_show(
        self,
        cwd: Optional[str] = None,
        ref: str = "HEAD",
        stat: bool = True,
        extra_args: Optional[List[str]] = None,
        **_,
    ) -> ToolResult:
        """
        git show <ref> (Ring 3 — free). Shows commit details.

        Args:
            ref        : Commit hash, tag, or branch (default HEAD)
            stat       : Include --stat summary (default True)
            extra_args : Additional git show args
        """
        args = ["show", ref]
        if stat:
            args.append("--stat")
        if extra_args:
            args.extend(extra_args)
        return self._run_git(args, cwd=cwd)

    def _git_stash_list(self, cwd: Optional[str] = None, **_) -> ToolResult:
        """git stash list (Ring 3 — free). Lists all stash entries."""
        return self._run_git(["stash", "list"], cwd=cwd)

    def _git_tag_list(
        self,
        cwd: Optional[str] = None,
        sort: str = "-version:refname",
        **_,
    ) -> ToolResult:
        """git tag -l (Ring 3 — free). Lists all tags, newest first."""
        return self._run_git(["tag", "-l", f"--sort={sort}"], cwd=cwd)

    # ── Ring 2: Write / Network Operations ────────────────────────────────────

    def _git_add(
        self,
        cwd: Optional[str] = None,
        files: Optional[List[str]] = None,
        all: bool = False,
        **_,
    ) -> ToolResult:
        """
        git add (Ring 2 — approval).

        Args:
            files : List of file paths to stage
            all   : Stage all changes (git add -A)
        """
        if all:
            files_desc = "all changes (git add -A)"
            args = ["add", "-A"]
        elif files:
            files_desc = ", ".join(files)
            args = ["add"] + files
        else:
            return ToolResult(
                success=False,
                error="Provide 'files' list or set 'all=True'.",
            )

        desc = f"Stage for commit: {files_desc} in {self._cwd_str(cwd)}"
        if not self._approve("git_add", desc):
            return ToolResult(
                success=False,
                error="git_add denied by user.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        return self._run_git(args, cwd=cwd)

    def _git_commit(
        self,
        cwd: Optional[str] = None,
        message: str = "",
        amend: bool = False,
        **_,
    ) -> ToolResult:
        """
        git commit (Ring 2 — approval).

        Args:
            message : Commit message (required unless amend=True)
            amend   : Amend the last commit (--amend)
        """
        if not message and not amend:
            return ToolResult(
                success=False,
                error="'message' is required for git_commit (or set amend=True).",
            )

        args = ["commit"]
        if amend:
            args.append("--amend")
        if message:
            args.extend(["-m", message])

        desc = f"Commit: '{message[:80]}'" if message else "Amend last commit"
        if not self._approve("git_commit", f"{desc} in {self._cwd_str(cwd)}"):
            return ToolResult(
                success=False,
                error="git_commit denied.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        return self._run_git(args, cwd=cwd)

    def _git_push(
        self,
        cwd: Optional[str] = None,
        remote: str = "origin",
        branch: Optional[str] = None,
        force: bool = False,
        set_upstream: bool = False,
        **_,
    ) -> ToolResult:
        """
        git push (Ring 2 — approval). Warns clearly on force push.

        Args:
            remote       : Remote name (default "origin")
            branch       : Branch to push (default: current branch)
            force        : Add --force flag; shown as ⚠️ WARNING in prompt
            set_upstream : Add --set-upstream (-u) flag
        """
        args = ["push"]
        if set_upstream:
            args.append("--set-upstream")
        if force:
            args.append("--force")
        args.append(remote)
        if branch:
            args.append(branch)

        force_warn = " ⚠️  FORCE PUSH — rewrites remote history" if force else ""
        desc = (
            f"Push to {remote}/{branch or 'current branch'}{force_warn} "
            f"from {self._cwd_str(cwd)}"
        )
        if not self._approve("git_push", desc):
            return ToolResult(
                success=False,
                error="git_push denied.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        return self._run_git(args, cwd=cwd, network=True)

    def _git_pull(
        self,
        cwd: Optional[str] = None,
        remote: str = "origin",
        branch: Optional[str] = None,
        rebase: bool = False,
        **_,
    ) -> ToolResult:
        """
        git pull (Ring 2 — approval).

        Args:
            remote : Remote name (default "origin")
            branch : Branch to pull (default: current tracking branch)
            rebase : Use --rebase instead of merge
        """
        args = ["pull"]
        if rebase:
            args.append("--rebase")
        args.append(remote)
        if branch:
            args.append(branch)

        desc = f"Pull from {remote}/{branch or 'current'} in {self._cwd_str(cwd)}"
        if not self._approve("git_pull", desc):
            return ToolResult(
                success=False,
                error="git_pull denied.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        return self._run_git(args, cwd=cwd, network=True)

    def _git_fetch(
        self,
        cwd: Optional[str] = None,
        remote: str = "origin",
        all_remotes: bool = False,
        prune: bool = False,
        **_,
    ) -> ToolResult:
        """
        git fetch (Ring 2 — approval).

        Args:
            remote      : Remote to fetch (default "origin")
            all_remotes : Fetch all remotes (--all)
            prune       : Prune deleted remote branches (--prune)
        """
        args = ["fetch"]
        if all_remotes:
            args.append("--all")
        else:
            args.append(remote)
        if prune:
            args.append("--prune")

        target = "all remotes" if all_remotes else remote
        prune_note = " (with --prune)" if prune else ""
        desc = f"Fetch {target}{prune_note} in {self._cwd_str(cwd)}"
        if not self._approve("git_fetch", desc):
            return ToolResult(
                success=False,
                error="git_fetch denied.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        return self._run_git(args, cwd=cwd, network=True)

    def _git_clone(
        self,
        url: str = "",
        dest: Optional[str] = None,
        cwd: Optional[str] = None,
        depth: Optional[int] = None,
        **_,
    ) -> ToolResult:
        """
        git clone (Ring 2 — approval).

        Args:
            url   : Repository URL to clone
            dest  : Local directory name (default: derived from URL)
            cwd   : Working directory for clone
            depth : Shallow clone with --depth N
        """
        if not url:
            return ToolResult(success=False, error="'url' is required for git_clone.")

        args = ["clone", "--progress"]
        if depth:
            args.extend(["--depth", str(depth)])
        args.append(url)
        if dest:
            args.append(dest)

        dest_display = dest or url.rstrip("/").split("/")[-1]
        depth_note = f" (shallow --depth {depth})" if depth else ""
        desc = f"Clone {url} → {dest_display}{depth_note} in {self._cwd_str(cwd)}"
        if not self._approve("git_clone", desc):
            return ToolResult(
                success=False,
                error="git_clone denied.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        return self._run_git(args, cwd=cwd, network=True)

    def _git_checkout(
        self,
        cwd: Optional[str] = None,
        target: str = "",
        create: bool = False,
        **_,
    ) -> ToolResult:
        """
        git checkout (Ring 2 — approval).

        Args:
            target : Branch name, file path, or commit ref
            create : Create new branch (-b flag)
        """
        if not target:
            return ToolResult(
                success=False,
                error="'target' (branch/file/commit) is required for git_checkout.",
            )

        args = ["checkout"]
        if create:
            args.append("-b")
        args.append(target)

        action_str = f"Create and switch to new branch '{target}'" if create else f"Checkout '{target}'"
        if not self._approve("git_checkout", f"{action_str} in {self._cwd_str(cwd)}"):
            return ToolResult(
                success=False,
                error="git_checkout denied.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        return self._run_git(args, cwd=cwd)

    def _git_reset(
        self,
        cwd: Optional[str] = None,
        mode: str = "--mixed",
        ref: str = "HEAD",
        **_,
    ) -> ToolResult:
        """
        git reset (Ring 2 — approval). Hard mode gets an explicit warning.

        Args:
            mode : --soft, --mixed (default), or --hard
            ref  : Commit to reset to (default HEAD)
        """
        valid_modes = {"--soft", "--mixed", "--hard"}
        if mode not in valid_modes:
            return ToolResult(
                success=False,
                error=f"Invalid mode '{mode}'. Must be one of: {valid_modes}",
            )

        args = ["reset", mode, ref]
        hard_warn = " ⚠️  HARD RESET — working tree changes will be discarded" if mode == "--hard" else ""
        desc = f"Reset {mode} to {ref}{hard_warn} in {self._cwd_str(cwd)}"
        if not self._approve("git_reset", desc):
            return ToolResult(
                success=False,
                error="git_reset denied.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        return self._run_git(args, cwd=cwd)

    def _git_merge(
        self,
        cwd: Optional[str] = None,
        branch: str = "",
        no_ff: bool = False,
        squash: bool = False,
        **_,
    ) -> ToolResult:
        """
        git merge (Ring 2 — approval).

        Args:
            branch : Branch to merge into current
            no_ff  : Disable fast-forward (--no-ff)
            squash : Squash all commits into one (--squash)
        """
        if not branch:
            return ToolResult(success=False, error="'branch' is required for git_merge.")

        args = ["merge"]
        if no_ff:
            args.append("--no-ff")
        if squash:
            args.append("--squash")
        args.append(branch)

        flags = " ".join(f for f in ["--no-ff" if no_ff else "", "--squash" if squash else ""] if f)
        desc = f"Merge '{branch}' {flags} into current branch in {self._cwd_str(cwd)}"
        if not self._approve("git_merge", desc):
            return ToolResult(
                success=False,
                error="git_merge denied.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        return self._run_git(args, cwd=cwd)

    def _git_rebase(
        self,
        cwd: Optional[str] = None,
        branch: str = "",
        abort: bool = False,
        continue_: bool = False,
        **_,
    ) -> ToolResult:
        """
        git rebase (Ring 2 — approval). Non-interactive only.

        Args:
            branch    : Branch to rebase onto (required unless abort/continue_)
            abort     : Run git rebase --abort
            continue_ : Run git rebase --continue
        """
        if abort:
            args = ["rebase", "--abort"]
            desc = f"Abort in-progress rebase in {self._cwd_str(cwd)}"
        elif continue_:
            args = ["rebase", "--continue"]
            desc = f"Continue in-progress rebase in {self._cwd_str(cwd)}"
        else:
            if not branch:
                return ToolResult(
                    success=False,
                    error="'branch' is required for git_rebase (or set abort=True / continue_=True).",
                )
            args = ["rebase", branch]
            desc = f"Rebase current branch onto '{branch}' in {self._cwd_str(cwd)}"

        if not self._approve("git_rebase", desc):
            return ToolResult(
                success=False,
                error="git_rebase denied.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        return self._run_git(args, cwd=cwd)

    def _git_stash(
        self,
        cwd: Optional[str] = None,
        subaction: str = "push",
        message: Optional[str] = None,
        stash_ref: Optional[str] = None,
        **_,
    ) -> ToolResult:
        """
        git stash push/pop/apply/drop/clear (Ring 2 — approval).

        Args:
            subaction : "push" (default), "pop", "apply", "drop", "clear"
            message   : Stash message (used with subaction="push")
            stash_ref : Stash reference e.g. "stash@{0}" (used with apply/drop)
        """
        valid = {"push", "pop", "apply", "drop", "clear"}
        if subaction not in valid:
            return ToolResult(
                success=False,
                error=f"Invalid stash subaction '{subaction}'. Must be one of: {valid}",
            )

        args = ["stash", subaction]
        if subaction == "push" and message:
            args.extend(["-m", message])
        if stash_ref and subaction in ("apply", "drop"):
            args.append(stash_ref)

        msg_part = f" '{message}'" if message else ""
        ref_part = f" {stash_ref}" if stash_ref else ""
        desc = f"git stash {subaction}{msg_part}{ref_part} in {self._cwd_str(cwd)}"
        if not self._approve("git_stash", desc):
            return ToolResult(
                success=False,
                error="git_stash denied.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        return self._run_git(args, cwd=cwd)

    def _git_create_tag(
        self,
        cwd: Optional[str] = None,
        name: str = "",
        message: Optional[str] = None,
        ref: str = "HEAD",
        **_,
    ) -> ToolResult:
        """
        git tag (create). Ring 2 — approval.

        Args:
            name    : Tag name (required)
            message : Annotation message — creates annotated tag (-a -m)
            ref     : Commit to tag (default HEAD)
        """
        if not name:
            return ToolResult(success=False, error="'name' is required for git_create_tag.")

        args = ["tag"]
        if message:
            args.extend(["-a", name, "-m", message])
        else:
            args.append(name)
        if ref != "HEAD":
            args.append(ref)

        tag_type = "annotated" if message else "lightweight"
        ref_note = f" on {ref}" if ref != "HEAD" else ""
        desc = f"Create {tag_type} tag '{name}'{ref_note} in {self._cwd_str(cwd)}"
        if not self._approve("git_create_tag", desc):
            return ToolResult(
                success=False,
                error="git_create_tag denied.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        return self._run_git(args, cwd=cwd)

    def _git_delete_tag(
        self,
        cwd: Optional[str] = None,
        name: str = "",
        **_,
    ) -> ToolResult:
        """
        git tag -d (delete local tag). Ring 2 — approval.

        Args:
            name : Tag name to delete (required)
        """
        if not name:
            return ToolResult(success=False, error="'name' is required for git_delete_tag.")

        if not self._approve("git_delete_tag", f"Delete local tag '{name}' in {self._cwd_str(cwd)}"):
            return ToolResult(
                success=False,
                error="git_delete_tag denied.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        return self._run_git(["tag", "-d", name], cwd=cwd)

    def _git_any(
        self,
        cwd: Optional[str] = None,
        subcommand: str = "",
        args: Optional[List[str]] = None,
        **_,
    ) -> ToolResult:
        """
        Universal git fallback. Passes any subcommand + args to the system git
        binary. Always Ring 2 — requires approval regardless of subcommand.

        Use this for: git cherry-pick, git bisect, git reflog, git gc,
        git config, git submodule, or any other git operation not listed above.

        Args:
            subcommand : git subcommand (e.g. "cherry-pick", "reflog")
            args       : Additional arguments (e.g. ["abc1234"])
        """
        if not subcommand:
            return ToolResult(
                success=False,
                error="'subcommand' is required for git_any. Example: subcommand='cherry-pick', args=['abc1234']",
            )

        full_args = [subcommand] + (args or [])
        is_network = subcommand.lower() in NETWORK_SUBCOMMANDS
        full_cmd   = "git " + " ".join(full_args)

        desc = f"{full_cmd} in {self._cwd_str(cwd)}"
        if not self._approve("git_any", desc):
            return ToolResult(
                success=False,
                error="git_any denied.",
                permission_level=PermissionLevel.SENSITIVE,
            )
        return self._run_git(full_args, cwd=cwd, network=is_network)
