"""
FRANKENSTEIN 1.0 - Eye of Sauron: Inference Engine
Phase 4: Master Orchestrator Agent

Wraps Ollama Python SDK for local Phi-3.5 Mini 3.8B Instruct inference.
Model: phi3.5:3.8b-mini-instruct-q4_K_M (~2.5GB RAM, loaded via Ollama)

IMPORTANT: This module must only be imported via get_sauron() in __init__.py.
Never import EyeOfSauron directly at the top of another module.
"""

import logging
import os
from typing import Iterator, Optional

import ollama

from core.safety import SAFETY

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

MODEL_NAME = "phi3.5:3.8b-mini-instruct-q4_K_M"

# 2 threads for inference (leaves 2 cores free for OS + quantum engine on i3 quad-core).
# Separate from SAFETY.MAX_WORKER_THREADS which governs agent worker pool.
INFERENCE_THREADS = 2

# Profile B — Chat Primary (default when quantum engine is idle)
INFERENCE_OPTIONS = {
    "num_ctx": 4096,          # Down from 8192 — saves KV-cache RAM
    "num_thread": INFERENCE_THREADS,
    "temperature": 0.5,       # Down from 0.7 — less rambling
    "top_p": 0.9,
    "repeat_penalty": 1.18,   # Prevents repetition loops
    "repeat_last_n": 192,     # Lookback window for repeat penalty
    "num_predict": 250,       # Hard output token cap (prevents novels)
}

# Profile A — Quantum Active (auto-selected when quantum engine is running)
INFERENCE_OPTIONS_QUANTUM = {
    "num_ctx": 2048,
    "num_thread": 2,
    "temperature": 0.5,
    "top_p": 0.9,
    "repeat_penalty": 1.18,
    "repeat_last_n": 192,
    "num_predict": 180,       # Shorter responses during quantum ops
}

# ── Prompt file loader ─────────────────────────────────────────────────────────

_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def _load_prompt(name: str) -> str:
    """Load a prompt template from the prompts/ directory."""
    path = os.path.join(_PROMPT_DIR, name)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.warning("Prompt file not found: %s", path)
        return ""


# ── Execution reminder injected into every chat turn ───────────────────────────

_EXEC_REMINDER = (
    "\n\n[AUTOMATION MANDATE: You are FRANK — an automation assistant first, "
    "chat assistant second. For ANY request that involves running a process, "
    "command, script, file operation, git operation, or quantum computation: "
    "you EXECUTE it — you do NOT describe it. "
    "Use ::EXEC::command for terminal/system commands. "
    "Use ::QUANTUM::action|param=value for quantum operations. "
    "Never say 'you can run...' or 'try typing...' — just DO it. One action per response.]"
)


# ── Engine ─────────────────────────────────────────────────────────────────────

