#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Router Terminal Commands
Phase 3, Step 5.7: Monster Terminal integration for routing

Commands:
  route --qubits N --depth N --priority MODE   Route a workload
  route-options --type TYPE --qubits N          Show compatible providers
  route-test --provider NAME --qubits N         Test specific routing
  route-history                                 Show past routing decisions

All imports are lazy-loaded. Output uses Monster Terminal theme.
"""

from typing import List, Callable


def handle_route_command(args: List[str], write_output: Callable):
    """
    Handle the 'route' command — route a workload and show decision.

    Usage:
      route --qubits 10 --priority cost
      route --type quantum_simulation --qubits 5 --depth 100
      route --type classical_optimization --threads 2 --memory 512
    """
    # Parse arguments
    spec = _parse_route_args(args)

    if spec is None:
        write_output(_route_usage())
        return

    try:
        from .intelligent_router import get_router
        router = get_router()
        result = router.route(spec)
    except Exception as e:
        write_output(f"  Error: Routing failed: {e}\n")
        return

    # Format output
    lines = [
        "",
        "=" * 58,
        "  INTELLIGENT ROUTER — ROUTING DECISION",
        "=" * 58,
        "",
        f"  Workload:    {result.get('workload_summary', 'N/A')}",
        "",
        f"  PRIMARY PROVIDER: {result['provider']}",
        f"  Score:            {result['score']:.4f}",
        "",
    ]

    # Safety info
    safety = result.get("safety", {})
    safe_icon = "PASS" if safety.get("safe", True) else "WARN"
    lines.append(f"  Safety:      [{safe_icon}]")
    lines.append(f"    CPU:       {safety.get('estimated_cpu', 0):.1f}% (limit 80%)")
    lines.append(f"    RAM:       {safety.get('estimated_ram', 0):.1f}% (limit 70%)")
    lines.append("")

    # Fallbacks
    fallbacks = result.get("fallbacks", [])
    if fallbacks:
        lines.append("  FALLBACK CHAIN:")
        for i, fb in enumerate(fallbacks, 1):
            lines.append(f"    {i}. {fb}")
        lines.append("")

    # Alternatives
    alts = result.get("alternatives", [])
    if alts:
        lines.append("  ALTERNATIVES:")
        for alt in alts:
            lines.append(f"    - {alt}")
        lines.append("")

    # Reasoning
    lines.append(f"  Reasoning: {result.get('reasoning', '')}")
    lines.append(f"  Routed in: {result.get('routing_time_ms', 0):.1f}ms")
    lines.append("")
    lines.append("=" * 58)
    lines.append("")

    write_output("\n".join(lines))


def handle_route_options_command(args: List[str], write_output: Callable):
    """
    Handle 'route-options' — show all compatible providers for a workload.

    Usage:
      route-options --type quantum_simulation --qubits 10
      route-options --qubits 5 --priority accuracy
    """
    spec = _parse_route_args(args)
    if spec is None:
        write_output(
            "\nUsage: route-options --type TYPE --qubits N [--priority MODE]\n"
            "Types: quantum_simulation, classical_optimization, "
            "hybrid_computation, data_synthesis\n\n"
        )
        return

    try:
        from .intelligent_router import get_router
        router = get_router()
        recommendations = router.get_recommendations(spec)
    except Exception as e:
        write_output(f"  Error: {e}\n")
        return

    lines = [
        "",
        "=" * 58,
        "  COMPATIBLE PROVIDERS — RANKED",
        "=" * 58,
        "",
        f"  {'Rank':<6} {'Provider':<24} {'Score':<8} {'Safe':<6} {'CPU%':<8} {'RAM%'}",
        f"  {'─'*6} {'─'*24} {'─'*8} {'─'*6} {'─'*8} {'─'*6}",
    ]

    for entry in recommendations:
        safe_icon = "YES" if entry.get("safe", True) else "NO"
        lines.append(
            f"  {entry['rank']:<6} "
            f"{entry['provider_id']:<24} "
            f"{entry['score']:<8.4f} "
            f"{safe_icon:<6} "
            f"{entry.get('estimated_cpu', 0):<8.1f} "
            f"{entry.get('estimated_ram', 0):.1f}"
        )

    lines.extend(["", "=" * 58, ""])
    write_output("\n".join(lines))


def handle_route_test_command(args: List[str], write_output: Callable):
    """
    Handle 'route-test' — test routing to a specific provider.

    Usage:
      route-test --provider ibm_quantum --qubits 10
      route-test --provider local_simulator --qubits 5
    """
    provider = None
    qubits = 5
    depth = 10

    i = 0
    while i < len(args):
        if args[i] == "--provider" and i + 1 < len(args):
            provider = args[i + 1]
            i += 2
        elif args[i] == "--qubits" and i + 1 < len(args):
            qubits = int(args[i + 1])
            i += 2
        elif args[i] == "--depth" and i + 1 < len(args):
            depth = int(args[i + 1])
            i += 2
        else:
            i += 1

    if not provider:
        write_output(
            "\nUsage: route-test --provider NAME --qubits N [--depth N]\n\n"
        )
        return

    try:
        from .safety_filter import check_resource_safety
        from .scoring import calculate_provider_score
        from .fallback import get_fallback_chain
        from .workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec(
            workload_type=WorkloadType.QUANTUM_SIMULATION,
            qubit_count=qubits,
            circuit_depth=depth,
        )

        # Get current resource usage
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            current_cpu = cpu
            current_ram = mem.percent
            total_ram_mb = mem.total / (1024 * 1024)
        except ImportError:
            current_cpu = 0.0
            current_ram = 0.0
            total_ram_mb = 8192.0

        safety = check_resource_safety(
            provider, spec, current_cpu, current_ram, total_ram_mb
        )
        score = calculate_provider_score(provider, spec, "cost")
        chain = get_fallback_chain(provider)

        safe_str = "PASS" if safety["safe"] else "FAIL"

        lines = [
            "",
            "=" * 58,
            f"  ROUTE TEST: {provider}",
            "=" * 58,
            "",
            f"  Provider:     {provider}",
            f"  Qubits:       {qubits}",
            f"  Circuit Depth: {depth}",
            "",
            f"  Score (cost): {score:.4f}",
            f"  Safety:       [{safe_str}]",
            f"    Current CPU:  {current_cpu:.1f}%",
            f"    Current RAM:  {current_ram:.1f}%",
            f"    Est. CPU:     {safety['estimated_cpu']:.1f}% (limit 80%)",
            f"    Est. RAM:     {safety['estimated_ram']:.1f}% (limit 70%)",
            "",
        ]

        if not safety["safe"]:
            lines.append(f"  REASON: {safety['reason']}")
            lines.append("")

        if chain:
            lines.append("  Fallback chain:")
            for i, fb in enumerate(chain, 1):
                lines.append(f"    {i}. {fb}")
            lines.append("")

        lines.extend(["=" * 58, ""])
        write_output("\n".join(lines))

    except Exception as e:
        write_output(f"  Error: Route test failed: {e}\n")


def handle_route_history_command(args: List[str], write_output: Callable):
    """
    Handle 'route-history' — show past routing decisions.

    Usage:
      route-history
      route-history --limit 10
    """
    limit = 20
    for i, arg in enumerate(args):
        if arg == "--limit" and i + 1 < len(args):
            try:
                limit = int(args[i + 1])
            except ValueError:
                pass

    try:
        from .intelligent_router import get_router
        router = get_router()
        history = router.get_history(limit)
    except Exception as e:
        write_output(f"  Error: {e}\n")
        return

    if not history:
        write_output("\n  No routing history yet. Run 'route' to make a decision.\n\n")
        return

    lines = [
        "",
        "=" * 58,
        "  ROUTING HISTORY",
        "=" * 58,
        "",
        f"  {'#':<4} {'Provider':<20} {'Score':<8} {'Time(ms)':<10} {'Workload'}",
        f"  {'─'*4} {'─'*20} {'─'*8} {'─'*10} {'─'*20}",
    ]

    for i, entry in enumerate(history, 1):
        lines.append(
            f"  {i:<4} "
            f"{entry.get('provider', '?'):<20} "
            f"{entry.get('score', 0):<8.4f} "
            f"{entry.get('routing_time_ms', 0):<10.1f} "
            f"{entry.get('workload', '')}"
        )

    lines.extend(["", "=" * 58, ""])
    write_output("\n".join(lines))


# ============================================================================
# ARGUMENT PARSING HELPERS
# ============================================================================

def _parse_route_args(args: List[str]) -> dict:
    """Parse route command arguments into a workload spec dict."""
    if not args:
        return None

    spec = {}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--type" and i + 1 < len(args):
            spec["workload_type"] = args[i + 1]
            i += 2
        elif arg == "--qubits" and i + 1 < len(args):
            try:
                spec["qubit_count"] = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif arg == "--depth" and i + 1 < len(args):
            try:
                spec["circuit_depth"] = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif arg == "--threads" and i + 1 < len(args):
            try:
                spec["classical_cpu_threads"] = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif arg == "--memory" and i + 1 < len(args):
            try:
                spec["memory_requirement_mb"] = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif arg == "--priority" and i + 1 < len(args):
            spec["priority"] = args[i + 1]
            i += 2
        elif arg == "--timeout" and i + 1 < len(args):
            try:
                spec["timeout_seconds"] = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        else:
            i += 1

    # Default workload type based on qubits
    if "workload_type" not in spec:
        if spec.get("qubit_count", 0) > 0:
            spec["workload_type"] = "quantum_simulation"
        else:
            spec["workload_type"] = "classical_optimization"

    return spec if spec else None


def _route_usage() -> str:
    """Return usage text for the route command."""
    return """
  USAGE: route [OPTIONS]

  Route a workload to the optimal compute provider.

  OPTIONS:
    --type TYPE       Workload type:
                        quantum_simulation (default if --qubits > 0)
                        classical_optimization (default otherwise)
                        hybrid_computation
                        data_synthesis
    --qubits N        Number of qubits (default 0)
    --depth N         Circuit depth (default 0)
    --threads N       CPU threads needed (default 1)
    --memory N        Memory required in MB (default 100)
    --priority MODE   Optimization priority: cost|speed|accuracy (default cost)
    --timeout N       Timeout in seconds (default 300)

  EXAMPLES:
    route --qubits 10 --priority cost
    route --type quantum_simulation --qubits 5 --depth 100
    route --type classical_optimization --threads 2 --memory 512
    route --qubits 30 --priority accuracy

  RELATED COMMANDS:
    route-options    Show all compatible providers
    route-test       Test routing to a specific provider
    route-history    Show past routing decisions

"""
