#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Integration Terminal Commands
Phase 3: Terminal command handlers for hardware discovery and provider registry.

Commands:
  hardware    - Hardware discovery and fingerprinting (Step 1)
  providers   - Provider registry listing and management (Step 2)
  connect     - Connect to a compute provider
  disconnect  - Disconnect from a provider

ALL imports are lazy — modules only load when the command is invoked.
"""

from typing import List, Callable


def handle_providers_command(args: List[str], write_fn: Callable) -> None:
    """
    Handle the 'providers' terminal command.
    
    Usage:
      providers              Show provider summary
      providers scan         Refresh SDK availability scan
      providers info <id>    Detailed info for a provider
      providers install <id> Show pip install command
      providers quantum      List quantum providers only
      providers classical    List classical providers only
    """
    from integration.providers.registry import get_registry, ProviderType
    
    registry = get_registry()

    if not args:
        write_fn(registry.format_summary() + "\n")
        return
    
    subcmd = args[0].lower()
    
    if subcmd == "scan":
        write_fn("🔍 Scanning all provider SDKs...\n")
        results = registry.scan_all(force=True)
        installed = sum(1 for s in results.values() if s.sdk_installed)
        write_fn(f"✅ Scan complete: {installed}/{len(results)} SDKs installed\n\n")
        write_fn(registry.format_summary() + "\n")
    
    elif subcmd == "info":
        if len(args) < 2:
            write_fn("❌ Usage: providers info <provider_id>\n")
            write_fn("   Example: providers info ibm_quantum\n")
            return
        write_fn(registry.format_provider_detail(args[1]) + "\n\n")
    
    elif subcmd == "install":
        if len(args) < 2:
            write_fn("❌ Usage: providers install <provider_id>\n")
            return
        info = registry.get_provider(args[1])
        if not info:
            write_fn(f"❌ Unknown provider: {args[1]}\n")
            return
        write_fn(f"\n📦 To install {info.name} SDK:\n")
        write_fn(f"   pip install {info.sdk_package}\n\n")
        if info.notes:
            write_fn(f"   Note: {info.notes}\n\n")

    elif subcmd == "quantum":
        write_fn("\n⚛️  QUANTUM PROVIDERS:\n\n")
        for p in registry.list_providers(ProviderType.QUANTUM_CLOUD):
            state = registry.get_state(p.id)
            icon = "🟢" if state.sdk_installed else "⚪"
            write_fn(f"  {icon} {p.id:<22} {p.name:<24} {p.max_qubits}q\n")
        for p in registry.list_providers(ProviderType.QUANTUM_LOCAL):
            state = registry.get_state(p.id)
            icon = "🟢" if state.sdk_installed else "⚪"
            write_fn(f"  {icon} {p.id:<22} {p.name:<24} {p.max_qubits}q\n")
        write_fn("\n")
    
    elif subcmd == "classical":
        write_fn("\n⚡ CLASSICAL PROVIDERS:\n\n")
        for ptype in [ProviderType.CLASSICAL_CPU, ProviderType.CLASSICAL_GPU, ProviderType.CLASSICAL_ACCEL]:
            for p in registry.list_providers(ptype):
                state = registry.get_state(p.id)
                icon = "🟢" if state.sdk_installed else "⚪"
                write_fn(f"  {icon} {p.id:<22} {p.name}\n")
        write_fn("\n")
    
    elif subcmd == "list":
        # Alias for no-arg
        write_fn(registry.format_summary() + "\n")
    
    elif subcmd in ("suggest", "recommend", "guide"):
        from integration.guide import generate_suggestions
        generate_suggestions(write_fn)
    
    elif subcmd == "setup":
        if len(args) < 2:
            write_fn("❌ Usage: providers setup <provider_id>\n")
            write_fn("   Example: providers setup ibm_quantum\n")
            return
        from integration.guide import generate_setup_guide
        generate_setup_guide(args[1], write_fn)
    
    else:
        write_fn(f"❌ Unknown subcommand: {subcmd}\n")
        write_fn("   Usage: providers [scan|info|install|quantum|classical|suggest|setup <id>]\n")


def handle_connect_command(args: List[str], write_fn: Callable) -> None:
    """
    Handle the 'connect' terminal command.
    
    Usage:
      connect <provider_id>    Connect to a provider
      connect                  Show usage help
    """
    from integration.providers.registry import get_registry, ProviderStatus
    
    if not args:
        write_fn("\n🔌 CONNECT — Establish provider connection\n\n")
        write_fn("  Usage: connect <provider_id>\n")
        write_fn("  Example: connect ibm_quantum\n")
        write_fn("  Example: connect local_simulator\n\n")
        write_fn("  Run 'providers' to see available provider IDs.\n\n")
        return
    
    provider_id = args[0].lower()
    registry = get_registry()
    info = registry.get_provider(provider_id)
    
    if not info:
        write_fn(f"❌ Unknown provider: {provider_id}\n")
        write_fn("   Run 'providers' to see available IDs.\n")
        return
    
    write_fn(f"🔌 Connecting to {info.name}...\n")
    state = registry.connect(provider_id)

    if state.status == ProviderStatus.CONNECTED:
        write_fn(f"✅ Connected to {info.name}\n")
        if state.available_backends:
            write_fn(f"   Backends: {', '.join(state.available_backends)}\n")
    elif state.status == ProviderStatus.UNAVAILABLE:
        write_fn(f"❌ SDK not installed.\n")
        write_fn(f"   Install: pip install {info.sdk_package}\n")
    elif state.status == ProviderStatus.NOT_CONFIGURED:
        write_fn(f"⚠️  SDK installed but credentials not configured.\n")
        write_fn(f"   Visit: {info.website}\n")
    else:
        write_fn(f"❌ Connection failed: {state.last_error}\n")


def handle_disconnect_command(args: List[str], write_fn: Callable) -> None:
    """
    Handle the 'disconnect' terminal command.
    
    Usage:
      disconnect <provider_id>   Disconnect from a provider
      disconnect all              Disconnect all providers
    """
    from integration.providers.registry import get_registry
    
    if not args:
        write_fn("❌ Usage: disconnect <provider_id> or disconnect all\n")
        return
    
    registry = get_registry()
    
    if args[0].lower() == "all":
        connected = registry.get_connected_providers()
        for pid in connected:
            registry.disconnect(pid)
        write_fn(f"🔌 Disconnected from {len(connected)} provider(s).\n")
        return

    provider_id = args[0].lower()
    info = registry.get_provider(provider_id)
    
    if not info:
        write_fn(f"❌ Unknown provider: {provider_id}\n")
        return
    
    registry.disconnect(provider_id)
    write_fn(f"🔌 Disconnected from {info.name}.\n")
