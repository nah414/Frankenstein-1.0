"""
Permission Integration - Integrate permissions with Phase 3 components

Adds permission checks to:
- Intelligent Router (intelligent_router.py)
- Provider Registry (provider_registry.py)
- Hardware Discovery (hardware_discovery.py)

All permission checks validate against 28 quantum and classical providers.

Author: Frankenstein 1.0 Team
Phase: 3, Step 6, Integration Layer
"""

import logging
from typing import Dict, List, Any, Optional
from functools import wraps

from permissions.permission_manager import get_permission_manager, PermissionDeniedError
from permissions.audit_logger import get_audit_logger
from permissions.rbac import get_provider_category, validate_provider

logger = logging.getLogger("frankenstein.integration.permissions")


class PermissionIntegration:
    """
    Integration layer for permission checks across Phase 3 components.

    Provides decorators and helper methods for adding permission checks
    to router, registry, and hardware discovery operations.
    """

    def __init__(self):
        """Initialize permission integration."""
        self.permission_manager = get_permission_manager()
        self.audit_logger = get_audit_logger()

    def check_job_submission_permission(
        self,
        job_type: str,
        provider_name: str,
        user_role: Optional[str] = None
    ):
        """
        Check if user has permission to submit a job to a provider.

        Args:
            job_type: Type of job ('quantum' or 'classical')
            provider_name: Name of the provider (one of 28 providers)
            user_role: Optional role to check (defaults to current user)

        Raises:
            PermissionDeniedError: If permission denied
        """
        role = user_role or self.permission_manager.get_user_role()

        # Validate provider exists
        if not validate_provider(provider_name):
            raise ValueError(f"Unknown provider: {provider_name}")

        # Check job type permission
        if job_type == "quantum":
            self.permission_manager.validate_operation(
                "quantum_job_submit",
                provider_name=provider_name,
                user_role=role
            )
        elif job_type == "classical":
            self.permission_manager.validate_operation(
                "classical_compute_submit",
                provider_name=provider_name,
                user_role=role
            )
        else:
            raise ValueError(f"Unknown job type: {job_type}")

        # Log successful permission check
        self.audit_logger.log_action(
            user_role=role,
            action=f"{job_type}_job_permission_check",
            resource=f"{provider_name} API",
            result="success",
            provider_name=provider_name,
            provider_category=get_provider_category(provider_name)
        )

    def check_provider_access(
        self,
        provider_name: str,
        user_role: Optional[str] = None
    ) -> bool:
        """
        Check if user has access to a specific provider.

        Args:
            provider_name: Name of the provider (one of 28 providers)
            user_role: Optional role to check (defaults to current user)

        Returns:
            True if access granted, False otherwise
        """
        role = user_role or self.permission_manager.get_user_role()

        # Validate provider exists
        if not validate_provider(provider_name):
            return False

        # Check provider access
        has_access = self.permission_manager.check_provider_access(role, provider_name)

        # Log access check
        self.audit_logger.log_action(
            user_role=role,
            action="provider_access_check",
            resource=f"{provider_name}",
            result="success" if has_access else "denied",
            provider_name=provider_name,
            provider_category=get_provider_category(provider_name)
        )

        return has_access

    def log_router_action(
        self,
        action: str,
        provider_name: str,
        result: str,
        details: Optional[str] = None
    ):
        """
        Log a router action to audit trail.

        Args:
            action: Action performed
            provider_name: Provider name
            result: Result of action
            details: Optional details
        """
        self.audit_logger.log_action(
            user_role=self.permission_manager.get_user_role(),
            action=action,
            resource="intelligent_router",
            result=result,
            provider_name=provider_name,
            provider_category=get_provider_category(provider_name),
            details=details
        )

    def log_registry_action(
        self,
        action: str,
        provider_name: str,
        result: str,
        details: Optional[str] = None
    ):
        """
        Log a provider registry action to audit trail.

        Args:
            action: Action performed
            provider_name: Provider name
            result: Result of action
            details: Optional details
        """
        self.audit_logger.log_action(
            user_role=self.permission_manager.get_user_role(),
            action=action,
            resource="provider_registry",
            result=result,
            provider_name=provider_name,
            provider_category=get_provider_category(provider_name),
            details=details
        )

    def log_discovery_action(
        self,
        action: str,
        resource: str,
        result: str,
        provider_name: Optional[str] = None,
        details: Optional[str] = None
    ):
        """
        Log a hardware discovery action to audit trail.

        Args:
            action: Action performed
            resource: Resource accessed
            result: Result of action
            provider_name: Optional provider name
            details: Optional details
        """
        log_kwargs = {
            "user_role": self.permission_manager.get_user_role(),
            "action": action,
            "resource": resource,
            "result": result,
            "details": details
        }

        if provider_name and validate_provider(provider_name):
            log_kwargs["provider_name"] = provider_name
            log_kwargs["provider_category"] = get_provider_category(provider_name)

        self.audit_logger.log_action(**log_kwargs)

    def validate_and_filter_providers(
        self,
        provider_list: List[str],
        user_role: Optional[str] = None
    ) -> List[str]:
        """
        Filter a list of providers based on user access permissions.

        Args:
            provider_list: List of provider names
            user_role: Optional role to check (defaults to current user)

        Returns:
            Filtered list of accessible providers
        """
        role = user_role or self.permission_manager.get_user_role()

        accessible = []
        for provider in provider_list:
            if validate_provider(provider):
                if self.permission_manager.check_provider_access(role, provider):
                    accessible.append(provider)

        return accessible


