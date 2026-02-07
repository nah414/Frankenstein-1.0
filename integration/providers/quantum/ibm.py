#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - IBM Quantum Adapter
Phase 3, Step 4: IBM Quantum cloud integration

Connects to IBM Quantum via Qiskit Runtime.
Requires: pip install qiskit qiskit-ibm-runtime
Free tier: 10 min/month on real quantum hardware.
"""

from typing import Dict, List, Optional, Any
from integration.providers.base import (
    ProviderAdapter,
    ProviderCategory,
    ProviderStatus,
    JobStatus,
    JobResult,
    BackendInfo,
    QuantumTechnology
)


class IBMQuantumAdapter(ProviderAdapter):
    """
    IBM Quantum adapter.
    Lazy-loaded — qiskit only imported on connect().
    """

    def __init__(self, credentials: Optional[Dict] = None):
        super().__init__("ibm_quantum", ProviderCategory.QUANTUM_CLOUD, credentials)
        self._service = None
        self._backend_cache = []

    def connect(self) -> bool:
        """Connect to IBM Quantum cloud."""
        self.status = ProviderStatus.CONNECTING

        try:
            from qiskit_ibm_runtime import QiskitRuntimeService
        except ImportError:
            self.status = ProviderStatus.SDK_MISSING
            self.error_message = "qiskit-ibm-runtime not installed. Run: pip install qiskit-ibm-runtime"
            return False

        token = self._credentials.get("token")

        try:
            if token:
                self._service = QiskitRuntimeService(
                    channel="ibm_quantum",
                    token=token
                )
            else:
                # Try saved account (via QiskitRuntimeService.save_account)
                try:
                    self._service = QiskitRuntimeService(channel="ibm_quantum")
                except Exception:
                    self.status = ProviderStatus.ERROR
                    self.error_message = (
                        "Missing 'token'. Get your IBM Quantum API token at "
                        "https://quantum.ibm.com → Account → API token. "
                        "Then run: credentials save ibm_quantum --token YOUR_TOKEN"
                    )
                    return False

            self.status = ProviderStatus.AUTHENTICATED
            return True

        except Exception as e:
            self.status = ProviderStatus.ERROR
            self.error_message = str(e)
            return False

    def disconnect(self) -> bool:
        """Disconnect from IBM Quantum."""
        self._service = None
        self.status = ProviderStatus.UNINITIALIZED
        return True

    def get_backends(self) -> List[BackendInfo]:
        """List available IBM Quantum backends."""
        if not self.is_connected or not self._service:
            return []

        try:
            backends = self._service.backends()
            backend_list = []

            for backend in backends:
                config = backend.configuration()
                backend_list.append(BackendInfo(
                    name=backend.name,
                    provider_id=self.provider_id,
                    backend_type="qpu" if not config.simulator else "simulator",
                    num_qubits=config.n_qubits,
                    quantum_technology=QuantumTechnology.SUPERCONDUCTING,
                    basis_gates=config.basis_gates if hasattr(config, 'basis_gates') else [],
                    is_available=backend.status().operational
                ))

            self._backend_cache = backend_list
            return backend_list

        except Exception as e:
            self.error_message = str(e)
            return []

    def submit_job(self, payload: Any, backend_name: str, **kwargs) -> Optional[str]:
        """
        Submit circuit to IBM Quantum.

        Args:
            payload: Qiskit QuantumCircuit object
            backend_name: Backend name (e.g., "ibm_kyoto", "ibmq_qasm_simulator")
            **kwargs: shots, optimization_level, etc.

        Returns:
            Job ID from IBM Quantum
        """
        if not self.is_connected:
            return None

        try:
            from qiskit_ibm_runtime import Sampler, Options

            backend_obj = self._service.backend(backend_name)

            # Configure options
            options = Options()
            if 'shots' in kwargs:
                options.execution.shots = kwargs['shots']

            # Use Sampler primitive
            sampler = Sampler(backend=backend_obj, options=options)
            job = sampler.run(payload)

            return job.job_id()

        except Exception as e:
            self.error_message = str(e)
            return None

    def get_job_status(self, job_id: str) -> JobStatus:
        """Get IBM Quantum job status."""
        if not self.is_connected:
            return JobStatus.FAILED

        try:
            job = self._service.job(job_id)
            status_str = job.status().name

            status_map = {
                "QUEUED": JobStatus.QUEUED,
                "VALIDATING": JobStatus.VALIDATING,
                "RUNNING": JobStatus.RUNNING,
                "DONE": JobStatus.COMPLETED,
                "ERROR": JobStatus.FAILED,
                "CANCELLED": JobStatus.CANCELLED,
            }
            return status_map.get(status_str, JobStatus.FAILED)
        except Exception:
            return JobStatus.FAILED

    def get_job_result(self, job_id: str) -> Optional[JobResult]:
        """Retrieve IBM Quantum job result."""
        if not self.is_connected:
            return None

        try:
            job = self._service.job(job_id)
            result = job.result()

            return JobResult(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                provider_id=self.provider_id,
                backend_name=job.backend().name,
                output=result,
                metadata={
                    "backend": job.backend().name,
                    "creation_date": str(job.creation_date()) if hasattr(job, 'creation_date') else ""
                }
            )
        except Exception as e:
            return JobResult(
                job_id=job_id,
                status=JobStatus.FAILED,
                provider_id=self.provider_id,
                backend_name="",
                error_message=str(e)
            )