class EyeOfSauron:
    """
    Master orchestrator LLM agent.

    Wraps Ollama inference for Phi-3.5 Mini 3.8B (Q4_K_M).
    Provides single-turn queries, streaming, and multi-turn chat.
    Memory is bounded to MAX_CONVERSATION_TURNS to prevent RAM growth.
    Supports two inference profiles: normal (Profile B) and quantum-active (Profile A).
    """

    name = "eye_of_sauron"
    version = "1.0.0"

    MAX_CONVERSATION_TURNS = 16  # Each turn = 1 user + 1 assistant message

    def __init__(self):
        self._conversation: list = []
        self._loaded = False
        self._quantum_active = False       # Tracks if quantum engine is running
        self._system_prompt = _load_prompt("system.txt") or self._default_system_prompt()
        self._verify_model()
        logger.info("Eye of Sauron initialized (model: %s).", MODEL_NAME)

    @staticmethod
    def _default_system_prompt() -> str:
        """Fallback system prompt if prompts/system.txt is not found."""
        return (
            "You are FRANK — FRANKENSTEIN 1.0's master AI. "
            "You EXECUTE commands using ::EXEC::command syntax. "
            "You do NOT just give instructions — you DO the work. "
            "Keep responses short. One command per response."
        )

    def set_quantum_active(self, active: bool) -> None:
        """Toggle quantum-active inference profile (Profile A) for resource safety."""
        self._quantum_active = active
        logger.info("Quantum-active mode: %s", active)

    def _get_options(self) -> dict:
        """Return inference options based on current quantum state."""
        if self._quantum_active:
            return INFERENCE_OPTIONS_QUANTUM
        return INFERENCE_OPTIONS

    # ── Internal ───────────────────────────────────────────────────────────────

    def _verify_model(self) -> None:
        """Confirm the Phi-3.5 Mini model is available in Ollama before we proceed."""
        try:
            available = [m.model for m in ollama.list().models]
            if MODEL_NAME not in available:
                raise RuntimeError(
                    f"Model '{MODEL_NAME}' not found in Ollama.\n"
                    f"Available models: {available}\n"
                    f"Run: ollama pull {MODEL_NAME}"
                )
            self._loaded = True
            logger.info("Model '%s' verified in Ollama.", MODEL_NAME)
        except ollama.ResponseError as e:
            logger.error("Ollama response error during model check: %s", e)
            raise
        except Exception as e:
            logger.error("Model verification failed: %s", e)
            raise

    def _trim_conversation(self) -> None:
        """
        Keep conversation within MAX_CONVERSATION_TURNS to bound RAM usage.
        When approaching the limit (75% full), summarize the oldest half of turns
        into a compact context message rather than discarding them silently.
        """
        max_messages = self.MAX_CONVERSATION_TURNS * 2  # user + assistant per turn
        threshold = int(max_messages * 0.75)

        if threshold < len(self._conversation) <= max_messages:
            # Approaching limit — summarize oldest half into a compact summary message
            half = len(self._conversation) // 2
            old_turns = self._conversation[:half]
            summary_parts = []
            for msg in old_turns:
                role = msg["role"]
                content = msg["content"][:80]
                if role == "user":
                    summary_parts.append(f"User asked about: {content}")
                elif role == "assistant":
                    summary_parts.append(f"Frank responded about: {content}")
            summary = "CONVERSATION SUMMARY (older turns):\n" + "\n".join(summary_parts[-6:])
            self._conversation = (
                [{"role": "system", "content": summary}]
                + self._conversation[half:]
            )
            logger.debug("Conversation summarized: %d old messages → 1 summary.", half)

        elif len(self._conversation) > max_messages:
            # Hard trim — past absolute limit
            self._conversation = self._conversation[-max_messages:]
            logger.debug("Conversation hard-trimmed to %d messages.", max_messages)

    def _build_context_preamble(self) -> str:
        """
        Build a compact system-context summary injected into every chat() turn.
        Lazy-loads all sources — never crashes if a module is unavailable.
        Covers: working dir, session stats, quantum engine state, saved artifacts,
        storage usage, and current CPU/RAM.
        """
        lines = ["## CURRENT SYSTEM CONTEXT"]

        # Working directory
        import os
        lines.append(f"Working directory: {os.getcwd()}")

        # Session stats
        try:
            from core.memory import get_memory
            stats = get_memory().get_session_stats()
            lines.append(
                f"Session: {stats.get('uptime_human', '?')} uptime, "
                f"{stats.get('task_count', 0)} tasks "
                f"({stats.get('successful_tasks', 0)} ok, "
                f"{stats.get('failed_tasks', 0)} failed)"
            )
        except Exception:
            pass

        # Active quantum engine state
        try:
            from synthesis.engine import get_synthesis_engine
            engine = get_synthesis_engine()
            n = engine.get_num_qubits()
            if n > 0:
                gate_log = getattr(engine, "_gate_log", [])
                lines.append(
                    f"Quantum engine: {n} qubits active, {len(gate_log)} gates applied"
                )
                try:
                    probs = engine.get_probabilities()
                    top = sorted(probs.items(), key=lambda kv: -kv[1])[:3]
                    lines.append(
                        "  Top states: " + ", ".join(f"|{s}⟩={p:.3f}" for s, p in top)
                    )
                except Exception:
                    pass
        except Exception:
            pass

        # Saved quantum states
        try:
            from pathlib import Path
            states_dir = Path.home() / ".frankenstein" / "synthesis_data" / "states"
            if states_dir.exists():
                state_files = sorted(
                    states_dir.glob("*.npz"),
                    key=lambda f: f.stat().st_mtime,
                    reverse=True,
                )
                if state_files:
                    names = [f.stem for f in state_files[:5]]
                    extra = f" (+{len(state_files) - 5} more)" if len(state_files) > 5 else ""
                    lines.append(f"Saved states: {', '.join(names)}{extra}")
        except Exception:
            pass

        # Saved circuits
        try:
            from pathlib import Path
            circuits_dir = Path.home() / ".frankenstein" / "synthesis_data" / "circuits"
            if circuits_dir.exists():
                circuit_files = sorted(
                    circuits_dir.glob("*.json"),
                    key=lambda f: f.stat().st_mtime,
                    reverse=True,
                )
                if circuit_files:
                    names = [f.stem for f in circuit_files[:5]]
                    extra = f" (+{len(circuit_files) - 5} more)" if len(circuit_files) > 5 else ""
                    lines.append(f"Saved circuits: {', '.join(names)}{extra}")
        except Exception:
            pass

        # Storage usage
        try:
            from core.memory import get_memory
            usage = get_memory().get_storage_usage()
            lines.append(f"Storage: {usage.get('total_mb', 0):.1f} MB used of 10 GB budget")
        except Exception:
            pass

        # CPU / RAM
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            lines.append(f"Resources: CPU {cpu:.0f}%, RAM {ram:.0f}%")
            if cpu > 65 or ram > 65:
                lines.append("WARNING: Resources elevated — keep responses short")
        except Exception:
            pass

        return "\n".join(lines) + "\n"

    # ── Public API ─────────────────────────────────────────────────────────────

    def query(self, prompt: str, system: Optional[str] = None) -> str:
        """
        Single-turn query. Does not affect conversation history.
        Returns the complete response as a string.
        Execution reminder is always injected — FRANK is an automation assistant.
        """
        messages = [
            {"role": "system", "content": system or self._system_prompt},
            {"role": "user",   "content": prompt + _EXEC_REMINDER},
        ]
        response = ollama.chat(
            model=MODEL_NAME,
            messages=messages,
            options=self._get_options(),
        )
        return response.message.content

    def stream(self, prompt: str, system: Optional[str] = None) -> Iterator[str]:
        """
        Single-turn streaming query. Yields tokens as they arrive.
        Does not affect conversation history.
        Execution reminder is always injected — FRANK is an automation assistant.
        """
        messages = [
            {"role": "system", "content": system or self._system_prompt},
            {"role": "user",   "content": prompt + _EXEC_REMINDER},
        ]
        for chunk in ollama.chat(
            model=MODEL_NAME,
            messages=messages,
            stream=True,
            options=self._get_options(),
        ):
            token = chunk.message.content
            if token:
                yield token

    def chat(self, user_message: str) -> str:
        """
        Multi-turn chat with context awareness.
        Injects execution reminder and live system context into every turn.
        History is automatically trimmed/summarized at MAX_CONVERSATION_TURNS.
        """
        # Inject reminder into what the LLM sees, but store the clean message in history
        augmented = user_message + _EXEC_REMINDER
        self._conversation.append({"role": "user", "content": augmented})
        self._trim_conversation()

        # Build context-enriched system prompt
        context = self._build_context_preamble()
        full_system = self._system_prompt + "\n\n" + context

        messages = [{"role": "system", "content": full_system}] + self._conversation

        response = ollama.chat(
            model=MODEL_NAME,
            messages=messages,
            options=self._get_options(),
        )
        reply = response.message.content

        # Replace augmented message with clean original in stored history
        self._conversation[-1] = {"role": "user", "content": user_message}
        self._conversation.append({"role": "assistant", "content": reply})
        return reply

    def chat_stream(self, user_message: str) -> Iterator[str]:
        """
        Multi-turn streaming chat with context awareness.
        Yields tokens; saves full reply to history.
        Injects execution reminder and live system context into every turn.
        """
        augmented = user_message + _EXEC_REMINDER
        self._conversation.append({"role": "user", "content": augmented})
        self._trim_conversation()

        # Build context-enriched system prompt
        context = self._build_context_preamble()
        full_system = self._system_prompt + "\n\n" + context

        messages = [{"role": "system", "content": full_system}] + self._conversation

        full_reply = []
        for chunk in ollama.chat(
            model=MODEL_NAME,
            messages=messages,
            stream=True,
            options=self._get_options(),
        ):
            token = chunk.message.content
            if token:
                full_reply.append(token)
                yield token

        # Replace augmented message with clean original in stored history
        self._conversation[-1] = {"role": "user", "content": user_message}
        self._conversation.append({"role": "assistant", "content": "".join(full_reply)})

    def reset_conversation(self) -> None:
        """Clear conversation history and free associated RAM."""
        self._conversation.clear()
        logger.info("Conversation history cleared.")

    def health_check(self) -> dict:
        """Return model status and current resource snapshot."""
        try:
            available = [m.model for m in ollama.list().models]
            model_ok = MODEL_NAME in available
            return {
                "status": "ok" if model_ok else "model_missing",
                "model": MODEL_NAME,
                "loaded": self._loaded,
                "quantum_active": self._quantum_active,
                "conversation_turns": len(self._conversation) // 2,
                "max_turns": self.MAX_CONVERSATION_TURNS,
                "inference_threads": INFERENCE_THREADS,
                "safety_cpu_limit": SAFETY.MAX_CPU_PERCENT,
                "safety_ram_limit": SAFETY.MAX_MEMORY_PERCENT,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def unload(self) -> None:
        """
        Signal Ollama to evict the model from memory (keep_alive=0).
        Called by unload_sauron() in __init__.py on idle timeout or exit.
        """
        try:
            ollama.chat(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": ""}],
                options={"keep_alive": 0},
            )
            self._loaded = False
            self._quantum_active = False
            logger.info("Eye of Sauron model unloaded from Ollama memory.")
        except Exception as e:
            logger.warning("Unload signal failed (non-fatal): %s", e)
