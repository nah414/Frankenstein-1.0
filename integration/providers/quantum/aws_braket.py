#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - AWS Braket Adapter
Phase 3, Step 4: Amazon Braket integration

Multi-provider access: IonQ, Rigetti, D-Wave, OQC via single SDK.
Requires: pip install amazon-braket-sdk
Requires: AWS account + credentials configured (aws configure)
Free tier: 1 hour simulator/month
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


class AWSBraketAdapter(ProviderAdapter):
    """
    AWS Braket adapter.
    Lazy-loaded — braket SDK only imported on connect().
    Provides access to multiple quantum hardware providers.
    """
    
    def __init__(self, credentials: Optional[Dict] = None):
        super().__init__("aws_braket", ProviderCategory.QUANTUM_CLOUD, credentials)
        self._session = None
        self._backend_cache = []

    
    def connect(self) -> bool:
        """Connect to AWS Braket."""
        self.status = ProviderStatus.CONNECTING
        
        try:
            from braket.aws import AwsDevice, AwsSession
            
            # Use AWS credentials from environment or ~/.aws/credentials
            self._session = AwsSession()
            self.status = ProviderStatus.AUTHENTICATED
            return True
            
        except ImportError:
            self.status = ProviderStatus.SDK_MISSING
            self.error_message = "amazon-braket-sdk not installed. Run: pip install amazon-braket-sdk"
            return False
        except Exception as e:
            self.status = ProviderStatus.ERROR
            self.error_message = f"AWS connection failed: {e}. Check AWS credentials (aws configure)"
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from AWS Braket."""
        self._session = None
        self.status = ProviderStatus.UNINITIALIZED
        return True

    
    def get_backends(self) -> List[BackendInfo]:
        """List available Braket devices."""
        if not self.is_connected:
            return []
        
        try:
            from braket.aws import AwsDevice
            
            devices = AwsDevice.get_devices()
            backend_list = []
            
            for device in devices:
                if not device.is_available:
                    continue
                
                # Determine technology type
                tech = QuantumTechnology.SIMULATION
                if "ionq" in device.name.lower():
                    tech = QuantumTechnology.TRAPPED_ION
                elif "rigetti" in device.name.lower() or "aspen" in device.name.lower():
                    tech = QuantumTechnology.SUPERCONDUCTING
                elif "dwave" in device.name.lower():
                    tech = QuantumTechnology.ANNEALING
                
                backend_list.append(BackendInfo(
                    name=device.name,
                    provider_id=self.provider_id,
                    backend_type="qpu" if "qpu" in device.arn.lower() else "simulator",
                    num_qubits=getattr(device.properties, 'qubitCount', 0),
                    quantum_technology=tech,
                    is_available=device.is_available
                ))
            
            self._backend_cache = backend_list
            return backend_list
            
        except Exception as e:
            self.error_message = str(e)
            return []

    
    def submit_job(self, payload: Any, backend_name: str, **kwargs) -> Optional[str]:
        """
        Submit circuit to AWS Braket.
        
        Args:
            payload: Braket Circuit object
            backend_name: Device ARN or name
            **kwargs: shots, etc.
        
        Returns:
            Job ID (task ARN)
        """
        if not self.is_connected:
            return None
        
        try:
            from braket.aws import AwsDevice
            
            # Get device (by name or ARN)
            device = AwsDevice(backend_name)
            
            # Submit task
            shots = kwargs.get("shots", 1024)
            task = device.run(payload, shots=shots)
            
            return task.id
            
        except Exception as e:
            self.error_message = str(e)
            return None

    
    def get_job_status(self, job_id: str) -> JobStatus:
        """Get Braket task status."""
        if not self.is_connected:
            return JobStatus.FAILED
        
        try:
            from braket.aws import AwsQuantumTask
            
            task = AwsQuantumTask(arn=job_id)
            state = task.state()
            
            status_map = {
                "CREATED": JobStatus.QUEUED,
                "QUEUED": JobStatus.QUEUED,
                "RUNNING": JobStatus.RUNNING,
                "COMPLETED": JobStatus.COMPLETED,
                "FAILED": JobStatus.FAILED,
                "CANCELLED": JobStatus.CANCELLED,
            }
            return status_map.get(state, JobStatus.FAILED)
            
        except Exception:
            return JobStatus.FAILED
    
    def get_job_result(self, job_id: str) -> Optional[JobResult]:
        """Retrieve Braket task result."""
        if not self.is_connected:
            return None
        
        try:
            from braket.aws import AwsQuantumTask
            
            task = AwsQuantumTask(arn=job_id)
            result = task.result()
            
            return JobResult(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                provider_id=self.provider_id,
                backend_name=task.metadata().get("deviceArn", ""),
                output=result.measurements,
                metadata={
                    "device": task.metadata().get("deviceArn", ""),
                    "shots": task.metadata().get("shots", 0),
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
