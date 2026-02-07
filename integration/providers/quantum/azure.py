#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Azure Quantum Adapter
Phase 3, Step 4: Microsoft Azure Quantum integration

Multi-provider access via Azure: IonQ, Quantinuum, Rigetti
Requires: pip install azure-quantum
Requires: Azure account + workspace configured
Free credits available for new accounts.
"""

from typing import Dict, List, Optional, Any
from integration.providers.base import (
    ProviderAdapter, ProviderCategory, ProviderStatus,
    JobStatus, JobResult, BackendInfo, QuantumTechnology
)


class AzureQuantumAdapter(ProviderAdapter):
    """Azure Quantum adapter - lazy-loaded SDK."""

    def __init__(self, credentials: Optional[Dict] = None):
        super().__init__("azure_quantum", ProviderCategory.QUANTUM_CLOUD, credentials)
        self._workspace = None

    def connect(self) -> bool:
        """Connect to Azure Quantum."""
        self.status = ProviderStatus.CONNECTING
        try:
            from azure.quantum import Workspace
        except ImportError:
            self.status = ProviderStatus.SDK_MISSING
            self.error_message = "azure-quantum not installed. Run: pip install azure-quantum"
            return False

        sub_id = self._credentials.get("subscription_id")
        rg = self._credentials.get("resource_group")
        ws = self._credentials.get("workspace_name")

        if not sub_id or not rg or not ws:
            self.status = ProviderStatus.ERROR
            self.error_message = (
                "Missing Azure credentials. Required: subscription_id, resource_group, workspace_name. "
                "Get at portal.azure.com → Quantum Workspace. "
                "Then run: credentials save azure_quantum --credentials "
                "'{\"subscription_id\":\"...\",\"resource_group\":\"...\",\"workspace_name\":\"...\"}'"
            )
            return False

        try:
            self._workspace = Workspace(
                subscription_id=sub_id,
                resource_group=rg,
                name=ws
            )
            self.status = ProviderStatus.AUTHENTICATED
            return True
        except Exception as e:
            self.status = ProviderStatus.ERROR
            self.error_message = str(e)
            return False

    def disconnect(self) -> bool:
        self._workspace = None
        self.status = ProviderStatus.UNINITIALIZED
        return True

    def get_backends(self) -> List[BackendInfo]:
        if not self.is_connected:
            return []
        try:
            targets = self._workspace.get_targets()
            return [BackendInfo(
                name=t.name,
                provider_id=self.provider_id,
                backend_type="qpu",
                is_available=t.current_availability == "Available"
            ) for t in targets]
        except Exception:
            return []

    def submit_job(self, payload: Any, backend_name: str, **kwargs) -> Optional[str]:
        if not self.is_connected:
            return None
        try:
            target = self._workspace.get_targets(backend_name)
            job = target.submit(payload, **kwargs)
            return job.id
        except Exception as e:
            self.error_message = str(e)
            return None

    def get_job_status(self, job_id: str) -> JobStatus:
        if not self.is_connected:
            return JobStatus.FAILED
        try:
            job = self._workspace.get_job(job_id)
            status_map = {
                "Waiting": JobStatus.QUEUED,
                "Executing": JobStatus.RUNNING,
                "Succeeded": JobStatus.COMPLETED,
                "Failed": JobStatus.FAILED,
                "Cancelled": JobStatus.CANCELLED
            }
            return status_map.get(job.details.status, JobStatus.FAILED)
        except Exception:
            return JobStatus.FAILED

    def get_job_result(self, job_id: str) -> Optional[JobResult]:
        if not self.is_connected:
            return None
        try:
            job = self._workspace.get_job(job_id)
            return JobResult(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                provider_id=self.provider_id,
                backend_name=job.details.target,
                output=job.get_results()
            )
        except Exception as e:
            return JobResult(job_id=job_id, status=JobStatus.FAILED,
                           provider_id=self.provider_id, backend_name="",
                           error_message=str(e))