# Singleton instance
_integration = None

def get_permission_integration() -> PermissionIntegration:
    """
    Get the singleton PermissionIntegration instance.

    Returns:
        PermissionIntegration singleton
    """
    global _integration
    if _integration is None:
        _integration = PermissionIntegration()
    return _integration


# Decorator for adding permission checks to router methods
def require_routing_permission(func):
    """
    Decorator to add permission checks to routing operations.

    Usage:
        @require_routing_permission
        def route(self, workload_spec):
            ...
    """
    @wraps(func)
    def wrapper(self, workload_spec, *args, **kwargs):
        integration = get_permission_integration()

        # Determine job type from workload
        job_type = "quantum"  # Default
        if isinstance(workload_spec, dict):
            workload_type = workload_spec.get("workload_type", "")
            if "classical" in workload_type.lower() or "cpu" in workload_type.lower():
                job_type = "classical"

        # Execute the original function
        result = func(self, workload_spec, *args, **kwargs)

        # Check permission for selected provider
        if isinstance(result, dict) and "provider" in result:
            provider_name = result["provider"]
            try:
                integration.check_job_submission_permission(job_type, provider_name)
                integration.log_router_action(
                    "route_to_provider",
                    provider_name,
                    "success",
                    f"Routed {job_type} job to {provider_name}"
                )
            except PermissionDeniedError as e:
                integration.log_router_action(
                    "route_to_provider",
                    provider_name,
                    "denied",
                    str(e)
                )
                raise

        return result

    return wrapper


# Decorator for adding permission checks to provider API calls
def require_provider_permission(func):
    """
    Decorator to add permission checks to provider API calls.

    Usage:
        @require_provider_permission
        def call_provider_api(self, provider_name, ...):
            ...
    """
    @wraps(func)
    def wrapper(self, provider_name, *args, **kwargs):
        integration = get_permission_integration()

        # Check provider access
        if not integration.check_provider_access(provider_name):
            integration.log_registry_action(
                "provider_api_call",
                provider_name,
                "denied",
                "Provider access denied"
            )
            raise PermissionDeniedError(f"Access to provider '{provider_name}' denied")

        # Execute the original function
        try:
            result = func(self, provider_name, *args, **kwargs)

            integration.log_registry_action(
                "provider_api_call",
                provider_name,
                "success",
                f"API call to {provider_name} successful"
            )

            return result

        except Exception as e:
            integration.log_registry_action(
                "provider_api_call",
                provider_name,
                "error",
                str(e)
            )
            raise

    return wrapper
