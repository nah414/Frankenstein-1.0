"""
FRANKENSTEIN 1.0 - Eye of Sauron: Inference Engine
Phase 4: Master Orchestrator Agent

Wraps Ollama Python SDK for local Qwen 2.5 7B Instruct inference.
Model: qwen2.5:7b-instruct-q4_K_M (~4.5GB RAM, loaded via Ollama)

IMPORTANT: This module must only be imported via get_sauron() in __init__.py.
Never import EyeOfSauron directly at the top of another module.
"""

import logging
from typing import Iterator, Optional

import ollama

from core.safety import SAFETY

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

MODEL_NAME = "qwen2.5:7b-instruct-q4_K_M"

# 3 threads for inference (leaves 1 core for OS on the i3 quad-core).
# Separate from SAFETY.MAX_WORKER_THREADS which governs agent worker pool.
INFERENCE_THREADS = 3

INFERENCE_OPTIONS = {
    "num_ctx": 8192,
    "num_thread": INFERENCE_THREADS,
    "temperature": 0.7,
    "top_p": 0.9,
}

SYSTEM_PROMPT = (
    "You are the Eye of Sauron, the master orchestrator agent for FRANKENSTEIN 1.0. "
    "You are a powerful, locally-running AI assistant that controls desktop operations, "
    "coordinates sub-agents, and executes complex workflows. "
    "You follow a strict permission-based security model with three rings of protection. "
    "You are precise, efficient, and safety-conscious."
)


# ── Engine ─────────────────────────────────────────────────────────────────────

class EyeOfSauron:
    """
    Master orchestrator LLM agent.

    Wraps Ollama inference for Qwen 2.5 7B Instruct (Q4_K_M).
    Provides single-turn queries, streaming, and multi-turn chat.
    Memory is bounded to MAX_CONVERSATION_TURNS to prevent RAM growth.
    """

    name = "eye_of_sauron"
    version = "1.0.0"

    MAX_CONVERSATION_TURNS = 20  # Each turn = 1 user + 1 assistant message

    def __init__(self):
        self._conversation: list = []
        self._loaded = False
        self._verify_model()
        logger.info("Eye of Sauron initialized (model: %s).", MODEL_NAME)

    # ── Internal ───────────────────────────────────────────────────────────────

    def _verify_model(self) -> None:
        """Confirm the Qwen model is available in Ollama before we proceed."""
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
        """Keep conversation within MAX_CONVERSATION_TURNS to bound RAM usage."""
        max_messages = self.MAX_CONVERSATION_TURNS * 2  # user + assistant per turn
        if len(self._conversation) > max_messages:
            self._conversation = self._conversation[-max_messages:]

    # ── Public API ─────────────────────────────────────────────────────────────

    def query(self, prompt: str, system: Optional[str] = None) -> str:
        """
        Single-turn query. Does not affect conversation history.
        Returns the complete response as a string.
        """
        messages = [
            {"role": "system", "content": system or SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ]
        response = ollama.chat(
            model=MODEL_NAME,
            messages=messages,
            options=INFERENCE_OPTIONS,
        )
        return response.message.content

    def stream(self, prompt: str, system: Optional[str] = None) -> Iterator[str]:
        """
        Single-turn streaming query. Yields tokens as they arrive.
        Does not affect conversation history.
        """
        messages = [
            {"role": "system", "content": system or SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ]
        for chunk in ollama.chat(
            model=MODEL_NAME,
            messages=messages,
            stream=True,
            options=INFERENCE_OPTIONS,
        ):
            token = chunk.message.content
            if token:
                yield token

    def chat(self, user_message: str) -> str:
        """
        Multi-turn chat. Maintains conversation history for context.
        History is automatically trimmed to MAX_CONVERSATION_TURNS.
        """
        self._conversation.append({"role": "user", "content": user_message})
        self._trim_conversation()

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self._conversation

        response = ollama.chat(
            model=MODEL_NAME,
            messages=messages,
            options=INFERENCE_OPTIONS,
        )
        reply = response.message.content
        self._conversation.append({"role": "assistant", "content": reply})
        return reply

    def chat_stream(self, user_message: str) -> Iterator[str]:
        """
        Multi-turn streaming chat. Yields tokens; saves full reply to history.
        """
        self._conversation.append({"role": "user", "content": user_message})
        self._trim_conversation()

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self._conversation

        full_reply = []
        for chunk in ollama.chat(
            model=MODEL_NAME,
            messages=messages,
            stream=True,
            options=INFERENCE_OPTIONS,
        ):
            token = chunk.message.content
            if token:
                full_reply.append(token)
                yield token

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
            logger.info("Eye of Sauron model unloaded from Ollama memory.")
        except Exception as e:
            logger.warning("Unload signal failed (non-fatal): %s", e)
