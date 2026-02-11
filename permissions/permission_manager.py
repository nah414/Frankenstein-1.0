"""
Permission Manager - Central permission checking service for Frankenstein 1.0

Provides thread-safe permission checks, provider access validation, and role management
for all 28 quantum and classical computing providers.

Author: Frankenstein 1.0 Team
Phase: 3, Step 6
"""

import json
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional
from cryptography.fernet import Fernet
import base64
import hashlib

from permissions.rbac import (
    get_permissions,
    get_provider_access,
    get_resource_limits,
    get_provider_category,
    validate_provider,
    ALL_PROVIDERS,
    Role,
)


class PermissionDeniedError(Exception):
    """Raised when a user attempts an unauthorized operation."""
    pass


class PermissionManager:
    """
    Singleton permission manager for centralized access control.

    Thread-safe singleton that manages user roles, permissions, and provider access
    for all 28 quantum and classical providers.
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the permission manager (only once)."""
        if self._initialized:
            return

        with self._lock:
            if not self._initialized:
                self._config_dir = Path.home() / ".frankenstein" / "config"
                self._config_file = self._config_dir / "user_permissions.json"
                self._key_file = self._config_dir / "permission.key"

                # Ensure config directory exists
                self._config_dir.mkdir(parents=True, exist_ok=True)

                # Initialize encryption
                self._cipher = self._initialize_encryption()

                # Load or create default config
                self._current_role = self._load_role()

                self._initialized = True

    def _initialize_encryption(self) -> Fernet:
        """Initialize or load encryption key for secure config storage."""
        if self._key_file.exists():
            with open(self._key_file, 'rb') as f:
                key = f.read()
        else:
            # Generate a deterministic key from system info
            # In production, use a proper key management system
            system_id = f"{os.name}-{Path.home()}".encode()
            key_material = hashlib.sha256(system_id).digest()
            key = base64.urlsafe_b64encode(key_material)

            with open(self._key_file, 'wb') as f:
                f.write(key)

            # Restrict permissions on key file (Unix-like systems)
            try:
                os.chmod(self._key_file, 0o600)
            except (OSError, AttributeError):
                pass  # Windows doesn't support chmod

        return Fernet(key)

    def _load_role(self) -> str:
        """
        Load user role from encrypted config file.

        Returns:
            Current user role (defaults to Admin if not set)
        """
        if not self._config_file.exists():
            # First run - default to Admin
            self._save_role("Admin")
            return "Admin"

        try:
            with open(self._config_file, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = self._cipher.decrypt(encrypted_data)
            config = json.loads(decrypted_data.decode())

            role = config.get("user_role", "Admin")

            # Validate role
            try:
                Role(role)
                return role
            except ValueError:
                # Invalid role in config, reset to Admin
                return "Admin"

        except Exception as e:
            # Config file corrupted or can't be read, default to Admin
            return "Admin"

    def _save_role(self, role: str):
        """
        Save user role to encrypted config file.

        Args:
            role: Role name to save
        """
        config = {"user_role": role}

        config_json = json.dumps(config, indent=2)
        encrypted_data = self._cipher.encrypt(config_json.encode())

        with open(self._config_file, 'wb') as f:
            f.write(encrypted_data)

    def check_permission(self, user_role: str, operation: str) -> bool:
        """
        Check if a role has permission to perform an operation.

        Args:
            user_role: Role to check (Admin, User, Agent, ReadOnly)
            operation: Permission name (e.g., 'quantum_job_submit')

        Returns:
            True if permission granted, False otherwise

        Thread-safe operation.
        """
        with self._lock:
            try:
                permissions = get_permissions(user_role)
                return permissions.get(operation, False)
            except ValueError:
                # Invalid role, deny permission
                return False

    def check_provider_access(self, user_role: str, provider_name: str) -> bool:
        """
        Check if a role has access to a specific provider.

        Args:
            user_role: Role to check (Admin, User, Agent, ReadOnly)
            provider_name: Provider name (must be one of 28 supported providers)

        Returns:
            True if access granted, False otherwise

        Thread-safe operation.
        """
        with self._lock:
            # Validate provider name
            if not validate_provider(provider_name):
                return False

            try:
                accessible_providers = get_provider_access(user_role)
                return provider_name in accessible_providers
            except ValueError:
                # Invalid role, deny access
                return False

    def get_accessible_providers(self, user_role: str) -> List[str]:
        """
        Get list of all providers accessible to a role.

        Args:
            user_role: Role to check (Admin, User, Agent, ReadOnly)

        Returns:
            List of provider names (can be empty for ReadOnly, up to 28 for others)

        Raises:
            ValueError: If role is invalid

        Thread-safe operation.
        """
        with self._lock:
            return get_provider_access(user_role)

    def get_user_role(self) -> str:
        """
        Get current user role from config.

        Returns:
            Current role name (Admin, User, Agent, ReadOnly)

        Thread-safe operation.
        """
        with self._lock:
            return self._current_role

    def set_user_role(self, role: str):
        """
        Set user role (Admin-only operation).

        Args:
            role: New role to set (Admin, User, Agent, ReadOnly)

        Raises:
            ValueError: If role is invalid
            PermissionDeniedError: If current role is not Admin

        Thread-safe operation.
        """
        with self._lock:
            # Verify current user is Admin
            if self._current_role != "Admin":
                raise PermissionDeniedError(
                    "Only Admin can change user role. Current role: " + self._current_role
                )

            # Validate new role
            try:
                Role(role)
            except ValueError:
                raise ValueError(
                    f"Invalid role: {role}. Must be one of: Admin, User, Agent, ReadOnly"
                )

            # Save and update
            self._save_role(role)
            self._current_role = role

    def get_resource_limits(self, role: str) -> Dict[str, int]:
        """
        Get resource limits for a specific role.

        Args:
            role: Role to check (Admin, User, Agent, ReadOnly)

        Returns:
            Dictionary of resource limits:
                - max_qubits: Maximum qubits allowed
                - max_compute_cores: Maximum CPU cores
                - max_gpu_memory_gb: Maximum GPU memory in GB
                - max_cost_per_job_usd: Maximum cost per job in USD
                - max_concurrent_jobs: Maximum concurrent jobs

        Raises:
            ValueError: If role is invalid

        Thread-safe operation.
        """
        with self._lock:
            return get_resource_limits(role)

    def get_provider_category(self, provider_name: str) -> str:
        """
        Get the category for a specific provider.

        Args:
            provider_name: Name of the provider

        Returns:
            Category name: 'quantum', 'classical_gpu_quantum', or 'classical_compute'

        Raises:
            ValueError: If provider is not recognized

        Thread-safe operation.
        """
        with self._lock:
            return get_provider_category(provider_name)

    def validate_operation(
        self,
        operation: str,
        provider_name: Optional[str] = None,
        user_role: Optional[str] = None
    ):
        """
        Validate an operation and raise PermissionDeniedError if unauthorized.

        Args:
            operation: Operation to validate (e.g., 'quantum_job_submit')
            provider_name: Optional provider name to check access
            user_role: Optional role to check (defaults to current user role)

        Raises:
            PermissionDeniedError: If operation or provider access denied

        Thread-safe operation.
        """
        # Don't acquire lock here - let the called methods handle their own locking
        role = user_role or self.get_user_role()

        # Check operation permission
        if not self.check_permission(role, operation):
            raise PermissionDeniedError(
                f"Operation '{operation}' denied for role '{role}'"
            )

        # Check provider access if specified
        if provider_name is not None:
            if not self.check_provider_access(role, provider_name):
                raise PermissionDeniedError(
                    f"Access to provider '{provider_name}' denied for role '{role}'"
                )

    def get_all_providers(self) -> List[str]:
        """
        Get list of all 28 supported providers.

        Returns:
            List of all provider names
        """
        return ALL_PROVIDERS.copy()

    def reset_to_defaults(self):
        """
        Reset configuration to defaults (Admin role).

        Raises:
            PermissionDeniedError: If current role is not Admin

        Thread-safe operation.
        """
        with self._lock:
            if self._current_role != "Admin":
                raise PermissionDeniedError(
                    "Only Admin can reset configuration"
                )

            self._save_role("Admin")
            self._current_role = "Admin"


# Singleton instance getter
_manager_instance = None

def get_permission_manager() -> PermissionManager:
    """
    Get the singleton PermissionManager instance.

    Returns:
        PermissionManager singleton
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = PermissionManager()
    return _manager_instance
