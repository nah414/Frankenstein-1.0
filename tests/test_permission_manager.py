"""
Unit tests for Permission Manager.

Tests permission checks, provider access validation, and role management
for all 28 quantum and classical providers.

Author: Frankenstein 1.0 Team
Phase: 3, Step 6, Test Suite 2
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import threading
import time

from permissions.permission_manager import (
    PermissionManager,
    PermissionDeniedError,
    get_permission_manager,
)


@pytest.fixture
def temp_config_dir(monkeypatch):
    """Create a temporary config directory for testing."""
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir) / ".frankenstein" / "config"
    temp_path.mkdir(parents=True, exist_ok=True)

    # Monkey patch the config directory
    monkeypatch.setattr(
        "permissions.permission_manager.Path.home",
        lambda: Path(temp_dir)
    )

    yield temp_path

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def fresh_manager(temp_config_dir):
    """Create a fresh PermissionManager instance for each test."""
    # Reset singleton
    PermissionManager._instance = None
    PermissionManager._initialized = False

    manager = PermissionManager()
    yield manager

    # Cleanup
    PermissionManager._instance = None
    PermissionManager._initialized = False


class TestSingletonBehavior:
    """Test singleton pattern implementation."""

    def test_singleton_instance(self, fresh_manager):
        """Verify only one instance is created."""
        manager1 = fresh_manager
        manager2 = PermissionManager()
        assert manager1 is manager2

    def test_get_permission_manager(self, fresh_manager):
        """Test helper function returns singleton."""
        manager1 = fresh_manager
        manager2 = get_permission_manager()
        assert manager1 is manager2


class TestRoleManagement:
    """Test role loading, saving, and management."""

    def test_default_role_is_admin(self, fresh_manager):
        """First run should default to Admin role."""
        assert fresh_manager.get_user_role() == "Admin"

    def test_set_user_role_as_admin(self, fresh_manager):
        """Admin can change user role."""
        fresh_manager.set_user_role("User")
        assert fresh_manager.get_user_role() == "User"

    def test_set_user_role_non_admin_fails(self, fresh_manager):
        """Non-Admin cannot change user role."""
        fresh_manager.set_user_role("User")

        with pytest.raises(PermissionDeniedError, match="Only Admin can change user role"):
            fresh_manager.set_user_role("Agent")

    def test_set_invalid_role(self, fresh_manager):
        """Setting invalid role raises ValueError."""
        with pytest.raises(ValueError, match="Invalid role"):
            fresh_manager.set_user_role("InvalidRole")

    def test_role_persistence(self, fresh_manager, temp_config_dir):
        """Role persists across manager instances."""
        fresh_manager.set_user_role("Agent")

        # Create new instance (simulating restart)
        PermissionManager._instance = None
        PermissionManager._initialized = False
        manager2 = PermissionManager()

        assert manager2.get_user_role() == "Agent"

    def test_reset_to_defaults(self, fresh_manager):
        """Test resetting configuration to defaults."""
        # Stay as Admin (default role) to test reset
        fresh_manager.reset_to_defaults()
        assert fresh_manager.get_user_role() == "Admin"

    def test_reset_non_admin_fails(self, fresh_manager):
        """Non-Admin cannot reset configuration."""
        fresh_manager.set_user_role("User")

        with pytest.raises(PermissionDeniedError):
            fresh_manager.reset_to_defaults()


class TestPermissionChecks:
    """Test permission checking for all operations."""

    def test_check_admin_permissions(self, fresh_manager):
        """Admin should have all permissions."""
        assert fresh_manager.check_permission("Admin", "quantum_job_submit") is True
        assert fresh_manager.check_permission("Admin", "classical_compute_submit") is True
        assert fresh_manager.check_permission("Admin", "credential_modify") is True
        assert fresh_manager.check_permission("Admin", "system_config_modify") is True

    def test_check_user_permissions(self, fresh_manager):
        """User should have limited permissions."""
        assert fresh_manager.check_permission("User", "quantum_job_submit") is True
        assert fresh_manager.check_permission("User", "system_config_modify") is False
        assert fresh_manager.check_permission("User", "agent_deploy") is False

    def test_check_agent_permissions(self, fresh_manager):
        """Agent should have restricted permissions."""
        assert fresh_manager.check_permission("Agent", "quantum_job_submit") is True
        assert fresh_manager.check_permission("Agent", "credential_view") is False
        assert fresh_manager.check_permission("Agent", "audit_view") is False

    def test_check_readonly_permissions(self, fresh_manager):
        """ReadOnly should have minimal permissions."""
        assert fresh_manager.check_permission("ReadOnly", "quantum_job_submit") is False
        assert fresh_manager.check_permission("ReadOnly", "audit_view") is True

    def test_invalid_role_permission_check(self, fresh_manager):
        """Invalid role should deny all permissions."""
        assert fresh_manager.check_permission("InvalidRole", "quantum_job_submit") is False

    def test_invalid_operation_permission_check(self, fresh_manager):
        """Invalid operation should return False."""
        assert fresh_manager.check_permission("Admin", "invalid_operation") is False


class TestProviderAccess:
    """Test provider access validation for all 28 providers."""

    def test_admin_access_all_providers(self, fresh_manager):
        """Admin should have access to all 28 providers."""
        # Test quantum providers
        assert fresh_manager.check_provider_access("Admin", "IBM Quantum") is True
        assert fresh_manager.check_provider_access("Admin", "AWS Braket") is True

        # Test classical providers
        assert fresh_manager.check_provider_access("Admin", "NVIDIA CUDA") is True
        assert fresh_manager.check_provider_access("Admin", "Intel oneAPI") is True

        # Test GPU/quantum hybrid
        assert fresh_manager.check_provider_access("Admin", "cuQuantum") is True

    def test_user_access_all_providers(self, fresh_manager):
        """User should have access to all 28 providers."""
        providers = fresh_manager.get_accessible_providers("User")
        assert len(providers) == 28

    def test_agent_access_all_providers(self, fresh_manager):
        """Agent should have access to all 28 providers."""
        providers = fresh_manager.get_accessible_providers("Agent")
        assert len(providers) == 28

    def test_readonly_no_provider_access(self, fresh_manager):
        """ReadOnly should have no provider access."""
        assert fresh_manager.check_provider_access("ReadOnly", "IBM Quantum") is False
        assert fresh_manager.check_provider_access("ReadOnly", "NVIDIA CUDA") is False

        providers = fresh_manager.get_accessible_providers("ReadOnly")
        assert len(providers) == 0

    def test_invalid_provider_access(self, fresh_manager):
        """Invalid provider should deny access."""
        assert fresh_manager.check_provider_access("Admin", "Invalid Provider") is False

    def test_get_accessible_providers(self, fresh_manager):
        """Test retrieving full provider access list."""
        admin_providers = fresh_manager.get_accessible_providers("Admin")
        assert len(admin_providers) == 28
        assert "IBM Quantum" in admin_providers
        assert "NVIDIA CUDA" in admin_providers

    def test_invalid_role_provider_access(self, fresh_manager):
        """Invalid role should raise ValueError for get_accessible_providers."""
        with pytest.raises(ValueError):
            fresh_manager.get_accessible_providers("InvalidRole")


class TestResourceLimits:
    """Test resource limit retrieval."""

    def test_get_admin_resource_limits(self, fresh_manager):
        """Test Admin resource limits."""
        limits = fresh_manager.get_resource_limits("Admin")
        assert limits["max_qubits"] == 1000
        assert limits["max_compute_cores"] == 16
        assert limits["max_gpu_memory_gb"] == 32
        assert limits["max_cost_per_job_usd"] == 10000
        assert limits["max_concurrent_jobs"] == 50

    def test_get_user_resource_limits(self, fresh_manager):
        """Test User resource limits."""
        limits = fresh_manager.get_resource_limits("User")
        assert limits["max_qubits"] == 100
        assert limits["max_compute_cores"] == 8

    def test_get_agent_resource_limits(self, fresh_manager):
        """Test Agent resource limits."""
        limits = fresh_manager.get_resource_limits("Agent")
        assert limits["max_qubits"] == 50
        assert limits["max_compute_cores"] == 4

    def test_get_readonly_resource_limits(self, fresh_manager):
        """Test ReadOnly resource limits (all zero)."""
        limits = fresh_manager.get_resource_limits("ReadOnly")
        assert limits["max_qubits"] == 0
        assert limits["max_concurrent_jobs"] == 0

    def test_invalid_role_resource_limits(self, fresh_manager):
        """Invalid role should raise ValueError."""
        with pytest.raises(ValueError):
            fresh_manager.get_resource_limits("InvalidRole")


class TestProviderCategory:
    """Test provider category detection."""

    def test_quantum_provider_category(self, fresh_manager):
        """Test quantum provider categorization."""
        assert fresh_manager.get_provider_category("IBM Quantum") == "quantum"
        assert fresh_manager.get_provider_category("AWS Braket") == "quantum"

    def test_classical_provider_category(self, fresh_manager):
        """Test classical provider categorization."""
        assert fresh_manager.get_provider_category("NVIDIA CUDA") == "classical_compute"
        assert fresh_manager.get_provider_category("Intel oneAPI") == "classical_compute"

    def test_gpu_quantum_provider_category(self, fresh_manager):
        """Test GPU/quantum hybrid provider categorization."""
        assert fresh_manager.get_provider_category("cuQuantum") == "classical_gpu_quantum"
        assert fresh_manager.get_provider_category("NVIDIA Quantum Cloud") == "classical_gpu_quantum"

    def test_invalid_provider_category(self, fresh_manager):
        """Invalid provider should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown provider"):
            fresh_manager.get_provider_category("Invalid Provider")


