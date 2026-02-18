"""
Unit tests for RBAC (Role-Based Access Control) system.

Tests all 4 roles, permissions, and provider access for all 28 providers.

Author: Frankenstein 1.0 Team
Phase: 3, Step 6, Test Suite 1
"""

import pytest
from permissions.rbac import (
    Role,
    ProviderCategory,
    PROVIDER_CATEGORIES,
    ALL_PROVIDERS,
    ROLE_PERMISSIONS,
    get_permissions,
    get_provider_access,
    get_resource_limits,
    get_providers_by_category,
    get_provider_category,
    validate_provider,
    get_quantum_providers,
    get_classical_providers,
)


class TestProviderDefinitions:
    """Test that all 28 providers are correctly defined."""

    def test_all_providers_count(self):
        """Verify exactly 28 providers are defined."""
        assert len(ALL_PROVIDERS) == 28, f"Expected 28 providers, got {len(ALL_PROVIDERS)}"

    def test_quantum_providers_count(self):
        """Verify exactly 15 quantum providers."""
        quantum = PROVIDER_CATEGORIES["quantum"]
        assert len(quantum) == 15, f"Expected 15 quantum providers, got {len(quantum)}"

    def test_classical_gpu_quantum_count(self):
        """Verify exactly 2 classical GPU/quantum providers."""
        classical_gpu = PROVIDER_CATEGORIES["classical_gpu_quantum"]
        assert len(classical_gpu) == 2, f"Expected 2 GPU/quantum providers, got {len(classical_gpu)}"

    def test_classical_compute_count(self):
        """Verify exactly 11 classical compute providers."""
        classical = PROVIDER_CATEGORIES["classical_compute"]
        assert len(classical) == 11, f"Expected 11 classical providers, got {len(classical)}"

    def test_no_duplicate_providers(self):
        """Ensure no provider appears in multiple categories."""
        all_categorized = []
        for providers in PROVIDER_CATEGORIES.values():
            all_categorized.extend(providers)

        assert len(all_categorized) == len(set(all_categorized)), "Duplicate providers found"

    def test_all_providers_categorized(self):
        """Verify ALL_PROVIDERS matches sum of all categories."""
        all_categorized = []
        for providers in PROVIDER_CATEGORIES.values():
            all_categorized.extend(providers)

        assert set(ALL_PROVIDERS) == set(all_categorized), "Mismatch between ALL_PROVIDERS and categories"


class TestRoleDefinitions:
    """Test that all 4 roles are correctly defined."""

    def test_all_roles_defined(self):
        """Verify all 4 roles exist."""
        assert len(Role) == 4, f"Expected 4 roles, got {len(Role)}"
        assert Role.ADMIN in ROLE_PERMISSIONS
        assert Role.USER in ROLE_PERMISSIONS
        assert Role.AGENT in ROLE_PERMISSIONS
        assert Role.READONLY in ROLE_PERMISSIONS

    def test_admin_permissions(self):
        """Verify Admin role has all permissions."""
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN].permissions
        assert admin_perms["quantum_job_submit"] is True
        assert admin_perms["classical_compute_submit"] is True
        assert admin_perms["provider_access_all"] is True
        assert admin_perms["credential_view"] is True
        assert admin_perms["credential_modify"] is True
        assert admin_perms["system_config_modify"] is True
        assert admin_perms["automation_enable"] is True
        assert admin_perms["agent_deploy"] is True
        assert admin_perms["audit_view"] is True
        assert admin_perms["hardware_optimization"] is True

    def test_user_permissions(self):
        """Verify User role has appropriate permissions."""
        user_perms = ROLE_PERMISSIONS[Role.USER].permissions
        assert user_perms["quantum_job_submit"] is True
        assert user_perms["classical_compute_submit"] is True
        assert user_perms["provider_access_all"] is True
        assert user_perms["credential_view"] is True
        assert user_perms["credential_modify"] is True
        assert user_perms["system_config_modify"] is False  # Cannot modify system
        assert user_perms["agent_deploy"] is False  # Cannot deploy agents
        assert user_perms["automation_enable"] is True
        assert user_perms["audit_view"] is True
        assert user_perms["hardware_optimization"] is True

    def test_agent_permissions(self):
        """Verify Agent role has limited permissions."""
        agent_perms = ROLE_PERMISSIONS[Role.AGENT].permissions
        assert agent_perms["quantum_job_submit"] is True
        assert agent_perms["classical_compute_submit"] is True
        assert agent_perms["provider_access_all"] is True
        assert agent_perms["credential_view"] is False  # Cannot view credentials
        assert agent_perms["credential_modify"] is False
        assert agent_perms["system_config_modify"] is False
        assert agent_perms["automation_enable"] is False
        assert agent_perms["agent_deploy"] is False
        assert agent_perms["audit_view"] is False  # Cannot view audit
        assert agent_perms["hardware_optimization"] is True

    def test_readonly_permissions(self):
        """Verify ReadOnly role has minimal permissions."""
        readonly_perms = ROLE_PERMISSIONS[Role.READONLY].permissions
        assert readonly_perms["quantum_job_submit"] is False
        assert readonly_perms["classical_compute_submit"] is False
        assert readonly_perms["provider_access_all"] is False
        assert readonly_perms["credential_view"] is False
        assert readonly_perms["credential_modify"] is False
        assert readonly_perms["system_config_modify"] is False
        assert readonly_perms["automation_enable"] is False
        assert readonly_perms["agent_deploy"] is False
        assert readonly_perms["audit_view"] is True  # Only can view audit
        assert readonly_perms["hardware_optimization"] is False


