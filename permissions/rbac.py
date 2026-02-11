"""
Role-Based Access Control (RBAC) System for Frankenstein 1.0

Defines roles, permissions, and provider access for all 28 quantum and classical providers.
Supports lazy loading - only imported when permission checks are requested.

Author: Frankenstein 1.0 Team
Phase: 3, Step 6
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set
from enum import Enum


class Role(Enum):
    """User roles with hierarchical permission levels."""
    ADMIN = "Admin"
    USER = "User"
    AGENT = "Agent"
    READONLY = "ReadOnly"


class ProviderCategory(Enum):
    """Provider categories for granular access control."""
    QUANTUM = "quantum"
    CLASSICAL_GPU_QUANTUM = "classical_gpu_quantum"
    CLASSICAL_COMPUTE = "classical_compute"


# Provider categorization - ALL 28 PROVIDERS
PROVIDER_CATEGORIES = {
    "quantum": [
        "IBM Quantum",
        "AWS Braket",
        "Azure Quantum",
        "Google Quantum AI",
        "IonQ",
        "Rigetti Computing",
        "Xanadu (PennyLane)",
        "D-Wave",
        "Quantinuum",
        "IQM",
        "QuEra Computing",
        "Oxford Quantum Circuits",
        "Atom Computing",
        "Pasqal",
        "AQT (Alpine Quantum Technologies)"
    ],
    "classical_gpu_quantum": [
        "NVIDIA Quantum Cloud",
        "cuQuantum"
    ],
    "classical_compute": [
        "ARM Compute",
        "RISC-V Compute",
        "NVIDIA CUDA",
        "AMD ROCm",
        "Apple Metal",
        "Intel oneAPI",
        "Google TPU",
        "FPGA Compute",
        "Neural Processing Unit",
        "Intel",
        "AMD"
    ]
}

# Flatten for easy iteration - ALL 28 PROVIDERS
ALL_PROVIDERS = [
    # Quantum (15)
    "IBM Quantum", "AWS Braket", "Azure Quantum", "Google Quantum AI",
    "IonQ", "Rigetti Computing", "Xanadu (PennyLane)", "D-Wave",
    "Quantinuum", "IQM", "QuEra Computing", "Oxford Quantum Circuits",
    "Atom Computing", "Pasqal", "AQT (Alpine Quantum Technologies)",

    # Classical GPU/Quantum Hybrid (2)
    "NVIDIA Quantum Cloud", "cuQuantum",

    # Classical Compute (11)
    "ARM Compute", "RISC-V Compute", "NVIDIA CUDA", "AMD ROCm",
    "Apple Metal", "Intel oneAPI", "Google TPU", "FPGA Compute",
    "Neural Processing Unit", "Intel", "AMD"
]


@dataclass
class RolePermissions:
    """Permission set for a specific role."""
    role: Role
    permissions: Dict[str, bool] = field(default_factory=dict)
    provider_access: List[str] = field(default_factory=list)
    resource_limits: Dict[str, int] = field(default_factory=dict)


# Permission definitions for each role
ROLE_PERMISSIONS = {
    Role.ADMIN: RolePermissions(
        role=Role.ADMIN,
        permissions={
            "quantum_job_submit": True,
            "classical_compute_submit": True,
            "provider_access_all": True,
            "provider_access_quantum": True,
            "provider_access_classical": True,
            "credential_view": True,
            "credential_modify": True,
            "system_config_modify": True,
            "automation_enable": True,
            "agent_deploy": True,
            "audit_view": True,
            "hardware_optimization": True,
        },
        provider_access=ALL_PROVIDERS,  # Full access to all 28 providers
        resource_limits={
            "max_qubits": 1000,
            "max_compute_cores": 16,
            "max_gpu_memory_gb": 32,
            "max_cost_per_job_usd": 10000,
            "max_concurrent_jobs": 50,
        }
    ),

    Role.USER: RolePermissions(
        role=Role.USER,
        permissions={
            "quantum_job_submit": True,
            "classical_compute_submit": True,
            "provider_access_all": True,
            "provider_access_quantum": True,
            "provider_access_classical": True,
            "credential_view": True,
            "credential_modify": True,
            "system_config_modify": False,  # Cannot change system settings
            "automation_enable": True,
            "agent_deploy": False,  # Cannot deploy new agents
            "audit_view": True,
            "hardware_optimization": True,
        },
        provider_access=ALL_PROVIDERS,  # Full access to all 28 providers
        resource_limits={
            "max_qubits": 100,
            "max_compute_cores": 8,
            "max_gpu_memory_gb": 16,
            "max_cost_per_job_usd": 1000,
            "max_concurrent_jobs": 20,
        }
    ),

    Role.AGENT: RolePermissions(
        role=Role.AGENT,
        permissions={
            "quantum_job_submit": True,
            "classical_compute_submit": True,
            "provider_access_all": True,
            "provider_access_quantum": True,
            "provider_access_classical": True,
            "credential_view": False,  # Agents cannot view raw credentials
            "credential_modify": False,
            "system_config_modify": False,
            "automation_enable": False,
            "agent_deploy": False,
            "audit_view": False,  # Cannot view audit logs
            "hardware_optimization": True,
        },
        provider_access=ALL_PROVIDERS,  # Full access to all 28 providers for job execution
        resource_limits={
            "max_qubits": 50,
            "max_compute_cores": 4,
            "max_gpu_memory_gb": 8,
            "max_cost_per_job_usd": 100,
            "max_concurrent_jobs": 10,
        }
    ),

    Role.READONLY: RolePermissions(
        role=Role.READONLY,
        permissions={
            "quantum_job_submit": False,
            "classical_compute_submit": False,
            "provider_access_all": False,
            "provider_access_quantum": False,
            "provider_access_classical": False,
            "credential_view": False,
            "credential_modify": False,
            "system_config_modify": False,
            "automation_enable": False,
            "agent_deploy": False,
            "audit_view": True,  # Can only view audit logs
            "hardware_optimization": False,
        },
        provider_access=[],  # No provider access for read-only users
        resource_limits={
            "max_qubits": 0,
            "max_compute_cores": 0,
            "max_gpu_memory_gb": 0,
            "max_cost_per_job_usd": 0,
            "max_concurrent_jobs": 0,
        }
    ),
}


def get_permissions(role: str) -> Dict[str, bool]:
    """
    Get permission dictionary for a specific role.

    Args:
        role: Role name as string (Admin, User, Agent, ReadOnly)

    Returns:
        Dictionary mapping permission names to boolean values

    Raises:
        ValueError: If role is not recognized
    """
    try:
        role_enum = Role(role)
    except ValueError:
        raise ValueError(f"Invalid role: {role}. Must be one of {[r.value for r in Role]}")

    return ROLE_PERMISSIONS[role_enum].permissions.copy()


def get_provider_access(role: str) -> List[str]:
    """
    Get list of accessible providers for a specific role.

    Args:
        role: Role name as string (Admin, User, Agent, ReadOnly)

    Returns:
        List of provider names the role can access (from 28 total)

    Raises:
        ValueError: If role is not recognized
    """
    try:
        role_enum = Role(role)
    except ValueError:
        raise ValueError(f"Invalid role: {role}. Must be one of {[r.value for r in Role]}")

    return ROLE_PERMISSIONS[role_enum].provider_access.copy()


def get_resource_limits(role: str) -> Dict[str, int]:
    """
    Get resource limits for a specific role.

    Args:
        role: Role name as string (Admin, User, Agent, ReadOnly)

    Returns:
        Dictionary of resource limit names to maximum values

    Raises:
        ValueError: If role is not recognized
    """
    try:
        role_enum = Role(role)
    except ValueError:
        raise ValueError(f"Invalid role: {role}. Must be one of {[r.value for r in Role]}")

    return ROLE_PERMISSIONS[role_enum].resource_limits.copy()


def get_providers_by_category(category: str) -> List[str]:
    """
    Get all providers in a specific category.

    Args:
        category: Provider category (quantum, classical_gpu_quantum, classical_compute)

    Returns:
        List of provider names in the category

    Raises:
        ValueError: If category is not recognized
    """
    if category not in PROVIDER_CATEGORIES:
        raise ValueError(
            f"Invalid category: {category}. Must be one of {list(PROVIDER_CATEGORIES.keys())}"
        )

    return PROVIDER_CATEGORIES[category].copy()


def get_provider_category(provider_name: str) -> str:
    """
    Get the category for a specific provider.

    Args:
        provider_name: Name of the provider

    Returns:
        Category name (quantum, classical_gpu_quantum, classical_compute)

    Raises:
        ValueError: If provider is not recognized
    """
    for category, providers in PROVIDER_CATEGORIES.items():
        if provider_name in providers:
            return category

    raise ValueError(
        f"Unknown provider: {provider_name}. Must be one of {ALL_PROVIDERS}"
    )


def validate_provider(provider_name: str) -> bool:
    """
    Check if a provider name is valid (one of the 28 supported providers).

    Args:
        provider_name: Name of the provider to validate

    Returns:
        True if provider is valid, False otherwise
    """
    return provider_name in ALL_PROVIDERS


def get_quantum_providers() -> List[str]:
    """Get list of all quantum providers (15 total)."""
    return PROVIDER_CATEGORIES["quantum"].copy()


def get_classical_providers() -> List[str]:
    """Get list of all classical compute providers (13 total, including GPU/Quantum hybrid)."""
    return (
        PROVIDER_CATEGORIES["classical_gpu_quantum"] +
        PROVIDER_CATEGORIES["classical_compute"]
    )


# Lazy loading verification
_MODULE_LOADED = False

def _mark_loaded():
    """Mark module as loaded for lazy loading tracking."""
    global _MODULE_LOADED
    _MODULE_LOADED = True

# Mark loaded on import
_mark_loaded()
