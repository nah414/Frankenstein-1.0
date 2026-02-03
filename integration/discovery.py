#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Hardware Discovery Engine
Phase 3, Step 1: Universal Hardware Detection

Detects and fingerprints all available hardware:
- CPU: cores, threads, frequency, architecture, vendor
- GPU: model, VRAM, compute capability (NVIDIA/AMD/Intel)
- RAM: total, available, speed, type
- Storage: drives, capacity, type (SSD/HDD), speeds
- Network: interfaces, bandwidth estimation

Safety: Read-only operations only - no system modifications
"""

import os
import sys
import platform
import socket
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

# Core dependency - always available
import psutil


# ============================================================================
# HARDWARE TIER CLASSIFICATION
# ============================================================================

class HardwareTier(Enum):
    """Hardware capability tiers for workload routing"""
    TIER_1_BASELINE = "tier1"      # Basic laptop (like Adam's Dell i3)
    TIER_2_WORKSTATION = "tier2"   # Mid-range workstation
    TIER_3_PERFORMANCE = "tier3"   # High-performance desktop
    TIER_4_ENTERPRISE = "tier4"    # Enterprise/server grade
    TIER_5_HPC = "tier5"           # HPC/Quantum-ready


class GPUVendor(Enum):
    """GPU vendor classification"""
    NVIDIA = "nvidia"
    AMD = "amd"
    INTEL = "intel"
    APPLE = "apple"
    NONE = "none"


class StorageType(Enum):
    """Storage device classification"""
    SSD = "ssd"
    HDD = "hdd"
    NVME = "nvme"
    UNKNOWN = "unknown"


# ============================================================================
# DATA CLASSES FOR HARDWARE INFO
# ============================================================================

@dataclass
class CPUInfo:
    """CPU hardware information"""
    vendor: str = "Unknown"
    model: str = "Unknown"
    architecture: str = "Unknown"
    physical_cores: int = 0
    logical_cores: int = 0
    max_frequency_mhz: float = 0.0
    current_frequency_mhz: float = 0.0
    min_frequency_mhz: float = 0.0
    cache_size_kb: int = 0
    features: List[str] = field(default_factory=list)
    
    @property
    def hyperthreading(self) -> bool:
        return self.logical_cores > self.physical_cores


@dataclass
class GPUInfo:
    """GPU hardware information"""
    vendor: GPUVendor = GPUVendor.NONE
    model: str = "None"
    vram_mb: int = 0
    vram_available_mb: int = 0
    compute_capability: str = ""
    cuda_cores: int = 0
    driver_version: str = ""
    temperature_c: float = 0.0
    utilization_percent: float = 0.0
    available: bool = False


@dataclass
class RAMInfo:
    """System memory information"""
    total_gb: float = 0.0
    available_gb: float = 0.0
    used_gb: float = 0.0
    percent_used: float = 0.0
    swap_total_gb: float = 0.0
    swap_used_gb: float = 0.0


@dataclass
class StorageInfo:
    """Storage device information"""
    device: str = ""
    mount_point: str = ""
    filesystem: str = ""
    total_gb: float = 0.0
    used_gb: float = 0.0
    free_gb: float = 0.0
    percent_used: float = 0.0
    storage_type: StorageType = StorageType.UNKNOWN


@dataclass
class NetworkInfo:
    """Network interface information"""
    hostname: str = ""
    interfaces: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    has_internet: bool = False



@dataclass
class HardwareFingerprint:
    """Complete hardware fingerprint for the system"""
    # Identification
    fingerprint_id: str = ""
    timestamp: str = ""
    
    # System info
    os_name: str = ""
    os_version: str = ""
    os_release: str = ""
    machine_type: str = ""
    hostname: str = ""
    
    # Hardware components
    cpu: CPUInfo = field(default_factory=CPUInfo)
    gpu: GPUInfo = field(default_factory=GPUInfo)
    ram: RAMInfo = field(default_factory=RAMInfo)
    storage: List[StorageInfo] = field(default_factory=list)
    network: NetworkInfo = field(default_factory=NetworkInfo)
    
    # Classification
    tier: HardwareTier = HardwareTier.TIER_1_BASELINE
    
    # Safety limits (based on tier)
    max_cpu_percent: int = 80
    max_memory_percent: int = 70
    max_gpu_percent: int = 85
    max_temperature_c: int = 85
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result['tier'] = self.tier.value
        result['cpu']['features'] = self.cpu.features
        result['gpu']['vendor'] = self.gpu.vendor.value
        for i, storage in enumerate(result['storage']):
            result['storage'][i]['storage_type'] = self.storage[i].storage_type.value
        return result
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent)



# ============================================================================
# HARDWARE DISCOVERY ENGINE
# ============================================================================

class HardwareDiscovery:
    """
    Universal Hardware Discovery Engine
    
    Detects and catalogs all available hardware for workload optimization.
    All operations are READ-ONLY - no system modifications.
    
    Safety:
    - Never modifies system state
    - Respects resource limits
    - Graceful fallback on detection failure
    """
    
    def __init__(self):
        self._fingerprint: Optional[HardwareFingerprint] = None
        self._last_scan: Optional[datetime] = None
        self._cache_timeout_seconds = 60  # Refresh every 60 seconds
    
    def discover(self, force_refresh: bool = False) -> HardwareFingerprint:
        """
        Perform complete hardware discovery scan.
        
        Args:
            force_refresh: Bypass cache and force fresh scan
            
        Returns:
            HardwareFingerprint with all detected hardware
        """
        # Check cache
        if not force_refresh and self._fingerprint and self._last_scan:
            elapsed = (datetime.now() - self._last_scan).total_seconds()
            if elapsed < self._cache_timeout_seconds:
                return self._fingerprint
        
        # Perform fresh scan
        fingerprint = HardwareFingerprint()
        fingerprint.timestamp = datetime.now().isoformat()
        
        # System information
        self._detect_system_info(fingerprint)
        
        # Hardware components
        fingerprint.cpu = self._detect_cpu()
        fingerprint.gpu = self._detect_gpu()
        fingerprint.ram = self._detect_ram()
        fingerprint.storage = self._detect_storage()
        fingerprint.network = self._detect_network()
        
        # Classification
        fingerprint.tier = self._classify_tier(fingerprint)
        self._set_safety_limits(fingerprint)
        
        # Generate fingerprint ID
        fingerprint.fingerprint_id = self._generate_fingerprint_id(fingerprint)
        
        # Cache results
        self._fingerprint = fingerprint
        self._last_scan = datetime.now()
        
        return fingerprint
    
    def _detect_system_info(self, fp: HardwareFingerprint) -> None:
        """Detect basic system information"""
        uname = platform.uname()
        fp.os_name = uname.system
        fp.os_version = uname.version
        fp.os_release = uname.release
        fp.machine_type = uname.machine
        fp.hostname = uname.node


    def _detect_cpu(self) -> CPUInfo:
        """Detect CPU information"""
        cpu = CPUInfo()
        
        try:
            # Basic info from platform
            cpu.architecture = platform.machine()
            cpu.model = platform.processor() or "Unknown"
            
            # Core counts from psutil
            cpu.physical_cores = psutil.cpu_count(logical=False) or 1
            cpu.logical_cores = psutil.cpu_count(logical=True) or 1
            
            # Frequency info
            freq = psutil.cpu_freq()
            if freq:
                cpu.max_frequency_mhz = freq.max or 0.0
                cpu.current_frequency_mhz = freq.current or 0.0
                cpu.min_frequency_mhz = freq.min or 0.0
            
            # Try to get detailed CPU info using py-cpuinfo if available
            try:
                import cpuinfo
                info = cpuinfo.get_cpu_info()
                cpu.vendor = info.get('vendor_id_raw', 'Unknown')
                cpu.model = info.get('brand_raw', cpu.model)
                cpu.features = info.get('flags', [])
                
                # Cache size (convert from string if needed)
                cache = info.get('l3_cache_size', 0)
                if isinstance(cache, str):
                    # Parse strings like "8192 KB"
                    cache = int(''.join(filter(str.isdigit, cache)) or 0)
                cpu.cache_size_kb = cache
                
            except ImportError:
                # py-cpuinfo not available, try WMI on Windows
                if sys.platform == 'win32':
                    cpu = self._detect_cpu_wmi(cpu)
                else:
                    # Try /proc/cpuinfo on Linux
                    cpu = self._detect_cpu_proc(cpu)
                    
        except Exception as e:
            # Graceful fallback - return partial info
            pass
        
        return cpu
    
    def _detect_cpu_wmi(self, cpu: CPUInfo) -> CPUInfo:
        """Detect CPU info using WMI on Windows"""
        try:
            import wmi
            w = wmi.WMI()
            for processor in w.Win32_Processor():
                cpu.vendor = processor.Manufacturer or cpu.vendor
                cpu.model = processor.Name or cpu.model
                cpu.cache_size_kb = processor.L3CacheSize or 0
                break
        except ImportError:
            pass
        except Exception:
            pass
        return cpu
    
    def _detect_cpu_proc(self, cpu: CPUInfo) -> CPUInfo:
        """Detect CPU info from /proc/cpuinfo on Linux"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip().lower()
                        value = value.strip()
                        if key == 'vendor_id':
                            cpu.vendor = value
                        elif key == 'model name':
                            cpu.model = value
                        elif key == 'cache size':
                            cpu.cache_size_kb = int(''.join(filter(str.isdigit, value)) or 0)
        except FileNotFoundError:
            pass
        except Exception:
            pass
        return cpu


    def _detect_gpu(self) -> GPUInfo:
        """Detect GPU information"""
        gpu = GPUInfo()
        
        # Try NVIDIA first (most common for compute)
        gpu = self._detect_nvidia_gpu(gpu)
        if gpu.available:
            return gpu
        
        # Try AMD
        gpu = self._detect_amd_gpu(gpu)
        if gpu.available:
            return gpu
        
        # Try Intel integrated
        gpu = self._detect_intel_gpu(gpu)
        if gpu.available:
            return gpu
        
        # Check for Apple Silicon
        if sys.platform == 'darwin':
            gpu = self._detect_apple_gpu(gpu)
        
        return gpu
    
    def _detect_nvidia_gpu(self, gpu: GPUInfo) -> GPUInfo:
        """Detect NVIDIA GPU using GPUtil or pynvml"""
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                nvidia_gpu = gpus[0]  # Primary GPU
                gpu.vendor = GPUVendor.NVIDIA
                gpu.model = nvidia_gpu.name
                gpu.vram_mb = int(nvidia_gpu.memoryTotal)
                gpu.vram_available_mb = int(nvidia_gpu.memoryFree)
                gpu.temperature_c = nvidia_gpu.temperature
                gpu.utilization_percent = nvidia_gpu.load * 100
                gpu.driver_version = nvidia_gpu.driver
                gpu.available = True
                
                # Try to get CUDA info
                try:
                    import pynvml
                    pynvml.nvmlInit()
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    major, minor = pynvml.nvmlDeviceGetCudaComputeCapability(handle)
                    gpu.compute_capability = f"{major}.{minor}"
                    pynvml.nvmlShutdown()
                except ImportError:
                    pass
                except Exception:
                    pass
                    
        except ImportError:
            # GPUtil not available, try pynvml directly
            try:
                import pynvml
                pynvml.nvmlInit()
                count = pynvml.nvmlDeviceGetCount()
                if count > 0:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    gpu.vendor = GPUVendor.NVIDIA
                    gpu.model = pynvml.nvmlDeviceGetName(handle)
                    if isinstance(gpu.model, bytes):
                        gpu.model = gpu.model.decode('utf-8')
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    gpu.vram_mb = mem_info.total // (1024 * 1024)
                    gpu.vram_available_mb = mem_info.free // (1024 * 1024)
                    gpu.available = True
                pynvml.nvmlShutdown()
            except ImportError:
                pass
            except Exception:
                pass
        except Exception:
            pass
        
        return gpu


    def _detect_amd_gpu(self, gpu: GPUInfo) -> GPUInfo:
        """Detect AMD GPU using ROCm tools"""
        try:
            # Try rocm-smi
            import subprocess
            result = subprocess.run(
                ['rocm-smi', '--showproductname'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout:
                gpu.vendor = GPUVendor.AMD
                gpu.model = result.stdout.strip()
                gpu.available = True
        except FileNotFoundError:
            pass
        except Exception:
            pass
        
        # Fallback: check WMI on Windows
        if not gpu.available and sys.platform == 'win32':
            try:
                import wmi
                w = wmi.WMI()
                for video in w.Win32_VideoController():
                    if 'AMD' in (video.Name or '') or 'Radeon' in (video.Name or ''):
                        gpu.vendor = GPUVendor.AMD
                        gpu.model = video.Name
                        gpu.vram_mb = int(video.AdapterRAM or 0) // (1024 * 1024)
                        gpu.available = True
                        break
            except ImportError:
                pass
            except Exception:
                pass
        
        return gpu
    
    def _detect_intel_gpu(self, gpu: GPUInfo) -> GPUInfo:
        """Detect Intel integrated GPU"""
        if sys.platform == 'win32':
            try:
                import wmi
                w = wmi.WMI()
                for video in w.Win32_VideoController():
                    name = video.Name or ''
                    if 'Intel' in name and ('UHD' in name or 'HD Graphics' in name or 'Iris' in name):
                        gpu.vendor = GPUVendor.INTEL
                        gpu.model = name
                        gpu.vram_mb = int(video.AdapterRAM or 0) // (1024 * 1024)
                        gpu.available = True
                        break
            except ImportError:
                pass
            except Exception:
                pass
        return gpu
    
    def _detect_apple_gpu(self, gpu: GPUInfo) -> GPUInfo:
        """Detect Apple Silicon GPU"""
        try:
            import subprocess
            result = subprocess.run(
                ['system_profiler', 'SPDisplaysDataType'],
                capture_output=True, text=True, timeout=10
            )
            if 'Apple' in result.stdout:
                gpu.vendor = GPUVendor.APPLE
                # Parse model from output
                for line in result.stdout.split('\n'):
                    if 'Chipset Model' in line:
                        gpu.model = line.split(':')[-1].strip()
                        gpu.available = True
                        break
        except Exception:
            pass
        return gpu


    def _detect_ram(self) -> RAMInfo:
        """Detect system memory information"""
        ram = RAMInfo()
        
        try:
            mem = psutil.virtual_memory()
            ram.total_gb = mem.total / (1024 ** 3)
            ram.available_gb = mem.available / (1024 ** 3)
            ram.used_gb = mem.used / (1024 ** 3)
            ram.percent_used = mem.percent
            
            swap = psutil.swap_memory()
            ram.swap_total_gb = swap.total / (1024 ** 3)
            ram.swap_used_gb = swap.used / (1024 ** 3)
            
        except Exception:
            pass
        
        return ram
    
    def _detect_storage(self) -> List[StorageInfo]:
        """Detect storage devices"""
        storage_list = []
        
        try:
            partitions = psutil.disk_partitions()
            for partition in partitions:
                storage = StorageInfo()
                storage.device = partition.device
                storage.mount_point = partition.mountpoint
                storage.filesystem = partition.fstype
                
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    storage.total_gb = usage.total / (1024 ** 3)
                    storage.used_gb = usage.used / (1024 ** 3)
                    storage.free_gb = usage.free / (1024 ** 3)
                    storage.percent_used = usage.percent
                except PermissionError:
                    continue
                
                # Determine storage type
                storage.storage_type = self._detect_storage_type(partition.device)
                
                storage_list.append(storage)
                
        except Exception:
            pass
        
        return storage_list
    
    def _detect_storage_type(self, device: str) -> StorageType:
        """Determine if storage is SSD, NVMe, or HDD"""
        device_lower = device.lower()
        
        # Check for NVMe
        if 'nvme' in device_lower:
            return StorageType.NVME
        
        # On Windows, try WMI
        if sys.platform == 'win32':
            try:
                import wmi
                w = wmi.WMI()
                for disk in w.Win32_DiskDrive():
                    if disk.MediaType:
                        media = disk.MediaType.lower()
                        if 'solid state' in media or 'ssd' in media:
                            return StorageType.SSD
                        elif 'fixed hard disk' in media:
                            return StorageType.HDD
            except ImportError:
                pass
            except Exception:
                pass
        
        # On Linux, check /sys/block
        elif sys.platform == 'linux':
            try:
                # Extract device name (e.g., sda from /dev/sda1)
                dev_name = device.replace('/dev/', '').rstrip('0123456789')
                rotational_path = f'/sys/block/{dev_name}/queue/rotational'
                if os.path.exists(rotational_path):
                    with open(rotational_path, 'r') as f:
                        if f.read().strip() == '0':
                            return StorageType.SSD
                        else:
                            return StorageType.HDD
            except Exception:
                pass
        
        return StorageType.UNKNOWN


    def _detect_network(self) -> NetworkInfo:
        """Detect network interfaces and connectivity"""
        network = NetworkInfo()
        
        try:
            network.hostname = socket.gethostname()
            
            # Get network interfaces
            interfaces = psutil.net_if_addrs()
            for iface_name, addrs in interfaces.items():
                iface_info = {'addresses': []}
                for addr in addrs:
                    addr_info = {
                        'family': str(addr.family),
                        'address': addr.address,
                        'netmask': addr.netmask,
                        'broadcast': addr.broadcast
                    }
                    iface_info['addresses'].append(addr_info)
                network.interfaces[iface_name] = iface_info
            
            # Check internet connectivity
            network.has_internet = self._check_internet()
            
        except Exception:
            pass
        
        return network
    
    def _check_internet(self, timeout: float = 3.0) -> bool:
        """Check if internet is available"""
        try:
            # Try to connect to common DNS servers
            socket.setdefaulttimeout(timeout)
            socket.create_connection(("8.8.8.8", 53))
            return True
        except (socket.timeout, OSError):
            pass
        
        try:
            # Fallback: try Cloudflare DNS
            socket.create_connection(("1.1.1.1", 53))
            return True
        except (socket.timeout, OSError):
            return False
    
    def _classify_tier(self, fp: HardwareFingerprint) -> HardwareTier:
        """Classify hardware into performance tiers"""
        score = 0
        
        # CPU scoring
        if fp.cpu.physical_cores >= 16:
            score += 40
        elif fp.cpu.physical_cores >= 8:
            score += 30
        elif fp.cpu.physical_cores >= 6:
            score += 20
        elif fp.cpu.physical_cores >= 4:
            score += 10
        else:
            score += 5
        
        # RAM scoring
        if fp.ram.total_gb >= 128:
            score += 30
        elif fp.ram.total_gb >= 64:
            score += 25
        elif fp.ram.total_gb >= 32:
            score += 20
        elif fp.ram.total_gb >= 16:
            score += 15
        elif fp.ram.total_gb >= 8:
            score += 10
        else:
            score += 5
        
        # GPU scoring
        if fp.gpu.available:
            if fp.gpu.vram_mb >= 24000:  # 24GB+ (RTX 4090, A100)
                score += 30
            elif fp.gpu.vram_mb >= 12000:  # 12GB+ (RTX 3080)
                score += 25
            elif fp.gpu.vram_mb >= 8000:   # 8GB+ (RTX 3070)
                score += 20
            elif fp.gpu.vram_mb >= 4000:   # 4GB+
                score += 10
            else:
                score += 5
        
        # Classify based on score
        if score >= 90:
            return HardwareTier.TIER_5_HPC
        elif score >= 70:
            return HardwareTier.TIER_4_ENTERPRISE
        elif score >= 50:
            return HardwareTier.TIER_3_PERFORMANCE
        elif score >= 35:
            return HardwareTier.TIER_2_WORKSTATION
        else:
            return HardwareTier.TIER_1_BASELINE


    def _set_safety_limits(self, fp: HardwareFingerprint) -> None:
        """Set safety limits based on hardware tier"""
        # Base limits (conservative for Tier 1)
        fp.max_cpu_percent = 80
        fp.max_memory_percent = 70
        fp.max_gpu_percent = 85
        fp.max_temperature_c = 85
        
        # Adjust based on tier (higher tiers can sustain more load)
        if fp.tier == HardwareTier.TIER_5_HPC:
            fp.max_cpu_percent = 95
            fp.max_memory_percent = 90
            fp.max_gpu_percent = 95
        elif fp.tier == HardwareTier.TIER_4_ENTERPRISE:
            fp.max_cpu_percent = 90
            fp.max_memory_percent = 85
            fp.max_gpu_percent = 90
        elif fp.tier == HardwareTier.TIER_3_PERFORMANCE:
            fp.max_cpu_percent = 85
            fp.max_memory_percent = 80
            fp.max_gpu_percent = 90
        elif fp.tier == HardwareTier.TIER_2_WORKSTATION:
            fp.max_cpu_percent = 85
            fp.max_memory_percent = 75
            fp.max_gpu_percent = 85
        # Tier 1 keeps conservative defaults
    
    def _generate_fingerprint_id(self, fp: HardwareFingerprint) -> str:
        """Generate unique fingerprint ID based on hardware"""
        import hashlib
        
        # Create unique string from hardware characteristics
        unique_str = f"{fp.hostname}:{fp.cpu.model}:{fp.cpu.physical_cores}:"
        unique_str += f"{fp.ram.total_gb:.1f}:{fp.gpu.model}:{fp.os_name}"
        
        # Generate short hash
        hash_obj = hashlib.sha256(unique_str.encode())
        return hash_obj.hexdigest()[:16]
    
    def get_current_usage(self) -> Dict[str, float]:
        """Get current resource usage (real-time)"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent if sys.platform != 'win32' 
                           else psutil.disk_usage('C:').percent,
        }
    
    def is_within_safety_limits(self) -> Tuple[bool, List[str]]:
        """Check if current usage is within safety limits"""
        if not self._fingerprint:
            self.discover()
        
        fp = self._fingerprint
        usage = self.get_current_usage()
        violations = []
        
        if usage['cpu_percent'] > fp.max_cpu_percent:
            violations.append(f"CPU at {usage['cpu_percent']:.1f}% (max: {fp.max_cpu_percent}%)")
        
        if usage['memory_percent'] > fp.max_memory_percent:
            violations.append(f"Memory at {usage['memory_percent']:.1f}% (max: {fp.max_memory_percent}%)")
        
        return len(violations) == 0, violations
    
    def format_summary(self) -> str:
        """Format a human-readable summary of discovered hardware"""
        if not self._fingerprint:
            self.discover()
        
        fp = self._fingerprint
        lines = [
            "═" * 50,
            "🔬 HARDWARE DISCOVERY REPORT",
            "═" * 50,
            "",
            f"📋 System: {fp.os_name} {fp.os_release}",
            f"🖥️  Host: {fp.hostname}",
            f"🏷️  Tier: {fp.tier.value.upper()}",
            f"🔑 ID: {fp.fingerprint_id}",
            "",
            "─" * 50,
            "⚡ CPU",
            "─" * 50,
            f"   Model: {fp.cpu.model}",
            f"   Vendor: {fp.cpu.vendor}",
            f"   Cores: {fp.cpu.physical_cores} physical, {fp.cpu.logical_cores} logical",
            f"   Frequency: {fp.cpu.current_frequency_mhz:.0f} MHz (max: {fp.cpu.max_frequency_mhz:.0f} MHz)",
            "",
        ]
        
        if fp.gpu.available:
            lines.extend([
                "─" * 50,
                "🎮 GPU",
                "─" * 50,
                f"   Model: {fp.gpu.model}",
                f"   Vendor: {fp.gpu.vendor.value.upper()}",
                f"   VRAM: {fp.gpu.vram_mb} MB ({fp.gpu.vram_available_mb} MB available)",
                "",
            ])
        else:
            lines.extend([
                "─" * 50,
                "🎮 GPU: Not detected / Integrated only",
                "",
            ])
        
        lines.extend([
            "─" * 50,
            "🧠 Memory",
            "─" * 50,
            f"   Total: {fp.ram.total_gb:.1f} GB",
            f"   Available: {fp.ram.available_gb:.1f} GB",
            f"   Used: {fp.ram.percent_used:.1f}%",
            "",
            "─" * 50,
            "🛡️ Safety Limits",
            "─" * 50,
            f"   Max CPU: {fp.max_cpu_percent}%",
            f"   Max Memory: {fp.max_memory_percent}%",
            f"   Max GPU: {fp.max_gpu_percent}%",
            f"   Max Temp: {fp.max_temperature_c}°C",
            "",
            "═" * 50,
        ])
        
        return "\n".join(lines)


# ============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# ============================================================================

_discovery_instance: Optional[HardwareDiscovery] = None

def get_hardware_fingerprint(force_refresh: bool = False) -> HardwareFingerprint:
    """Get hardware fingerprint (singleton pattern)"""
    global _discovery_instance
    if _discovery_instance is None:
        _discovery_instance = HardwareDiscovery()
    return _discovery_instance.discover(force_refresh)

def get_discovery_engine() -> HardwareDiscovery:
    """Get the hardware discovery engine instance"""
    global _discovery_instance
    if _discovery_instance is None:
        _discovery_instance = HardwareDiscovery()
    return _discovery_instance


# ============================================================================
# CLI INTERFACE (for testing)
# ============================================================================

if __name__ == "__main__":
    print("Scanning hardware...")
    discovery = HardwareDiscovery()
    fingerprint = discovery.discover()
    print(discovery.format_summary())
    
    # Check safety
    safe, violations = discovery.is_within_safety_limits()
    if safe:
        print("✅ All resources within safety limits")
    else:
        print("⚠️ Safety violations:")
        for v in violations:
            print(f"   - {v}")