class TestProviderAccess:
    """Test provider access for each role."""

    def test_admin_has_all_providers(self):
        """Admin should have access to all 28 providers."""
        admin_providers = ROLE_PERMISSIONS[Role.ADMIN].provider_access
        assert len(admin_providers) == 28
        assert set(admin_providers) == set(ALL_PROVIDERS)

    def test_user_has_all_providers(self):
        """User should have access to all 28 providers."""
        user_providers = ROLE_PERMISSIONS[Role.USER].provider_access
        assert len(user_providers) == 28
        assert set(user_providers) == set(ALL_PROVIDERS)

    def test_agent_has_all_providers(self):
        """Agent should have access to all 28 providers."""
        agent_providers = ROLE_PERMISSIONS[Role.AGENT].provider_access
        assert len(agent_providers) == 28
        assert set(agent_providers) == set(ALL_PROVIDERS)

    def test_readonly_has_no_providers(self):
        """ReadOnly should have no provider access."""
        readonly_providers = ROLE_PERMISSIONS[Role.READONLY].provider_access
        assert len(readonly_providers) == 0


class TestResourceLimits:
    """Test resource limits for each role."""

    def test_admin_limits(self):
        """Verify Admin has highest resource limits."""
        limits = ROLE_PERMISSIONS[Role.ADMIN].resource_limits
        assert limits["max_qubits"] == 1000
        assert limits["max_compute_cores"] == 16
        assert limits["max_gpu_memory_gb"] == 32
        assert limits["max_cost_per_job_usd"] == 10000
        assert limits["max_concurrent_jobs"] == 50

    def test_user_limits(self):
        """Verify User has moderate resource limits."""
        limits = ROLE_PERMISSIONS[Role.USER].resource_limits
        assert limits["max_qubits"] == 100
        assert limits["max_compute_cores"] == 8
        assert limits["max_gpu_memory_gb"] == 16
        assert limits["max_cost_per_job_usd"] == 1000
        assert limits["max_concurrent_jobs"] == 20

    def test_agent_limits(self):
        """Verify Agent has lower resource limits."""
        limits = ROLE_PERMISSIONS[Role.AGENT].resource_limits
        assert limits["max_qubits"] == 50
        assert limits["max_compute_cores"] == 4
        assert limits["max_gpu_memory_gb"] == 8
        assert limits["max_cost_per_job_usd"] == 100
        assert limits["max_concurrent_jobs"] == 10

    def test_readonly_limits(self):
        """Verify ReadOnly has zero resource limits."""
        limits = ROLE_PERMISSIONS[Role.READONLY].resource_limits
        assert limits["max_qubits"] == 0
        assert limits["max_compute_cores"] == 0
        assert limits["max_gpu_memory_gb"] == 0
        assert limits["max_cost_per_job_usd"] == 0
        assert limits["max_concurrent_jobs"] == 0


