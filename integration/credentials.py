#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Credential Management System
Phase 3, Step 4: Credential storage for provider access

STORAGE:
- Credentials are stored as PLAIN JSON in ~/.frankenstein/credentials.json
- File permissions are set to owner-only (600 on Unix) for basic protection
- This is NOT encrypted — a future version could use the `keyring` library
  for OS-level encryption via the system keychain

SECURITY:
- Stored separately from the Git repository
- Per-provider credential isolation
- Sensitive values masked when displayed
"""

import os
import json
from typing import Optional, Dict, List
from pathlib import Path


# ============================================================================
# REQUIRED FIELDS PER PROVIDER
# ============================================================================

PROVIDER_CREDENTIAL_FIELDS: Dict[str, Dict] = {
    "ibm_quantum": {
        "fields": ["token"],
        "help": "Get at https://quantum.ibm.com → Account → API token"
    },
    "aws_braket": {
        "fields": ["aws_access_key_id", "aws_secret_access_key", "region_name"],
        "help": "AWS Console → IAM → Create access key"
    },
    "azure_quantum": {
        "fields": ["subscription_id", "resource_group", "workspace_name"],
        "help": "portal.azure.com → Quantum Workspace"
    },
    "google_cirq": {
        "fields": ["project_id"],
        "help": "gcloud auth application-default login"
    },
    "dwave": {
        "fields": ["token"],
        "help": "https://cloud.dwavesys.com/leap → API token"
    },
    "xanadu": {
        "fields": ["token"],
        "help": "https://cloud.xanadu.ai → Account → API key"
    },
    "ionq": {
        "fields": ["token"],
        "help": "https://cloud.ionq.com → API keys"
    },
    "rigetti": {
        "fields": ["token"],
        "help": "https://qcs.rigetti.com → Account → API key"
    },
    "quantinuum": {
        "fields": ["token"],
        "help": "https://um.qapi.quantinuum.com → API token"
    },
    "iqm": {
        "fields": ["token"],
        "help": "https://www.meetiqm.com → Account → API key"
    },
    "quera": {
        "fields": ["token"],
        "help": "https://www.quera.com → Account → API key"
    },
    "oxford": {
        "fields": ["token"],
        "help": "https://oxfordquantumcircuits.com → Account → API key"
    },
    "atom_computing": {
        "fields": ["token"],
        "help": "https://atom-computing.com → Account → API key"
    },
    "pasqal": {
        "fields": ["token"],
        "help": "https://www.pasqal.com → Account → API key"
    },
    "aqt": {
        "fields": ["token"],
        "help": "https://www.aqt.eu → Account → API key"
    },
    "nvidia_quantum_cloud": {
        "fields": ["api_key"],
        "help": "https://ngc.nvidia.com → Setup → API Key"
    },
    "local_simulator": {
        "fields": [],
        "help": "No credentials needed"
    },
    "local_cpu": {
        "fields": [],
        "help": "No credentials needed"
    },
    "qiskit_aer": {
        "fields": [],
        "help": "No credentials needed — local simulator"
    },
    "cuquantum": {
        "fields": [],
        "help": "No credentials needed — local GPU simulator"
    },
    "nvidia_cuda": {
        "fields": [],
        "help": "No credentials needed — local GPU"
    },
    "amd_rocm": {
        "fields": [],
        "help": "No credentials needed — local GPU"
    },
    "intel_oneapi": {
        "fields": [],
        "help": "No credentials needed — local CPU"
    },
    "apple_metal": {
        "fields": [],
        "help": "No credentials needed — local GPU"
    },
    "arm": {
        "fields": [],
        "help": "No credentials needed — local CPU"
    },
    "risc_v": {
        "fields": [],
        "help": "No credentials needed — local CPU"
    },
    "tpu": {
        "fields": ["project_id"],
        "help": "Google Cloud project with TPU access"
    },
    "fpga": {
        "fields": [],
        "help": "No credentials needed — local FPGA"
    },
    "npu": {
        "fields": [],
        "help": "No credentials needed — local NPU"
    },
}


def get_required_fields(provider_id: str) -> Dict:
    """
    Get required credential fields for a provider.

    Returns:
        Dict with 'fields' (list of field names) and 'help' (guidance string).
        Providers not in the registry default to {"fields": ["token"], "help": "Check provider website"}.
    """
    return PROVIDER_CREDENTIAL_FIELDS.get(
        provider_id,
        {"fields": ["token"], "help": "Check provider website"}
    )


class CredentialManager:
    """
    Manages credential storage for providers.
    Stores credentials as plain JSON in ~/.frankenstein/credentials.json
    with restrictive file permissions (owner read/write only on Unix).
    """

    def __init__(self):
        self.cred_dir = Path.home() / ".frankenstein"
        self.cred_file = self.cred_dir / "credentials.json"
        self.cred_dir.mkdir(exist_ok=True)

        # Set restrictive permissions (owner read/write only)
        if os.name != 'nt':  # Unix-like systems
            os.chmod(self.cred_dir, 0o700)

    def save_credentials(self, provider_id: str, credentials: Dict) -> bool:
        """
        Save credentials for a provider.

        Args:
            provider_id: Provider identifier (e.g., "ibm_quantum")
            credentials: Dict with provider-specific credentials

        Returns:
            True if saved successfully
        """
        try:
            all_creds = self._load_all()
            all_creds[provider_id] = credentials
            self._save_all(all_creds)
            return True
        except Exception as e:
            print(f"Error saving credentials: {e}")
            return False

    def get_credentials(self, provider_id: str) -> Optional[Dict]:
        """
        Retrieve credentials for a provider.

        Args:
            provider_id: Provider identifier

        Returns:
            Credentials dict or None if not found
        """
        all_creds = self._load_all()
        return all_creds.get(provider_id)

    def delete_credentials(self, provider_id: str) -> bool:
        """Delete credentials for a provider."""
        try:
            all_creds = self._load_all()
            if provider_id in all_creds:
                del all_creds[provider_id]
                self._save_all(all_creds)
                return True
            return False
        except Exception:
            return False

    def list_saved_providers(self) -> List[str]:
        """List all providers with saved credentials."""
        all_creds = self._load_all()
        return list(all_creds.keys())

    def _load_all(self) -> Dict:
        """Load all credentials from storage."""
        if not self.cred_file.exists():
            return {}

        try:
            with open(self.cred_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_all(self, credentials: Dict) -> None:
        """Save all credentials to storage."""
        with open(self.cred_file, 'w') as f:
            json.dump(credentials, f, indent=2)

        # Set restrictive file permissions
        if os.name != 'nt':
            os.chmod(self.cred_file, 0o600)


# Singleton instance
_credential_manager = None


def get_credential_manager() -> CredentialManager:
    """Get the global credential manager instance."""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    return _credential_manager
