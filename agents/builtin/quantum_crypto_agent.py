#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Quantum Cryptography Agent
Phase 3.5: Lazy-loaded wrapper for qencrypt-local toolset

Provides quantum-assisted encryption, decryption, entropy generation,
and key management using AES-256-GCM with quantum entropy seeding.
"""

from typing import Any, Dict, Optional

from ..base import BaseAgent, AgentResult


class QuantumCryptoAgent(BaseAgent):
    """
    Agent for quantum encryption and secure communications via qencrypt-local.

    Capabilities:
    - Quantum-assisted text encryption (AES-256-GCM + quantum entropy)
    - Decryption of encrypted packages
    - Quantum entropy generation (IBM hardware, simulator, or local)
    - Encryption package inspection and validation
    """

    name = "quantum_crypto"
    description = "Quantum-assisted encryption and secure communications (qencrypt)"
    version = "1.0.0"
    requires_network = False  # local entropy mode needs no network
    requires_filesystem = False
    max_execution_time = 60

    def __init__(self):
        super().__init__()
        self._qencrypt = None

    def _ensure_loaded(self):
        """Lazy-load qencrypt_local only when a method is actually called."""
        if self._qencrypt is None:
            from libs.local_toolsets import load_qencrypt
            self._qencrypt = load_qencrypt()
            if self._qencrypt is None:
                raise RuntimeError(
                    "Failed to load qencrypt_local — insufficient RAM or not installed"
                )

    def execute(self, operation: str = "", **kwargs) -> AgentResult:
        """
        Dispatch to the requested crypto operation.

        Args:
            operation: One of 'encrypt', 'decrypt', 'generate_entropy', 'inspect_package'
            **kwargs: Operation-specific parameters
        """
        if not operation:
            return AgentResult(
                success=False,
                error="No operation specified. Available: encrypt, decrypt, "
                      "generate_entropy, inspect_package",
            )

        dispatch = {
            "encrypt": self._run_encrypt,
            "decrypt": self._run_decrypt,
            "generate_entropy": self._run_generate_entropy,
            "inspect_package": self._run_inspect_package,
        }

        handler = dispatch.get(operation)
        if handler is None:
            return AgentResult(
                success=False,
                error=f"Unknown operation: {operation!r}. "
                      f"Available: {', '.join(sorted(dispatch))}",
            )

        try:
            self._ensure_loaded()
            return handler(**kwargs)
        except RuntimeError as exc:
            return AgentResult(success=False, error=str(exc))
        except Exception as exc:
            return AgentResult(success=False, error=f"{type(exc).__name__}: {exc}")

    # ── Encryption ───────────────────────────────────────────────────────

    def _run_encrypt(
        self,
        plaintext: str = "",
        passphrase: str = "",
        entropy_source: str = "local",
        entropy_bytes: int = 256,
        **kwargs,
    ) -> AgentResult:
        """
        Encrypt plaintext using quantum-assisted AES-256-GCM.

        Args:
            plaintext: The text to encrypt
            passphrase: Passphrase for key wrapping
            entropy_source: 'local', 'ibm_simulator', 'ibm_hardware', or 'auto'
            entropy_bytes: Number of entropy bytes (default 256)
        """
        if not plaintext:
            return AgentResult(success=False, error="plaintext must be non-empty")
        if not passphrase:
            return AgentResult(success=False, error="passphrase must be non-empty")

        qe = self._qencrypt
        package = qe.encrypt_text(
            plaintext,
            passphrase,
            entropy_source=entropy_source,
            entropy_bytes=entropy_bytes,
        )

        return AgentResult(
            success=True,
            data={
                "package": package,
                "cipher": package.get("cipher"),
                "entropy_source": package.get("entropy_meta", {}).get("source", "unknown"),
                "key_fingerprint": package.get("key_fingerprint"),
                "created_at": package.get("created_at"),
            },
        )

    # ── Decryption ───────────────────────────────────────────────────────

    def _run_decrypt(
        self,
        package=None,
        passphrase: str = "",
        **kwargs,
    ) -> AgentResult:
        """
        Decrypt an encrypted package back to plaintext.

        Args:
            package: The EncryptionPackage dict (or JSON string)
            passphrase: The passphrase used during encryption
        """
        if package is None:
            return AgentResult(success=False, error="package is required")
        if not passphrase:
            return AgentResult(success=False, error="passphrase must be non-empty")

        qe = self._qencrypt
        plaintext = qe.decrypt_text(package, passphrase)

        return AgentResult(
            success=True,
            data={
                "plaintext": plaintext,
                "length": len(plaintext),
            },
        )

    # ── Entropy generation ───────────────────────────────────────────────

    def _run_generate_entropy(
        self,
        n_bytes: int = 32,
        source: str = "local",
        **kwargs,
    ) -> AgentResult:
        """
        Generate quantum entropy bytes.

        Args:
            n_bytes: Number of entropy bytes to generate (default 32)
            source: 'local', 'ibm_simulator', 'ibm_hardware', or 'auto'
        """
        from qencrypt_local.quantum_entropy import get_entropy

        entropy_bytes, meta = get_entropy(
            n_bytes,
            source=source,
            allow_fallback=True,
        )

        return AgentResult(
            success=True,
            data={
                "entropy_hex": entropy_bytes.hex(),
                "n_bytes": len(entropy_bytes),
                "source_used": meta.get("source", "unknown"),
                "meta": meta,
            },
        )

    # ── Package inspection ───────────────────────────────────────────────

    def _run_inspect_package(
        self,
        package=None,
        **kwargs,
    ) -> AgentResult:
        """
        Inspect an encryption package without decrypting it.

        Args:
            package: The EncryptionPackage dict (or JSON string)
        """
        import json

        if package is None:
            return AgentResult(success=False, error="package is required")

        if isinstance(package, str):
            package = json.loads(package)

        return AgentResult(
            success=True,
            data={
                "version": package.get("v"),
                "cipher": package.get("cipher"),
                "created_at": package.get("created_at"),
                "key_fingerprint": package.get("key_fingerprint"),
                "kdf": package.get("kdf", {}).get("name"),
                "kdf_params": {
                    "n": package.get("kdf", {}).get("n"),
                    "r": package.get("kdf", {}).get("r"),
                    "p": package.get("kdf", {}).get("p"),
                },
                "entropy_meta": package.get("entropy_meta"),
                "has_ciphertext": "ciphertext_b64" in package,
                "has_wrapped_key": "wrapped_key_b64" in package,
            },
        )
