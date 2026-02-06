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



# ═══════════════════════════════════════════════════════════
# ANALYZE COMMAND HANDLER
# ═══════════════════════════════════════════════════════════

def handle_analyze_command(args: list, write_fn) -> None:
    """
    Handle 'analyze' terminal command.

    Usage:
      analyze circuit <qubits> [depth] [--shots N] [--variational]
      analyze qubo <variables> [--reads N]
      analyze matrix <operation> <rows> <cols> [--iterations N]
      analyze synthesis [--dims N] [--states N] [--no-lorentz]
      analyze help
    """
    if not args:
        _show_analyze_help(write_fn)
        return

    subcmd = args[0].lower()

    if subcmd == "help":
        _show_analyze_help(write_fn)
        return

    if subcmd == "circuit":
        _analyze_circuit_cmd(args[1:], write_fn)
    elif subcmd == "qubo":
        _analyze_qubo_cmd(args[1:], write_fn)
    elif subcmd in ("matrix", "classical"):
        _analyze_matrix_cmd(args[1:], write_fn)
    elif subcmd in ("synthesis", "pse"):
        _analyze_synthesis_cmd(args[1:], write_fn)
    else:
        write_fn(f"❌ Unknown analyze subcommand: {subcmd}\n")
        write_fn("   Run 'analyze help' for usage.\n")


def _analyze_circuit_cmd(args: list, write_fn) -> None:
    """Parse and run circuit analysis."""
    from integration.analyzer import analyze_circuit, format_analysis

    if not args:
        write_fn("❌ Usage: analyze circuit <qubits> [depth] [--shots N] [--variational]\n")
        write_fn("   Example: analyze circuit 10 20\n")
        write_fn("   Example: analyze circuit 5 10 --variational\n")
        return

    try:
        qubits = int(args[0])
    except ValueError:
        write_fn(f"❌ Invalid qubit count: {args[0]}\n")
        return

    depth = 0
    shots = 1024
    variational = False

    i = 1
    while i < len(args):
        if args[i] == "--shots" and i + 1 < len(args):
            shots = int(args[i + 1])
            i += 2
        elif args[i] == "--variational":
            variational = True
            i += 1
        else:
            try:
                depth = int(args[i])
            except ValueError:
                pass
            i += 1

    result = analyze_circuit(qubits, depth, shots=shots, is_variational=variational)
    format_analysis(result, write_fn)


def _analyze_qubo_cmd(args: list, write_fn) -> None:
    """Parse and run QUBO analysis."""
    from integration.analyzer import analyze_qubo, format_analysis

    if not args:
        write_fn("❌ Usage: analyze qubo <variables> [--reads N]\n")
        write_fn("   Example: analyze qubo 50\n")
        return

    try:
        variables = int(args[0])
    except ValueError:
        write_fn(f"❌ Invalid variable count: {args[0]}\n")
        return

    reads = 100
    if "--reads" in args:
        idx = args.index("--reads")
        if idx + 1 < len(args):
            reads = int(args[idx + 1])

    result = analyze_qubo(variables, num_reads=reads)
    format_analysis(result, write_fn)


def _analyze_matrix_cmd(args: list, write_fn) -> None:
    """Parse and run classical matrix analysis."""
    from integration.analyzer import analyze_matrix, format_analysis

    operations = ["matmul", "eigenvalue", "fft", "svd", "inverse", "solve", "simulation"]

    if not args:
        write_fn("❌ Usage: analyze matrix <operation> <rows> <cols> [--iterations N]\n")
        write_fn(f"   Operations: {', '.join(operations)}\n")
        write_fn("   Example: analyze matrix matmul 1000 1000\n")
        return

    op = args[0].lower() if args else "matmul"
    if op not in operations:
        write_fn(f"❌ Unknown operation: {op}\n")
        write_fn(f"   Available: {', '.join(operations)}\n")
        return

    rows, cols, iters = 100, 100, 1
    if len(args) >= 2:
        try:
            rows = int(args[1])
        except ValueError:
            pass
    if len(args) >= 3:
        try:
            cols = int(args[2])
        except ValueError:
            pass
    if "--iterations" in args:
        idx = args.index("--iterations")
        if idx + 1 < len(args):
            iters = int(args[idx + 1])

    result = analyze_matrix(op, (rows, cols), iterations=iters)
    format_analysis(result, write_fn)


def _analyze_synthesis_cmd(args: list, write_fn) -> None:
    """Parse and run PSE analysis."""
    from integration.analyzer import analyze_pse, format_analysis

    dims, states, lorentz = 3, 8, True

    i = 0
    while i < len(args):
        if args[i] == "--dims" and i + 1 < len(args):
            dims = int(args[i + 1]); i += 2
        elif args[i] == "--states" and i + 1 < len(args):
            states = int(args[i + 1]); i += 2
        elif args[i] == "--no-lorentz":
            lorentz = False; i += 1
        else:
            i += 1

    result = analyze_pse(
        input_dimensions=dims,
        superposition_states=states,
        lorentz_corrections=lorentz,
    )
    format_analysis(result, write_fn)


def _show_analyze_help(write_fn) -> None:
    """Show analyze command help."""
    write_fn("\n")
    write_fn("═" * 62 + "\n")
    write_fn("🔬 WORKLOAD ANALYZER — Profile & Route Computations\n")
    write_fn("═" * 62 + "\n\n")
    write_fn("COMMANDS:\n\n")
    write_fn("  analyze circuit <qubits> [depth] [options]\n")
    write_fn("    Profile a quantum gate circuit and find best provider.\n")
    write_fn("    Options: --shots N  --variational\n")
    write_fn("    Example: analyze circuit 10 20\n")
    write_fn("    Example: analyze circuit 5 10 --variational\n\n")
    write_fn("  analyze qubo <variables> [options]\n")
    write_fn("    Profile a QUBO/annealing optimization problem.\n")
    write_fn("    Options: --reads N\n")
    write_fn("    Example: analyze qubo 200\n\n")
    write_fn("  analyze matrix <op> <rows> <cols> [options]\n")
    write_fn("    Profile a classical numerical computation.\n")
    write_fn("    Ops: matmul, eigenvalue, fft, svd, inverse, solve, simulation\n")
    write_fn("    Options: --iterations N\n")
    write_fn("    Example: analyze matrix matmul 1000 1000\n")
    write_fn("    Example: analyze matrix eigenvalue 500 500\n\n")
    write_fn("  analyze synthesis [options]\n")
    write_fn("    Profile a Predictive Synthesis Engine workload.\n")
    write_fn("    Options: --dims N  --states N  --no-lorentz\n")
    write_fn("    Example: analyze synthesis --dims 5 --states 32\n\n")
    write_fn("WHAT YOU GET:\n")
    write_fn("  • Workload classification (quantum/classical/hybrid)\n")
    write_fn("  • Complexity tier (trivial → infeasible)\n")
    write_fn("  • Memory, CPU time, GPU usefulness estimates\n")
    write_fn("  • Ranked provider matches with suitability scores\n")
    write_fn("  • Routing recommendation (local vs cloud)\n")
    write_fn("  • Actionable tips for your hardware tier\n\n")
    write_fn("═" * 62 + "\n\n")
