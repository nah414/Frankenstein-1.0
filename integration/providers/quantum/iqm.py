#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - IQM Adapter
Superconducting quantum computing platform.
Requires: pip install iqm-client
"""

from typing import Dict, List, Optional, Any
from integration.providers.base import (
    ProviderAdapter, ProviderCategory, ProviderStatus, JobStatus, JobResult, BackendInfo, QuantumTechnology
)


class IqmAdapter(ProviderAdapter):
    def __init__(self, credentials: Optional[Dict] = None):
        super().__init__("iqm", ProviderCategory.QUANTUM_HARDWARE, credentials)
        self._client = None

    def connect(self) -> bool:
        self.status = ProviderStatus.CONNECTING
        try:
            import iqm
        except ImportError:
            self.status = ProviderStatus.SDK_MISSING
            self.error_message = "iqm-client not installed. Run: pip install iqm-client"
            return False

        token = self._credentials.get("token")
        if not token:
            self.status = ProviderStatus.ERROR
            self.error_message = (
                "Missing 'token'. Get your IQM API key at https://www.meetiqm.com → Account → API key. "
                "Then run: credentials save iqm --token YOUR_TOKEN"
            )
            return False

        try:
            self._client = True  # Placeholder
            self.status = ProviderStatus.AUTHENTICATED
            return True
        except Exception as e:
            self.status = ProviderStatus.ERROR
            self.error_message = str(e)
            return False

    def disconnect(self) -> bool:
        self._client = None
        self.status = ProviderStatus.UNINITIALIZED
        return True

    def get_backends(self) -> List[BackendInfo]:
        if not self.is_connected:
            return []
        return [BackendInfo(
            name="iqm_backend",
            provider_id=self.provider_id,
            backend_type="qpu",
            num_qubits=20,
            quantum_technology=QuantumTechnology.SUPERCONDUCTING,
            is_available=True
        )]

    def submit_job(self, payload: Any, backend_name: str, **kwargs) -> Optional[str]:
        if not self.is_connected:
            return None
        return "iqm_job_id_placeholder"

    def get_job_status(self, job_id: str) -> JobStatus:
        return JobStatus.QUEUED

    def get_job_result(self, job_id: str) -> Optional[JobResult]:
        return JobResult(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            provider_id=self.provider_id,
            backend_name="iqm_backend"
        )
