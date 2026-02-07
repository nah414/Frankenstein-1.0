#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Provider Guide Engine
Phase 3, Step 2: Intelligent provider recommendations

Generates real, personalized guidance based on:
- Detected hardware (from discovery.py)
- Installed SDKs (from registry.py)
- Provider compatibility with the user's system
- Step-by-step setup instructions per provider

This module is LAZY-LOADED — only runs when the user invokes
'providers suggest', 'providers guide', or 'providers setup'.
"""

from typing import List, Dict, Optional, Any, Callable


def generate_suggestions(write_fn: Callable) -> None:
    """
    Generate real provider suggestions based on detected hardware.
    Cross-references hardware fingerprint with provider catalog
    to produce actionable, ranked recommendations.
    """
    from integration.discovery import get_hardware_fingerprint, HardwareTier
    from integration.providers.registry import (
        get_registry, ALL_PROVIDERS, ProviderType, ProviderStatus
    )

    fp = get_hardware_fingerprint()
    registry = get_registry()
    registry.scan_all()

    # ── Collect live data ──
    ram_gb = fp.ram.total_gb
    cores = fp.cpu.logical_cores
    tier = fp.tier
    gpu_available = fp.gpu.available
    gpu_vendor = fp.gpu.vendor.value if fp.gpu.available else "none"
    has_internet = fp.network.has_internet

    installed_ids = registry.get_available_providers()
    connected_ids = registry.get_connected_providers()

    # ── Header ──
    write_fn("\n")
    write_fn("═" * 62 + "\n")
    write_fn("🧠 PROVIDER SUGGESTIONS — Personalized for Your System\n")
    write_fn("═" * 62 + "\n\n")

    write_fn(f"  Your Hardware:\n")
    write_fn(f"    CPU:  {fp.cpu.model}  ({cores} threads)\n")
    write_fn(f"    RAM:  {ram_gb:.1f} GB\n")
    write_fn(f"    GPU:  {fp.gpu.model if gpu_available else 'Not detected / Integrated'}\n")
    write_fn(f"    Tier: {tier.value.upper()}\n")
    write_fn(f"    Net:  {'Online' if has_internet else 'Offline'}\n\n")

    # ── SECTION 1: What's ready right now ──
    write_fn("─── ✅ READY TO USE (installed on your system) ───\n\n")

    ready_found = False
    for pid in installed_ids:
        info = ALL_PROVIDERS[pid]
        state = registry.get_state(pid)
        is_conn = pid in connected_ids
        conn_tag = " 🟢 CONNECTED" if is_conn else ""
        write_fn(f"  • {info.name} (v{state.sdk_version}){conn_tag}\n")

        # Give context based on provider type
        if pid == "local_simulator":
            max_q = min(20, int(ram_gb * 2.5))
            write_fn(f"    → Simulates up to ~{max_q} qubits on your {ram_gb:.0f}GB RAM\n")
            write_fn(f"    → No internet needed. Great for learning & prototyping.\n")
            if not is_conn:
                write_fn(f"    → Try: connect local_simulator\n")
        elif pid == "local_cpu":
            write_fn(f"    → NumPy/SciPy compute on {cores} threads\n")
            write_fn(f"    → Handles synthesis engine, matrix ops, simulations\n")
            if not is_conn:
                write_fn(f"    → Try: connect local_cpu\n")
        elif pid == "ibm_quantum":
            write_fn(f"    → Access real quantum hardware (up to 127 qubits)\n")
            write_fn(f"    → Free tier: 10 min/month on real QPUs\n")
            write_fn(f"    → Try: connect ibm_quantum\n")
        else:
            write_fn(f"    → Type: providers info {pid}\n")
        write_fn("\n")
        ready_found = True

    if not ready_found:
        write_fn("  (none detected — run 'providers scan' to refresh)\n\n")

    # ── SECTION 2: Ranked recommendations to install ──
    write_fn("─── 🎯 RECOMMENDED NEXT INSTALLS (ranked for your hardware) ───\n\n")

    # Build ranked recommendations based on hardware
    recommendations = []

    # Always recommend quantum providers with free tiers
    for pid, info in ALL_PROVIDERS.items():
        if pid in installed_ids:
            continue  # Already installed

        score = 0
        reason = ""

        # Quantum cloud — great for Tier 1 since compute is remote
        if info.provider_type == ProviderType.QUANTUM_CLOUD:
            if info.free_tier:
                score += 30
                reason = "Free tier available"
            if has_internet:
                score += 20
                reason += ", you're online"
            else:
                score -= 50
                reason = "Needs internet (you're offline)"

            # Specific boosts
            if pid == "aws_braket":
                score += 10
                reason += ". Multi-provider access (IonQ, Rigetti, D-Wave)"
            elif pid == "xanadu":
                score += 5
                reason += ". Auto-differentiation for quantum ML"
            elif pid == "dwave" and tier.value in ("tier1", "tier2"):
                score += 15
                reason += ". Annealing is lightweight — ideal for Tier 1"

        # GPU providers — only if GPU detected
        if info.provider_type == ProviderType.CLASSICAL_GPU:
            if not gpu_available:
                score -= 100  # Skip if no GPU
                reason = "No compatible GPU detected"
            elif pid == "nvidia_cuda" and gpu_vendor == "nvidia":
                score += 40
                reason = f"NVIDIA {fp.gpu.model} detected — CUDA will accelerate compute"
            elif pid == "amd_rocm" and gpu_vendor == "amd":
                score += 40
                reason = f"AMD {fp.gpu.model} detected — ROCm will accelerate compute"
            elif pid == "apple_metal" and gpu_vendor == "apple":
                score += 40
                reason = f"Apple Silicon detected — Metal will accelerate compute"
            else:
                score -= 50
                reason = f"Your GPU is {gpu_vendor}, this needs a different vendor"

        # Intel oneAPI — boost if Intel CPU
        if pid == "intel_oneapi":
            if "intel" in fp.cpu.vendor.lower():
                score += 25
                reason = f"You have an Intel CPU — oneAPI optimizes NumPy for Intel"
            else:
                score -= 20
                reason = "Designed for Intel CPUs, limited benefit on yours"

        if score > 0:
            recommendations.append((score, pid, info, reason))

    # Sort by score descending
    recommendations.sort(key=lambda x: -x[0])

    if recommendations:
        for i, (score, pid, info, reason) in enumerate(recommendations[:6], 1):
            free_tag = " [FREE]" if info.free_tier else ""
            qubits = f" · {info.max_qubits}q" if info.max_qubits else ""
            write_fn(f"  {i}. {info.name}{free_tag}{qubits}\n")
            write_fn(f"     Why: {reason}\n")
            write_fn(f"     Install: pip install {info.sdk_package}\n")
            write_fn(f"     Details: providers info {pid}\n\n")
    else:
        write_fn("  All relevant providers are already installed!\n\n")

    # ── SECTION 3: Hardware-specific tips ──
    write_fn("─── 💡 TIPS FOR YOUR HARDWARE TIER ───\n\n")

    if tier.value == "tier1":
        write_fn("  Your system is TIER 1 (Baseline Laptop). Best strategies:\n\n")
        write_fn("  • Use cloud quantum providers — your QPU time runs on their\n")
        write_fn("    hardware, not yours. IBM Quantum & D-Wave are great starts.\n\n")
        write_fn("  • Local quantum simulation caps at ~16-20 qubits before\n")
        write_fn(f"    memory pressure hits (you have {ram_gb:.0f}GB). For larger\n")
        write_fn("    circuits, offload to cloud.\n\n")
        write_fn("  • CPU safety limits: max 80% CPU, 70% RAM. The governor\n")
        write_fn("    enforces this automatically.\n\n")
        write_fn("  • Intel oneAPI can squeeze ~15-30% more performance from\n")
        write_fn("    your Intel CPU for NumPy-heavy workloads.\n\n")
    elif tier.value == "tier2":
        write_fn("  Your system is TIER 2 (Workstation). Good balance of options:\n\n")
        write_fn("  • Local simulation handles 20-24 qubits comfortably.\n")
        write_fn("  • Cloud quantum expands your reach to 100+ qubits.\n")
        write_fn("  • If you have a discrete GPU, install the matching SDK.\n\n")
    elif tier.value in ("tier3", "tier4", "tier5"):
        write_fn(f"  Your system is {tier.value.upper()} (High Performance). Full capability:\n\n")
        write_fn("  • Local simulation can handle 24-30+ qubits.\n")
        write_fn("  • GPU acceleration significantly speeds matrix operations.\n")
        write_fn("  • All cloud providers are viable for hybrid workloads.\n\n")

    write_fn("═" * 62 + "\n")
    write_fn("  Run 'providers' to see full list. Run 'providers setup <id>'\n")
    write_fn("  for step-by-step setup instructions for any provider.\n")
    write_fn("═" * 62 + "\n\n")


def generate_setup_guide(provider_id: str, write_fn: Callable) -> None:
    """
    Generate step-by-step setup instructions for a specific provider.
    Tailored to the user's OS and current state.
    """
    from integration.providers.registry import get_registry, ALL_PROVIDERS

    registry = get_registry()
    info = ALL_PROVIDERS.get(provider_id)

    if not info:
        write_fn(f"❌ Unknown provider: {provider_id}\n")
        write_fn("   Run 'providers' to see available IDs.\n")
        return

    state = registry.get_state(provider_id)

    write_fn("\n")
    write_fn("═" * 62 + "\n")
    write_fn(f"📘 SETUP GUIDE: {info.name}\n")
    write_fn("═" * 62 + "\n\n")

    # Step 1: SDK Install
    if state.sdk_installed:
        write_fn(f"  ✅ Step 1: Install SDK — DONE (v{state.sdk_version})\n\n")
    else:
        write_fn(f"  📦 Step 1: Install the SDK\n")
        write_fn(f"     pip install {info.sdk_package}\n\n")

    # Provider-specific steps
    guides = {
        "ibm_quantum": [
            ("Create IBM Quantum account",
             "Go to https://quantum.ibm.com and sign up (free)"),
            ("Get your API token",
             "Dashboard → Account → Copy your API token"),
            ("Save token locally",
             "In Frankenstein terminal, run:\n"
             "       python -c \"from qiskit_ibm_runtime import QiskitRuntimeService; "
             "QiskitRuntimeService.save_account(channel='ibm_quantum', token='YOUR_TOKEN')\""),
            ("Connect in Frankenstein",
             "connect ibm_quantum"),
            ("Verify",
             "providers info ibm_quantum  (should show 🟢 Connected)"),
        ],
        "aws_braket": [
            ("Create AWS account",
             "Go to https://aws.amazon.com and sign up"),
            ("Enable Braket",
             "AWS Console → Amazon Braket → Get Started"),
            ("Configure AWS CLI",
             "pip install awscli\n       aws configure  (enter Access Key, Secret, Region)"),
            ("Connect in Frankenstein",
             "connect aws_braket"),
        ],
        "azure_quantum": [
            ("Create Azure account",
             "Go to https://azure.microsoft.com and sign up (free credits)"),
            ("Create Quantum Workspace",
             "Azure Portal → Create Resource → Azure Quantum"),
            ("Install Azure CLI",
             "pip install azure-cli\n       az login"),
            ("Connect in Frankenstein",
             "connect azure_quantum"),
        ],
        "google_cirq": [
            ("Install Cirq",
             "pip install cirq"),
            ("Explore locally",
             "Cirq works locally as a simulator by default"),
            ("Apply for hardware access",
             "Visit https://quantumai.google for research access"),
            ("Connect in Frankenstein",
             "connect google_cirq"),
        ],
        "ionq": [
            ("Access via AWS Braket or Azure",
             "IonQ hardware is available through AWS Braket and Azure Quantum"),
            ("Or use direct API",
             "Sign up at https://cloud.ionq.com"),
            ("Install SDK",
             "pip install cirq-ionq"),
            ("Connect in Frankenstein",
             "connect ionq"),
        ],
        "rigetti": [
            ("Create QCS account",
             "Sign up at https://qcs.rigetti.com (free tier available)"),
            ("Install PyQuil",
             "pip install pyquil"),
            ("Connect in Frankenstein",
             "connect rigetti"),
        ],
        "xanadu": [
            ("Install PennyLane",
             "pip install pennylane"),
            ("Explore locally",
             "PennyLane works locally with built-in simulators"),
            ("Optional: Xanadu Cloud",
             "Sign up at https://platform.xanadu.ai for photonic hardware"),
            ("Connect in Frankenstein",
             "connect xanadu"),
        ],
        "dwave": [
            ("Create Leap account",
             "Sign up at https://cloud.dwavesys.com/leap (free 1 min/month)"),
            ("Install Ocean SDK",
             "pip install dwave-ocean-sdk"),
            ("Configure token",
             "dwave config create  (paste your API token)"),
            ("Connect in Frankenstein",
             "connect dwave"),
        ],
        "local_simulator": [
            ("Already available",
             "NumPy is installed. No setup needed."),
            ("Connect",
             "connect local_simulator"),
            ("Start using",
             "Enter quantum mode: q\n       Initialize: qubit 2\n       Apply gates: h 0, cx 0 1\n       Measure: measure"),
        ],
        "local_cpu": [
            ("Already available",
             "NumPy/SciPy on local CPU. No setup needed."),
            ("Connect",
             "connect local_cpu"),
            ("Use for",
             "Synthesis engine, matrix operations, classical simulations"),
        ],
        "nvidia_cuda": [
            ("Verify NVIDIA GPU",
             "Run: hardware  (check GPU section for NVIDIA detection)"),
            ("Install CUDA Toolkit",
             "Download from https://developer.nvidia.com/cuda-downloads"),
            ("Install CuPy",
             "pip install cupy-cuda12x  (match your CUDA version)"),
            ("Connect in Frankenstein",
             "connect nvidia_cuda"),
        ],
        "amd_rocm": [
            ("Verify AMD GPU",
             "Run: hardware  (check GPU section for AMD detection)"),
            ("Install ROCm",
             "Follow https://rocm.docs.amd.com/en/latest/deploy/linux/quick_start.html"),
            ("Install PyTorch ROCm",
             "pip install torch --index-url https://download.pytorch.org/whl/rocm6.0"),
            ("Connect in Frankenstein",
             "connect amd_rocm"),
        ],
        "intel_oneapi": [
            ("Install oneAPI toolkit",
             "Download from https://www.intel.com/content/www/us/en/developer/tools/oneapi/overview.html"),
            ("Install DPNP",
             "pip install dpnp"),
            ("Connect in Frankenstein",
             "connect intel_oneapi"),
        ],
        "apple_metal": [
            ("Verify Apple Silicon",
             "Run: hardware  (check GPU for Apple detection)"),
            ("Install PyTorch",
             "pip install torch torchvision torchaudio"),
            ("Verify MPS backend",
             "python -c \"import torch; print(torch.backends.mps.is_available())\""),
            ("Connect in Frankenstein",
             "connect apple_metal"),
        ],
    }

    steps = guides.get(provider_id, [])

    if steps:
        start = 1 if state.sdk_installed else 2  # Skip step 1 if SDK installed
        for i, (title, instruction) in enumerate(steps, start):
            write_fn(f"  📌 Step {i}: {title}\n")
            write_fn(f"     {instruction}\n\n")
    else:
        write_fn(f"  No step-by-step guide available yet for {info.name}.\n")
        write_fn(f"  Visit: {info.website}\n\n")

    if info.notes:
        write_fn(f"  ℹ️  {info.notes}\n\n")

    write_fn("═" * 62 + "\n\n")
