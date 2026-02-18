"""
Unit tests for Permission Integration.

Tests integration of permissions with Phase 3 components (router, registry, hardware discovery).

Author: Frankenstein 1.0 Team
Phase: 3, Step 6, Test Suite 6
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from integration.permission_integration import (
    PermissionIntegration,
    get_permission_integration,
    require_routing_permission,
    require_provider_permission,
)
from permissions.permission_manager import PermissionDeniedError


@pytest.fixture
def mock_permission_manager():
    """Mock permission manager."""
    with patch('integration.permission_integration.get_permission_manager') as mock_pm:
        mock_instance = MagicMock()
        mock_instance.get_user_role.return_value = "Admin"
        mock_instance.validate_operation.return_value = None
        mock_instance.check_provider_access.return_value = True
        mock_pm.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_audit_logger():
    """Mock audit logger."""
    with patch('integration.permission_integration.get_audit_logger') as mock_al:
        mock_instance = MagicMock()
        mock_al.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_validate_provider():
    """Mock validate_provider function."""
    with patch('integration.permission_integration.validate_provider') as mock_vp:
        mock_vp.return_value = True
        yield mock_vp


@pytest.fixture
def mock_get_category():
    """Mock get_provider_category function."""
    with patch('integration.permission_integration.get_provider_category') as mock_gc:
        mock_gc.return_value = "quantum"
        yield mock_gc


@pytest.fixture
def integration(mock_permission_manager, mock_audit_logger, mock_validate_provider, mock_get_category):
    """Create a fresh PermissionIntegration instance for each test."""
    # Reset singleton
    import integration.permission_integration
    integration.permission_integration._integration = None

    instance = PermissionIntegration()
    # Set as singleton for tests that use get_permission_integration()
    integration.permission_integration._integration = instance
    return instance


class TestSingleton:
    """Test singleton pattern."""

    def test_singleton_instance(self, integration):
        """Verify only one instance is created."""
        integration1 = integration
        integration2 = get_permission_integration()
        assert integration1 is integration2


class TestJobSubmissionPermission:
    """Test job submission permission checks."""

    def test_check_quantum_job_permission_success(self, integration, mock_permission_manager):
        """Test successful quantum job permission check."""
        integration.check_job_submission_permission("quantum", "IBM Quantum")

        # Verify validate_operation was called with quantum_job_submit
        mock_permission_manager.validate_operation.assert_called_once()
        call_args = mock_permission_manager.validate_operation.call_args
        assert call_args[0][0] == "quantum_job_submit"
        assert call_args[1]["provider_name"] == "IBM Quantum"

    def test_check_classical_job_permission_success(self, integration, mock_permission_manager):
        """Test successful classical job permission check."""
        integration.check_job_submission_permission("classical", "NVIDIA CUDA")

        # Verify validate_operation was called with classical_compute_submit
        call_args = mock_permission_manager.validate_operation.call_args
        assert call_args[0][0] == "classical_compute_submit"
        assert call_args[1]["provider_name"] == "NVIDIA CUDA"

    def test_check_job_permission_invalid_provider(self, integration, mock_validate_provider):
        """Test job permission check with invalid provider."""
        mock_validate_provider.return_value = False

        with pytest.raises(ValueError, match="Unknown provider"):
            integration.check_job_submission_permission("quantum", "InvalidProvider")

    def test_check_job_permission_invalid_type(self, integration):
        """Test job permission check with invalid job type."""
        with pytest.raises(ValueError, match="Unknown job type"):
            integration.check_job_submission_permission("invalid_type", "IBM Quantum")

    def test_check_job_permission_denied(self, integration, mock_permission_manager):
        """Test job permission denied."""
        mock_permission_manager.validate_operation.side_effect = PermissionDeniedError("Access denied")

        with pytest.raises(PermissionDeniedError):
            integration.check_job_submission_permission("quantum", "IBM Quantum")

    def test_check_job_permission_logs_success(self, integration, mock_audit_logger):
        """Test that successful permission check is logged."""
        integration.check_job_submission_permission("quantum", "AWS Braket")

        # Verify audit logger was called
        mock_audit_logger.log_action.assert_called_once()
        call_args = mock_audit_logger.log_action.call_args[1]
        assert call_args["action"] == "quantum_job_permission_check"
        assert call_args["result"] == "success"
        assert call_args["provider_name"] == "AWS Braket"


class TestProviderAccess:
    """Test provider access checks."""

    def test_check_provider_access_success(self, integration, mock_permission_manager):
        """Test successful provider access check."""
        has_access = integration.check_provider_access("IBM Quantum")

        assert has_access is True
        mock_permission_manager.check_provider_access.assert_called_once_with("Admin", "IBM Quantum")

    def test_check_provider_access_denied(self, integration, mock_permission_manager):
        """Test provider access denied."""
        mock_permission_manager.check_provider_access.return_value = False

        has_access = integration.check_provider_access("IBM Quantum")

        assert has_access is False

    def test_check_provider_access_invalid_provider(self, integration, mock_validate_provider):
        """Test provider access check with invalid provider."""
        mock_validate_provider.return_value = False

        has_access = integration.check_provider_access("InvalidProvider")

        assert has_access is False

    def test_check_provider_access_logs_result(self, integration, mock_audit_logger):
        """Test that access check is logged."""
        integration.check_provider_access("Azure Quantum")

        mock_audit_logger.log_action.assert_called_once()
        call_args = mock_audit_logger.log_action.call_args[1]
        assert call_args["action"] == "provider_access_check"
        assert call_args["resource"] == "Azure Quantum"
        assert call_args["result"] == "success"


class TestLoggingActions:
    """Test logging helper methods."""

    def test_log_router_action(self, integration, mock_audit_logger):
        """Test logging router action."""
        integration.log_router_action(
            "route_to_provider",
            "IBM Quantum",
            "success",
            "Routed quantum job"
        )

        mock_audit_logger.log_action.assert_called_once()
        call_args = mock_audit_logger.log_action.call_args[1]
        assert call_args["action"] == "route_to_provider"
        assert call_args["resource"] == "intelligent_router"
        assert call_args["result"] == "success"
        assert call_args["provider_name"] == "IBM Quantum"
        assert call_args["details"] == "Routed quantum job"

    def test_log_registry_action(self, integration, mock_audit_logger):
        """Test logging registry action."""
        integration.log_registry_action(
            "provider_api_call",
            "AWS Braket",
            "success",
            "API call successful"
        )

        call_args = mock_audit_logger.log_action.call_args[1]
        assert call_args["action"] == "provider_api_call"
        assert call_args["resource"] == "provider_registry"
        assert call_args["result"] == "success"
        assert call_args["provider_name"] == "AWS Braket"

    def test_log_discovery_action_with_provider(self, integration, mock_audit_logger):
        """Test logging discovery action with provider."""
        integration.log_discovery_action(
            "hardware_detected",
            "gpu_hardware",
            "success",
            "NVIDIA CUDA",
            "CUDA hardware detected"
        )

        call_args = mock_audit_logger.log_action.call_args[1]
        assert call_args["action"] == "hardware_detected"
        assert call_args["resource"] == "gpu_hardware"
        assert call_args["result"] == "success"
        assert call_args["provider_name"] == "NVIDIA CUDA"
        assert call_args["details"] == "CUDA hardware detected"

    def test_log_discovery_action_without_provider(self, integration, mock_audit_logger):
        """Test logging discovery action without provider."""
        integration.log_discovery_action(
            "system_scan",
            "system_hardware",
            "success",
            None,
            "Full system scan completed"
        )

        call_args = mock_audit_logger.log_action.call_args[1]
        assert call_args["action"] == "system_scan"
        assert "provider_name" not in call_args or call_args["provider_name"] is None


class TestProviderFiltering:
    """Test provider list filtering."""

    def test_validate_and_filter_providers_all_valid(self, integration, mock_permission_manager):
        """Test filtering when all providers are valid and accessible."""
        mock_permission_manager.check_provider_access.return_value = True

        provider_list = ["IBM Quantum", "AWS Braket", "Azure Quantum"]
        filtered = integration.validate_and_filter_providers(provider_list)

        assert len(filtered) == 3
        assert "IBM Quantum" in filtered
        assert "AWS Braket" in filtered
        assert "Azure Quantum" in filtered

    def test_validate_and_filter_providers_some_denied(self, integration, mock_permission_manager):
        """Test filtering when some providers are denied."""
        # IBM Quantum allowed, AWS Braket denied
        mock_permission_manager.check_provider_access.side_effect = lambda role, provider: provider == "IBM Quantum"

        provider_list = ["IBM Quantum", "AWS Braket"]
        filtered = integration.validate_and_filter_providers(provider_list)

        assert len(filtered) == 1
        assert "IBM Quantum" in filtered
        assert "AWS Braket" not in filtered

    def test_validate_and_filter_providers_invalid_provider(self, integration, mock_validate_provider):
        """Test filtering with invalid provider."""
        # Only valid providers should pass validate_provider
        mock_validate_provider.side_effect = lambda p: p in ["IBM Quantum", "AWS Braket"]

        provider_list = ["IBM Quantum", "InvalidProvider", "AWS Braket"]
        filtered = integration.validate_and_filter_providers(provider_list)

        # InvalidProvider should be filtered out
        assert "InvalidProvider" not in filtered

    def test_validate_and_filter_providers_empty_list(self, integration):
        """Test filtering empty provider list."""
        filtered = integration.validate_and_filter_providers([])
        assert len(filtered) == 0


class TestRoutingPermissionDecorator:
    """Test @require_routing_permission decorator."""

    def test_decorator_allows_with_permission(self, integration, mock_permission_manager, mock_audit_logger, mock_validate_provider, mock_get_category):
        """Test decorator allows execution with permission."""
        # Reset mocks
        mock_permission_manager.validate_operation.reset_mock()

        @require_routing_permission
        def route(self, workload_spec):
            return {"provider": "IBM Quantum", "status": "success"}

        # Create mock object
        mock_obj = Mock()

        # Execute decorated function
        result = route(mock_obj, {"workload_type": "quantum"})

        assert result["provider"] == "IBM Quantum"
        assert result["status"] == "success"

        # Verify permission check was performed
        mock_permission_manager.validate_operation.assert_called_once()

    def test_decorator_denies_without_permission(self, integration, mock_permission_manager, mock_audit_logger, mock_validate_provider, mock_get_category):
        """Test decorator denies execution without permission."""
        # Reset the mock side effect after integration fixture used it
        mock_permission_manager.validate_operation.reset_mock()
        mock_permission_manager.validate_operation.side_effect = PermissionDeniedError("Access denied")

        @require_routing_permission
        def route(self, workload_spec):
            return {"provider": "IBM Quantum", "status": "success"}

        mock_obj = Mock()

        with pytest.raises(PermissionDeniedError):
            route(mock_obj, {"workload_type": "quantum"})

    def test_decorator_logs_successful_route(self, integration, mock_permission_manager, mock_audit_logger, mock_validate_provider, mock_get_category):
        """Test decorator logs successful routing."""
        # Reset mocks
        mock_audit_logger.reset_mock()
        mock_permission_manager.validate_operation.reset_mock()
        mock_permission_manager.validate_operation.side_effect = None

        @require_routing_permission
        def route(self, workload_spec):
            return {"provider": "AWS Braket", "status": "success"}

        mock_obj = Mock()
        route(mock_obj, {"workload_type": "quantum"})

        # Verify audit logging occurred
        assert mock_audit_logger.log_action.called


class TestProviderPermissionDecorator:
    """Test @require_provider_permission decorator."""

    def test_decorator_allows_with_permission(self, mock_permission_manager, mock_audit_logger, mock_validate_provider, mock_get_category):
        """Test decorator allows execution with permission."""
        mock_permission_manager.check_provider_access.return_value = True

        @require_provider_permission
        def call_provider_api(self, provider_name):
            return {"status": "success"}

        mock_obj = Mock()
        result = call_provider_api(mock_obj, "IBM Quantum")

        assert result["status"] == "success"

    def test_decorator_denies_without_permission(self, mock_permission_manager, mock_audit_logger, mock_validate_provider, mock_get_category):
        """Test decorator denies execution without permission."""
        # Reset singleton to get fresh integration
        import integration.permission_integration
        integration.permission_integration._integration = None

        mock_permission_manager.check_provider_access.return_value = False

        @require_provider_permission
        def call_provider_api(self, provider_name):
            return {"status": "success"}

        mock_obj = Mock()

        with pytest.raises(PermissionDeniedError, match="Access to provider 'AWS Braket' denied"):
            call_provider_api(mock_obj, "AWS Braket")

    def test_decorator_logs_api_call(self, mock_permission_manager, mock_audit_logger, mock_validate_provider, mock_get_category):
        """Test decorator logs API calls."""
        # Reset singleton
        import integration.permission_integration
        integration.permission_integration._integration = None

        mock_permission_manager.check_provider_access.return_value = True

        @require_provider_permission
        def call_provider_api(self, provider_name):
            return {"status": "success"}

        mock_obj = Mock()
        call_provider_api(mock_obj, "Azure Quantum")

        # Verify logging occurred
        assert mock_audit_logger.log_action.called

        # Check that success was logged
        call_args_list = mock_audit_logger.log_action.call_args_list
        success_logged = any(
            call[1].get("result") == "success" and call[1].get("action") == "provider_api_call"
            for call in call_args_list
        )
        assert success_logged

    def test_decorator_logs_api_error(self, mock_permission_manager, mock_audit_logger, mock_validate_provider, mock_get_category):
        """Test decorator logs API errors."""
        # Reset singleton
        import integration.permission_integration
        integration.permission_integration._integration = None

        mock_permission_manager.check_provider_access.return_value = True

        @require_provider_permission
        def call_provider_api(self, provider_name):
            raise Exception("API error")

        mock_obj = Mock()

        with pytest.raises(Exception, match="API error"):
            call_provider_api(mock_obj, "Google Quantum AI")

        # Verify error was logged
        call_args_list = mock_audit_logger.log_action.call_args_list
        error_logged = any(
            call[1].get("result") == "error"
            for call in call_args_list
        )
        assert error_logged


class TestUserRoleHandling:
    """Test user role handling in integration."""

    def test_check_job_permission_with_custom_role(self, integration, mock_permission_manager):
        """Test job permission check with custom user role."""
        integration.check_job_submission_permission("quantum", "IBM Quantum", user_role="User")

        # Verify custom role was used
        call_args = mock_permission_manager.validate_operation.call_args
        assert call_args[1]["user_role"] == "User"

    def test_check_provider_access_with_custom_role(self, integration, mock_permission_manager):
        """Test provider access check with custom user role."""
        integration.check_provider_access("AWS Braket", user_role="ReadOnly")

        # Verify custom role was used
        mock_permission_manager.check_provider_access.assert_called_with("ReadOnly", "AWS Braket")

    def test_filter_providers_with_custom_role(self, integration, mock_permission_manager):
        """Test provider filtering with custom user role."""
        provider_list = ["IBM Quantum", "AWS Braket"]
        integration.validate_and_filter_providers(provider_list, user_role="Agent")

        # Verify custom role was used in checks
        calls = mock_permission_manager.check_provider_access.call_args_list
        assert all(call[0][0] == "Agent" for call in calls)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