class TestGetPermissions:
    """Test get_permissions() function."""

    def test_get_admin_permissions(self):
        """Test retrieving Admin permissions."""
        perms = get_permissions("Admin")
        assert isinstance(perms, dict)
        assert perms["system_config_modify"] is True

    def test_get_user_permissions(self):
        """Test retrieving User permissions."""
        perms = get_permissions("User")
        assert isinstance(perms, dict)
        assert perms["system_config_modify"] is False

    def test_get_agent_permissions(self):
        """Test retrieving Agent permissions."""
        perms = get_permissions("Agent")
        assert isinstance(perms, dict)
        assert perms["credential_view"] is False

    def test_get_readonly_permissions(self):
        """Test retrieving ReadOnly permissions."""
        perms = get_permissions("ReadOnly")
        assert isinstance(perms, dict)
        assert perms["audit_view"] is True

    def test_invalid_role(self):
        """Test that invalid role raises ValueError."""
        with pytest.raises(ValueError, match="Invalid role"):
            get_permissions("InvalidRole")

    def test_returns_copy(self):
        """Ensure get_permissions returns a copy, not reference."""
        perms1 = get_permissions("Admin")
        perms2 = get_permissions("Admin")
        perms1["new_key"] = True
        assert "new_key" not in perms2


class TestGetProviderAccess:
    """Test get_provider_access() function."""

    def test_get_admin_providers(self):
        """Test retrieving Admin provider access."""
        providers = get_provider_access("Admin")
        assert len(providers) == 28
        assert "IBM Quantum" in providers
        assert "NVIDIA CUDA" in providers

    def test_get_readonly_providers(self):
        """Test retrieving ReadOnly provider access."""
        providers = get_provider_access("ReadOnly")
        assert len(providers) == 0

    def test_invalid_role(self):
        """Test that invalid role raises ValueError."""
        with pytest.raises(ValueError, match="Invalid role"):
            get_provider_access("InvalidRole")

    def test_returns_copy(self):
        """Ensure get_provider_access returns a copy."""
        providers1 = get_provider_access("Admin")
        providers2 = get_provider_access("Admin")
        providers1.append("Fake Provider")
        assert "Fake Provider" not in providers2


class TestGetResourceLimits:
    """Test get_resource_limits() function."""

    def test_get_admin_limits(self):
        """Test retrieving Admin resource limits."""
        limits = get_resource_limits("Admin")
        assert limits["max_qubits"] == 1000

    def test_get_user_limits(self):
        """Test retrieving User resource limits."""
        limits = get_resource_limits("User")
        assert limits["max_qubits"] == 100

    def test_invalid_role(self):
        """Test that invalid role raises ValueError."""
        with pytest.raises(ValueError, match="Invalid role"):
            get_resource_limits("InvalidRole")


class TestProviderCategoryFunctions:
    """Test provider category helper functions."""

    def test_get_providers_by_category_quantum(self):
        """Test getting quantum providers."""
        quantum = get_providers_by_category("quantum")
        assert len(quantum) == 15
        assert "IBM Quantum" in quantum

    def test_get_providers_by_category_classical(self):
        """Test getting classical compute providers."""
        classical = get_providers_by_category("classical_compute")
        assert len(classical) == 11
        assert "NVIDIA CUDA" in classical

    def test_get_providers_by_category_invalid(self):
        """Test invalid category raises ValueError."""
        with pytest.raises(ValueError, match="Invalid category"):
            get_providers_by_category("invalid_category")

    def test_get_provider_category(self):
        """Test determining provider category."""
        assert get_provider_category("IBM Quantum") == "quantum"
        assert get_provider_category("NVIDIA CUDA") == "classical_compute"
        assert get_provider_category("cuQuantum") == "classical_gpu_quantum"

    def test_get_provider_category_invalid(self):
        """Test invalid provider raises ValueError."""
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider_category("Invalid Provider")

    def test_validate_provider_valid(self):
        """Test validating valid providers."""
        assert validate_provider("IBM Quantum") is True
        assert validate_provider("NVIDIA CUDA") is True

    def test_validate_provider_invalid(self):
        """Test validating invalid providers."""
        assert validate_provider("Invalid Provider") is False
        assert validate_provider("") is False

    def test_get_quantum_providers(self):
        """Test getting all quantum providers."""
        quantum = get_quantum_providers()
        assert len(quantum) == 15
        assert "IBM Quantum" in quantum

    def test_get_classical_providers(self):
        """Test getting all classical providers (including GPU/quantum)."""
        classical = get_classical_providers()
        assert len(classical) == 13  # 2 GPU/quantum + 11 classical
        assert "cuQuantum" in classical
        assert "NVIDIA CUDA" in classical


class TestLazyLoading:
    """Test lazy loading behavior."""

    def test_module_loaded_flag(self):
        """Verify module loading tracking."""
        from permissions import rbac
        assert rbac._MODULE_LOADED is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
