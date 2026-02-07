#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Local CPU Adapter
Phase 3, Step 4: NumPy/SciPy classical compute

Always available. No credentials needed.
Handles matrix operations, simulations, synthesis engine compute.
"""

from typing import Dict, List, Optional, Any
from integration.providers.base import (
    ProviderAdapter,
    ProviderCategory,
    ProviderStatus,
    JobStatus,
    JobResult,
    BackendInfo,
    ClassicalArchitecture
)
import uuid
import time


class LocalCPUAdapter(ProviderAdapter):
    """
    Local CPU compute adapter.
    NumPy/SciPy backend for classical operations.
    """

    def __init__(self, credentials: Optional[Dict] = None):
        super().__init__("local_cpu", ProviderCategory.CLASSICAL_CPU, credentials)
        self._jobs = {}

    def connect(self) -> bool:
        """Connect to local CPU (instant). No credentials needed."""
        try:
            import numpy as np
        except ImportError:
            self.status = ProviderStatus.SDK_MISSING
            self.error_message = "numpy not installed. Run: pip install numpy"
            return False

        try:
            import psutil
            cpu_count = psutil.cpu_count(logical=True)
            mem_gb = psutil.virtual_memory().total / (1024**3)
        except ImportError:
            import os
            cpu_count = os.cpu_count() or 1
            mem_gb = 0.0

        self.status = ProviderStatus.AUTHENTICATED

        # Detect architecture
        import platform
        machine = platform.machine().lower()
        if "arm" in machine or "aarch" in machine:
            arch = ClassicalArchitecture.ARM
        elif "amd" in platform.processor().lower():
            arch = ClassicalArchitecture.X86_AMD
        else:
            arch = ClassicalArchitecture.X86_INTEL

        self._backends = [
            BackendInfo(
                name="numpy_cpu",
                provider_id=self.provider_id,
                backend_type="cpu",
                compute_units=cpu_count,
                memory_gb=mem_gb,
                architecture=arch,
                is_available=True
            )
        ]
        return True

    def disconnect(self) -> bool:
        """Disconnect from local CPU."""
        self.status = ProviderStatus.UNINITIALIZED
        self._jobs.clear()
        return True

    def get_backends(self) -> List[BackendInfo]:
        """List available CPU backends."""
        return self._backends if self.is_connected else []

    def submit_job(self, payload: Any, backend_name: str = "numpy_cpu", **kwargs) -> Optional[str]:
        """Submit CPU computation job."""
        if not self.is_connected:
            return None

        job_id = str(uuid.uuid4())

        try:
            result = self._execute_cpu_operation(payload, backend_name)
            self._jobs[job_id] = JobResult(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                provider_id=self.provider_id,
                backend_name=backend_name,
                output=result,
                started_at=time.time(),
                completed_at=time.time()
            )
        except Exception as e:
            self._jobs[job_id] = JobResult(
                job_id=job_id,
                status=JobStatus.FAILED,
                provider_id=self.provider_id,
                backend_name=backend_name,
                error_message=str(e)
            )

        return job_id

    def get_job_status(self, job_id: str) -> JobStatus:
        """Get job status."""
        if job_id not in self._jobs:
            return JobStatus.FAILED
        return self._jobs[job_id].status

    def get_job_result(self, job_id: str) -> Optional[JobResult]:
        """Retrieve job result."""
        return self._jobs.get(job_id)

    def _execute_cpu_operation(self, payload: Dict, backend: str) -> Any:
        """
        Execute CPU operation.

        Payload format:
            {
                "operation": "matmul" | "fft" | "solve" | "eigen",
                "data": array or arrays,
                "params": optional parameters
            }
        """
        import numpy as np

        operation = payload.get("operation", "identity")
        data = payload.get("data")

        if operation == "matmul":
            return np.matmul(data[0], data[1]).tolist()
        elif operation == "fft":
            return np.fft.fft(data).tolist()
        elif operation == "solve":
            return np.linalg.solve(data[0], data[1]).tolist()
        elif operation == "eigen":
            eigenvalues, eigenvectors = np.linalg.eig(data)
            return {"eigenvalues": eigenvalues.tolist(), "eigenvectors": eigenvectors.tolist()}
        else:
            return data