class TestValidateOperation:
    """Test operation validation helper."""

    def test_validate_allowed_operation(self, fresh_manager):
        """Valid operation should not raise error."""
        fresh_manager.validate_operation("quantum_job_submit")  # Admin by default

    def test_validate_denied_operation(self, fresh_manager):
        """Denied operation should raise PermissionDeniedError."""
        with pytest.raises(PermissionDeniedError, match="Operation .* denied"):
            fresh_manager.validate_operation("system_config_modify", user_role="User")

    def test_validate_with_provider_access(self, fresh_manager):
        """Validate operation with provider access check."""
        fresh_manager.validate_operation(
            "quantum_job_submit",
            provider_name="IBM Quantum",
            user_role="Admin"
        )

    def test_validate_denied_provider_access(self, fresh_manager):
        """Denied provider access should raise PermissionDeniedError."""
        # ReadOnly cannot submit jobs at all, so use audit_view (which they CAN do)
        # but test provider access denial
        with pytest.raises(PermissionDeniedError, match="Access to provider .* denied"):
            fresh_manager.validate_operation(
                "audit_view",  # ReadOnly HAS this permission
                provider_name="IBM Quantum",  # but NOT provider access
                user_role="ReadOnly"
            )


class TestThreadSafety:
    """Test thread-safe operations."""

    def test_concurrent_permission_checks(self, fresh_manager):
        """Test concurrent permission checks don't cause issues."""
        results = []

        def check_permission():
            for _ in range(10):
                result = fresh_manager.check_permission("Admin", "quantum_job_submit")
                results.append(result)

        threads = [threading.Thread(target=check_permission) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        # All checks should succeed
        assert all(results)
        assert len(results) == 30

    def test_concurrent_provider_access_checks(self, fresh_manager):
        """Test concurrent provider access checks."""
        results = []

        def check_access():
            for _ in range(10):
                result = fresh_manager.check_provider_access("Admin", "IBM Quantum")
                results.append(result)

        threads = [threading.Thread(target=check_access) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert all(results)
        assert len(results) == 30


class TestUtilityMethods:
    """Test utility methods."""

    def test_get_all_providers(self, fresh_manager):
        """Test getting all 28 providers."""
        providers = fresh_manager.get_all_providers()
        assert len(providers) == 28
        assert "IBM Quantum" in providers
        assert "NVIDIA CUDA" in providers

    def test_get_all_providers_returns_copy(self, fresh_manager):
        """Ensure get_all_providers returns a copy."""
        providers1 = fresh_manager.get_all_providers()
        providers2 = fresh_manager.get_all_providers()

        providers1.append("Fake Provider")
        assert "Fake Provider" not in providers2


class TestEncryption:
    """Test encrypted config storage."""

    def test_config_file_created(self, fresh_manager, temp_config_dir):
        """Config file should be created on first run."""
        config_file = temp_config_dir / "user_permissions.json"
        assert config_file.exists()

    def test_key_file_created(self, fresh_manager, temp_config_dir):
        """Encryption key file should be created."""
        key_file = temp_config_dir / "permission.key"
        assert key_file.exists()

    def test_config_encrypted(self, fresh_manager, temp_config_dir):
        """Config file should be encrypted (not plain JSON)."""
        config_file = temp_config_dir / "user_permissions.json"

        with open(config_file, 'rb') as f:
            raw_data = f.read()

        # Should not be readable as plain JSON
        try:
            import json
            json.loads(raw_data)
            assert False, "Config should be encrypted, not plain JSON"
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Expected - file is encrypted
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
