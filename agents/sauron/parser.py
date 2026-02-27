"""
FRANKENSTEIN 1.0 - Eye of Sauron: Intent Parser
Phase 4 / Day 5: Natural Language → Tool Calls

Converts a conversation message list into a structured ParsedIntent using
Ollama's native function calling API with Qwen 2.5 7B Instruct.

The parser owns the tool schema definitions. Each tool is represented as one
Ollama function with an `action` enum listing all valid sub-actions plus the
key parameters for those actions. All schemas are defined as module-level
constants so they can be inspected or updated without touching parser logic.

Usage:
    parser = IntentParser()
    intent = parser.parse_from_messages(messages)
    if intent.has_tool_call:
        # Route to tool registry
        result = registry.execute(intent.tool_name, **intent.arguments)
    else:
        # Model gave a direct text answer
        print(intent.text_response)
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import ollama

from agents.sauron.engine import MODEL_NAME, INFERENCE_OPTIONS
from agents.sauron.audit import SauronEvent, get_sauron_audit

logger = logging.getLogger(__name__)

# ── Prompt Loading ─────────────────────────────────────────────────────────────

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(filename: str, fallback: str = "") -> str:
    """Load a prompt file, returning fallback string if not found."""
    path = _PROMPTS_DIR / filename
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return fallback


SYSTEM_PROMPT = _load_prompt("system.txt", fallback=(
    "You are the Eye of Sauron, FRANKENSTEIN 1.0's master orchestrator agent. "
    "Use the available tools to answer the user's requests. "
    "Be precise and safety-conscious."
))

TOOL_USE_ADDENDUM = _load_prompt("tool_use.txt", fallback="")


# ── Tool Schema Definitions ────────────────────────────────────────────────────
# One Ollama function per tool. Each function has an `action` enum listing all
# valid sub-actions for that tool, plus the most-used parameters described
# clearly so the model knows which params apply to which actions.

TOOL_SCHEMAS = [

    # ── git ────────────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "git",
            "description": (
                "Full Git operations. "
                "Ring 3 (free — no prompt): git_status, git_log, git_diff, git_branch, "
                "git_remote, git_show, git_stash_list, git_tag_list. "
                "Ring 2 (approval required): git_add, git_commit, git_push, git_pull, "
                "git_fetch, git_clone, git_checkout, git_reset, git_merge, git_rebase, "
                "git_stash, git_create_tag, git_delete_tag, git_any (universal fallback)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "git_status", "git_log", "git_diff", "git_branch",
                            "git_remote", "git_show", "git_stash_list", "git_tag_list",
                            "git_add", "git_commit", "git_push", "git_pull", "git_fetch",
                            "git_clone", "git_checkout", "git_reset", "git_merge",
                            "git_rebase", "git_stash", "git_create_tag", "git_delete_tag",
                            "git_any",
                        ],
                        "description": "Git sub-action to perform.",
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Absolute path to the git repository. Required for all actions.",
                    },
                    "message": {
                        "type": "string",
                        "description": "Commit message (git_commit) or stash description (git_stash push).",
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files to stage (git_add). Pass ['.'] to stage all.",
                    },
                    "all": {
                        "type": "boolean",
                        "description": "git_add: stage all changes. git_branch: include remote branches.",
                    },
                    "remote": {
                        "type": "string",
                        "description": "Remote name (default 'origin'). Used by push/pull/fetch.",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name. Used by push, pull, checkout, merge, rebase.",
                    },
                    "force": {
                        "type": "boolean",
                        "description": "git_push: add --force flag. WARNING: rewrites remote history.",
                    },
                    "n": {
                        "type": "integer",
                        "description": "git_log: number of commits to show (default 20).",
                    },
                    "staged": {
                        "type": "boolean",
                        "description": "git_diff: show staged changes (--cached flag).",
                    },
                    "ref": {
                        "type": "string",
                        "description": "Commit/tag/branch ref. Used by git_diff, git_show, git_reset.",
                    },
                    "file": {
                        "type": "string",
                        "description": "git_diff: limit diff to a single file path.",
                    },
                    "target": {
                        "type": "string",
                        "description": "git_checkout: branch name, file path, or commit ref to switch to.",
                    },
                    "create": {
                        "type": "boolean",
                        "description": "git_checkout: create a new branch (-b flag).",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["--soft", "--mixed", "--hard"],
                        "description": "git_reset: reset mode (default --mixed).",
                    },
                    "url": {
                        "type": "string",
                        "description": "git_clone: repository URL to clone.",
                    },
                    "dest": {
                        "type": "string",
                        "description": "git_clone: local directory name (optional).",
                    },
                    "amend": {
                        "type": "boolean",
                        "description": "git_commit: amend the previous commit (--amend).",
                    },
                    "subaction": {
                        "type": "string",
                        "enum": ["push", "pop", "apply", "drop", "clear"],
                        "description": "git_stash: which stash operation to run (default 'push').",
                    },
                    "stash_ref": {
                        "type": "string",
                        "description": "git_stash apply/drop: stash reference e.g. 'stash@{0}'.",
                    },
                    "no_ff": {
                        "type": "boolean",
                        "description": "git_merge: disable fast-forward (--no-ff).",
                    },
                    "name": {
                        "type": "string",
                        "description": "Tag name for git_create_tag or git_delete_tag.",
                    },
                    "subcommand": {
                        "type": "string",
                        "description": "git_any: any git subcommand (e.g. 'cherry-pick', 'reflog', 'bisect').",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "git_any: additional arguments. git_log: extra log flags.",
                    },
                },
                "required": ["action"],
            },
        },
    },

    # ── code ───────────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "code",
            "description": (
                "Source code operations. "
                "Ring 3 (free): code_read (view file with line numbers), "
                "code_format (black --check, no file change), code_lint (flake8 or pylint). "
                "Ring 2 (approval): code_edit (inline old→new replacement), "
                "code_format_apply (black reformat), code_run (python script or -c), "
                "code_test (pytest)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "code_read", "code_format", "code_lint",
                            "code_edit", "code_format_apply", "code_run", "code_test",
                        ],
                        "description": "Code sub-action to perform.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Absolute file path. Required for code_read, code_edit, code_format, code_lint, code_format_apply, code_test.",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "code_read: first line to return (1-indexed, default 1).",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "code_read: last line to return inclusive (default start+499).",
                    },
                    "old_string": {
                        "type": "string",
                        "description": "code_edit: exact text to find (must be unique or use replace_all=true).",
                    },
                    "new_string": {
                        "type": "string",
                        "description": "code_edit: replacement text (can be empty string to delete).",
                    },
                    "replace_all": {
                        "type": "boolean",
                        "description": "code_edit: replace every occurrence instead of requiring uniqueness.",
                    },
                    "tool": {
                        "type": "string",
                        "enum": ["flake8", "pylint"],
                        "description": "code_lint: which linter to use (default 'flake8').",
                    },
                    "code": {
                        "type": "string",
                        "description": "code_run: inline Python code string (python -c '...'). Mutually exclusive with path.",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "code_run: CLI args for the script. code_test: pytest flags e.g. ['-v', '-x'].",
                    },
                    "cwd": {
                        "type": "string",
                        "description": "code_run / code_test: working directory for execution.",
                    },
                },
                "required": ["action"],
            },
        },
    },

    # ── shell ──────────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "shell",
            "description": (
                "Shell operations. "
                "Ring 3 (free): shell_info (system info), env_read (environment variables). "
                "Ring 2 (approval): shell_exec (run any command), env_write (set/unset env vars)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["shell_info", "shell_exec", "env_read", "env_write"],
                        "description": "Shell sub-action to perform.",
                    },
                    "query": {
                        "type": "string",
                        "enum": ["all", "host", "date", "user", "env", "disk", "processes", "python", "memory", "cpu"],
                        "description": "shell_info: which info section to return (default 'all').",
                    },
                    "command": {
                        "type": "string",
                        "description": "shell_exec: the shell command to run. Always requires approval.",
                    },
                    "cwd": {
                        "type": "string",
                        "description": "shell_exec: working directory for the command.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "shell_exec: timeout in seconds (max 15, default 15).",
                    },
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "env_read: specific variable names to return. Omit for filtered full environment.",
                    },
                    "operations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["set", "unset"]},
                                "key": {"type": "string"},
                                "value": {"type": "string"},
                            },
                            "required": ["action", "key"],
                        },
                        "description": "env_write: list of set/unset operations. Each: {action, key, value}.",
                    },
                },
                "required": ["action"],
            },
        },
    },

    # ── package ────────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "package",
            "description": (
                "Package manager operations (pip, npm, conda). "
                "Ring 3 (free): pip_list, pip_show, pip_freeze, pip_check, npm_list, npm_outdated, conda_list, conda_env_list. "
                "Ring 2 (approval): pip_install, pip_uninstall, pip_upgrade, npm_install, npm_uninstall, npm_run, conda_install, conda_create, conda_remove."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "pip_list", "pip_show", "pip_freeze", "pip_check",
                            "pip_install", "pip_uninstall", "pip_upgrade",
                            "npm_list", "npm_outdated",
                            "npm_install", "npm_uninstall", "npm_run",
                            "conda_list", "conda_env_list",
                            "conda_install", "conda_create", "conda_remove",
                        ],
                        "description": "Package manager sub-action.",
                    },
                    "packages": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Package name(s) for install/uninstall/upgrade/show actions.",
                    },
                    "package": {
                        "type": "string",
                        "description": "pip_show: single package name to inspect.",
                    },
                    "requirements": {
                        "type": "string",
                        "description": "pip_install: path to requirements.txt file (-r flag).",
                    },
                    "env": {
                        "type": "string",
                        "description": "conda: environment name for install/create/remove/list.",
                    },
                    "python_version": {
                        "type": "string",
                        "description": "conda_create: Python version to install (e.g. '3.11').",
                    },
                    "channel": {
                        "type": "string",
                        "description": "conda_install: conda channel (e.g. 'conda-forge').",
                    },
                    "script": {
                        "type": "string",
                        "description": "npm_run: script name from package.json.",
                    },
                    "cwd": {
                        "type": "string",
                        "description": "npm_*: project directory containing package.json.",
                    },
                    "global_": {
                        "type": "boolean",
                        "description": "npm_install / npm_uninstall: install/remove globally (-g).",
                    },
                },
                "required": ["action"],
            },
        },
    },

    # ── file ───────────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "file",
            "description": (
                "File system operations. "
                "Ring 3 (free): file_read, file_copy. "
                "Ring 2 (approval): file_write, file_delete, file_move. "
                "Write/delete operations restricted to FRANKENSTEIN allowed directories."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["file_read", "file_write", "file_delete", "file_copy", "file_move", "file_append"],
                        "description": "File operation to perform.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the target file.",
                    },
                    "content": {
                        "type": "string",
                        "description": "file_write / file_append: content to write or append.",
                    },
                    "dest": {
                        "type": "string",
                        "description": "file_copy / file_move: destination path.",
                    },
                    "encoding": {
                        "type": "string",
                        "description": "File encoding (default 'utf-8').",
                    },
                },
                "required": ["action", "path"],
            },
        },
    },

    # ── dir ────────────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "dir",
            "description": (
                "Directory operations. "
                "Ring 3 (free): dir_list, dir_navigate, dir_tree. "
                "Ring 2 (approval): dir_create."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["dir_list", "dir_create", "dir_navigate", "dir_tree"],
                        "description": "Directory operation to perform.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Absolute directory path. Required for all actions.",
                    },
                    "show_hidden": {
                        "type": "boolean",
                        "description": "dir_list: include hidden files (default false).",
                    },
                    "depth": {
                        "type": "integer",
                        "description": "dir_tree: maximum depth to traverse (default 3).",
                    },
                },
                "required": ["action", "path"],
            },
        },
    },

    # ── search ─────────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": (
                "Search operations. Ring 3 (free). "
                "file_search: find files by name pattern (glob). "
                "content_search: search file contents by regex (grep-style)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["file_search", "content_search"],
                        "description": "Search type.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search in.",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "file_search: glob pattern (e.g. '*.py'). content_search: regex pattern.",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Search recursively into subdirectories (default true).",
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "content_search: case-sensitive match (default false).",
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "content_search: limit search to files matching this glob (e.g. '*.py').",
                    },
                },
                "required": ["action", "pattern"],
            },
        },
    },

    # ── web_fetch ──────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": (
                "Fetch content from the web. Ring 2 (approval). "
                "ONLY Wolfram Alpha (wolframalpha.com) and Wikipedia (wikipedia.org) are allowed. "
                "All other domains are permanently blocked (Ring 1)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["fetch"],
                        "description": "Always 'fetch'.",
                    },
                    "url": {
                        "type": "string",
                        "description": "URL to fetch. Must be on wolframalpha.com or wikipedia.org.",
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "Maximum characters to return (default 4000).",
                    },
                },
                "required": ["action", "url"],
            },
        },
    },

    # ── memory ─────────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "memory",
            "description": (
                "Session memory and quantum state recall. Ring 3 (free). "
                "list_states, load_state, list_circuits, load_circuit, get_session_summary."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "list_states", "load_state", "save_state",
                            "list_circuits", "load_circuit", "get_session_summary",
                        ],
                        "description": "Memory operation to perform.",
                    },
                    "name": {
                        "type": "string",
                        "description": "State or circuit name for load/save operations.",
                    },
                },
                "required": ["action"],
            },
        },
    },

    # ── quantum ────────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "quantum",
            "description": (
                "Full quantum computing automation via FRANKENSTEIN synthesis engines. "
                "Ring 3 (free): init_qubits, apply_gate, run_circuit, run_preset (bell/ghz/qft), "
                "get_state_info, list_circuits, synthesis_status, true_engine_status. "
                "Ring 2 (approval): measure (auto-launches Bloch sphere), show_bloch, save_state, "
                "save_circuit, delete_circuit, load_circuit_and_run, qiskit_run, qutip_evolve, "
                "synthesis_run, synthesis_bloch, synthesis_gaussian, synthesis_tunneling, "
                "synthesis_harmonic, synthesis_lorentz. "
                "Supports up to 18 qubits (>16 auto-routes to 20 GB TrueSynthesisEngine). "
                "Typical workflow: init_qubits -> apply_gate / run_preset -> measure."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": (
                            "Quantum action to perform. "
                            "Ring 3 (auto-safe): init_qubits, apply_gate, run_circuit, "
                            "run_preset, get_state_info, list_circuits, synthesis_status, "
                            "true_engine_status. "
                            "Ring 2 (approval required): measure, show_bloch, save_state, "
                            "save_circuit, delete_circuit, load_circuit_and_run, qiskit_run, "
                            "qutip_evolve, synthesis_run, synthesis_bloch, synthesis_gaussian, "
                            "synthesis_tunneling, synthesis_harmonic, synthesis_lorentz."
                        ),
                    },
                    "n_qubits": {
                        "type": "integer",
                        "description": (
                            "Number of qubits for init_qubits (1-18) or run_preset ghz/qft. "
                            "Values >16 automatically use the 20 GB TrueSynthesisEngine."
                        ),
                    },
                    "target": {
                        "type": "integer",
                        "description": "Target qubit index (0-based) for apply_gate.",
                    },
                    "gate": {
                        "type": "string",
                        "description": (
                            "Gate name for apply_gate: h, x, y, z, s, t, sdg, tdg, sx, sxdg, "
                            "rx, ry, rz, p, cx, cnot, cy, cz, ch, swap, cp, ccx, toffoli, "
                            "cswap, mcx."
                        ),
                    },
                    "control": {
                        "type": "integer",
                        "description": "Single control qubit index for two-qubit gates (cx, cz, cp, etc.).",
                    },
                    "controls": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of control qubit indices for multi-controlled gates (mcx, ccx).",
                    },
                    "params": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Gate parameters, e.g. [1.5708] for rx/ry/rz/p/cp rotation angle.",
                    },
                    "circuit": {
                        "type": "array",
                        "description": (
                            "List of gate dicts for run_circuit. Each dict: "
                            "{gate, targets: [ints], controls: [ints], params: [floats]}. "
                            "Use gate='reset' with n_qubits to initialise. "
                            "Use gate='measure' with shots to measure inline."
                        ),
                    },
                    "preset": {
                        "type": "string",
                        "description": (
                            "For run_preset: 'bell', 'ghz', or 'qft'. "
                            "For synthesis_run: 'gaussian', 'tunneling', 'harmonic', or 'relativistic'."
                        ),
                    },
                    "sim_type": {
                        "type": "string",
                        "description": (
                            "Synthesis Bloch sphere simulation type for synthesis_bloch: "
                            "'rabi', 'precession', 'spiral', or 'hadamard'."
                        ),
                    },
                    "name": {
                        "type": "string",
                        "description": "Circuit or state name for save_circuit, delete_circuit, load_circuit_and_run, save_state.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional human-readable description when saving a circuit.",
                    },
                    "shots": {
                        "type": "integer",
                        "description": "Number of measurement shots for measure or load_circuit_and_run (default 1024).",
                    },
                    "qasm": {
                        "type": "string",
                        "description": "OpenQASM 2.0 source string for qiskit_run.",
                    },
                    "omega": {
                        "type": "number",
                        "description": "Frequency parameter for synthesis_bloch or synthesis_harmonic.",
                    },
                    "sigma": {
                        "type": "number",
                        "description": "Sigma (width) parameter for synthesis_gaussian.",
                    },
                    "k0": {
                        "type": "number",
                        "description": "Initial wave vector k0 for synthesis_gaussian.",
                    },
                    "barrier": {
                        "type": "number",
                        "description": "Barrier height for synthesis_tunneling.",
                    },
                    "velocity": {
                        "type": "number",
                        "description": "Velocity as fraction of c (0.0-1.0) for synthesis_lorentz.",
                    },
                },
                "required": ["action"],
            },
        },
    },
]


# ── ParsedIntent ───────────────────────────────────────────────────────────────

@dataclass
class ParsedIntent:
    """
    Result of one inference step.

    If has_tool_call is True, tool_name and arguments are populated and the
    router should execute the tool then call parse_from_messages again with
    the tool result appended.

    If has_tool_call is False, text_response contains the model's final answer
    and the ReAct loop should terminate.
    """
    tool_name: Optional[str]        # None → model gave a direct text answer
    arguments: dict                  # Tool arguments from model's function call
    text_response: Optional[str]     # Model's text when no tool call
    raw_tool_call: Optional[dict]    # Raw tool_call dict for debugging

    @property
    def has_tool_call(self) -> bool:
        return self.tool_name is not None

    @property
    def action(self) -> str:
        """Convenience: extract 'action' from arguments."""
        return self.arguments.get("action", "")


# ── Intent Parser ──────────────────────────────────────────────────────────────

class IntentParser:
    """
    Converts natural language user messages into structured tool calls.

    Uses Ollama's native function calling with Qwen 2.5 7B Instruct.
    The parser is stateless — it receives the full message list each call.
    State (conversation history) is managed by ActionRouter.

    Tool schemas are defined at module level (TOOL_SCHEMAS) and loaded once
    at instantiation time.
    """

    def __init__(self):
        self._tools = TOOL_SCHEMAS
        self._system_messages = self._build_system_messages()
        logger.info(
            "IntentParser initialized with %d tool schemas.", len(self._tools)
        )

    def _build_system_messages(self) -> list:
        """
        Build the system message list that is prepended to every inference call.
        Combines the identity prompt with the tool-use guidelines.
        """
        content = SYSTEM_PROMPT
        if TOOL_USE_ADDENDUM:
            content = content + "\n\n" + TOOL_USE_ADDENDUM
        return [{"role": "system", "content": content}]

    def parse_from_messages(self, messages: list) -> ParsedIntent:
        """
        Run one inference step against the current message list.

        The system messages are prepended automatically — do not include them
        in the `messages` argument.

        Args:
            messages : Conversation history. The last entry should be the
                       user message or tool result to respond to.

        Returns:
            ParsedIntent with has_tool_call=True (tool call) or False (text answer).
        """
        full_messages = self._system_messages + messages

        get_sauron_audit().log(
            SauronEvent.QUERY,
            f"Parser inference: {len(full_messages)} messages, last role={messages[-1].get('role', '?') if messages else 'none'}",
        )

        try:
            response = ollama.chat(
                model=MODEL_NAME,
                messages=full_messages,
                tools=self._tools,
                options=INFERENCE_OPTIONS,
            )
        except Exception as e:
            logger.error("Ollama inference error: %s", e, exc_info=True)
            return ParsedIntent(
                tool_name=None,
                arguments={},
                text_response=f"[Inference error: {e}]",
                raw_tool_call=None,
            )

        msg = response.message

        # ── Tool call path ─────────────────────────────────────────────────────
        if msg.tool_calls:
            call = msg.tool_calls[0]
            name = call.function.name
            raw_args = call.function.arguments

            # Ollama may return arguments as a JSON string or already a dict
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    logger.warning("Could not parse tool arguments as JSON: %s", raw_args[:200])
                    args = {}
            else:
                args = dict(raw_args) if raw_args else {}

            get_sauron_audit().log_tool_call(name, str(args)[:150])

            return ParsedIntent(
                tool_name=name,
                arguments=args,
                text_response=None,
                raw_tool_call={"name": name, "arguments": args},
            )

        # ── Text-only path ─────────────────────────────────────────────────────
        text = (msg.content or "").strip()
        return ParsedIntent(
            tool_name=None,
            arguments={},
            text_response=text,
            raw_tool_call=None,
        )

    def list_tool_names(self) -> list:
        """Return the list of tool names registered in the schema."""
        return [s["function"]["name"] for s in self._tools]

    def get_schema(self, tool_name: str) -> Optional[dict]:
        """Return the full Ollama schema for a tool by name."""
        for s in self._tools:
            if s["function"]["name"] == tool_name:
                return s
        return None


# ── Singleton ──────────────────────────────────────────────────────────────────

_parser_instance: Optional[IntentParser] = None


def get_parser() -> IntentParser:
    """Get or create the global IntentParser singleton."""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = IntentParser()
    return _parser_instance
