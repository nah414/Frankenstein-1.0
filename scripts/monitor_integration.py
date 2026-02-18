#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Resource Monitor
Phase 3.5: Real-time CPU/RAM monitor during toolset integration.

Usage:
    python scripts/monitor_integration.py               # Live monitor (5 min default)
    python scripts/monitor_integration.py --duration 60  # Live monitor for 60 seconds
    python scripts/monitor_integration.py --snapshot      # One-shot status dump
    python scripts/monitor_integration.py --load-test     # Load all toolsets and monitor impact

Alerts if safety limits are exceeded (CPU 80%, RAM 75%).
Tracks violations and prints a summary on exit.
"""

import argparse
import sys
import os
import time

import psutil
from colorama import Fore, Style, init

# Ensure project root is on the path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

init(autoreset=True)

# ── Safety limits (must match libs/local_toolsets.py) ────────────────────────
CPU_LIMIT = 80   # Percent
RAM_LIMIT = 75   # Percent


# ── Helpers ──────────────────────────────────────────────────────────────────

def _bar(percent: float, width: int = 30) -> str:
    """Render a simple ASCII bar: [######........................]"""
    filled = int(width * percent / 100)
    empty = width - filled
    return f"[{'#' * filled}{'.' * empty}]"


def _color(value: float, limit: float) -> str:
    """Pick a color based on how close *value* is to *limit*."""
    if value > limit:
        return Fore.RED
    elif value > limit * 0.85:
        return Fore.YELLOW
    return Fore.GREEN


def _get_toolset_status():
    """Try to load the toolset manager and return its status dict."""
    try:
        from libs.local_toolsets import get_toolset_manager
        mgr = get_toolset_manager()
        return mgr.get_loaded_status(), mgr.get_total_loaded_ram_mb()
    except Exception:
        return None, 0


# ── Snapshot mode ────────────────────────────────────────────────────────────

def snapshot():
    """One-shot status dump: system resources + toolset status."""
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.5)

    print(f"{Fore.CYAN}{'=' * 65}")
    print(f"{Fore.CYAN}  FRANKENSTEIN 1.0 - Resource Snapshot")
    print(f"{Fore.CYAN}{'=' * 65}")
    print()

    cpu_c = _color(cpu, CPU_LIMIT)
    ram_c = _color(mem.percent, RAM_LIMIT)

    print(f"  CPU:  {cpu_c}{cpu:5.1f}%{Style.RESET_ALL}  {_bar(cpu)}  limit {CPU_LIMIT}%")
    print(f"  RAM:  {ram_c}{mem.percent:5.1f}%{Style.RESET_ALL}  {_bar(mem.percent)}  limit {RAM_LIMIT}%")
    print(f"        {mem.used // (1024**2):,} MB / {mem.total // (1024**2):,} MB")
    print()

    # Toolset status
    status, loaded_ram = _get_toolset_status()
    if status:
        print(f"{Fore.CYAN}  Toolset Status")
        print(f"  {'-' * 55}")
        for key, info in status.items():
            loaded_tag = f"{Fore.GREEN}LOADED{Style.RESET_ALL}" if info["loaded"] else f"{Fore.WHITE}idle{Style.RESET_ALL}"
            ram_str = f"{info['ram_mb']} MB" if info["loaded"] else "-"
            src = "src" if info.get("source_available") else "   "
            print(f"    {key:18s}  {loaded_tag:20s}  RAM: {ram_str:>8s}  [{src}]")
        print(f"\n    Estimated toolset RAM: {loaded_ram} MB")
    else:
        print(f"  {Fore.YELLOW}(toolset manager not available){Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}{'=' * 65}")


# ── Live monitor mode ───────────────────────────────────────────────────────

def monitor_resources(duration_seconds: int = 300):
    """Live resource monitor with violation tracking."""
    print(f"{Fore.CYAN}{'=' * 65}")
    print(f"{Fore.CYAN}  FRANKENSTEIN 1.0 - Live Resource Monitor")
    print(f"{Fore.CYAN}  CPU Limit: {CPU_LIMIT}%  |  RAM Limit: {RAM_LIMIT}%")
    print(f"{Fore.CYAN}  Duration:  {duration_seconds}s  |  Press Ctrl+C to stop")
    print(f"{Fore.CYAN}{'=' * 65}\n")

    violations = []
    samples = []
    start_time = time.time()

    try:
        while (time.time() - start_time) < duration_seconds:
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            ram = mem.percent

            cpu_c = _color(cpu, CPU_LIMIT)
            ram_c = _color(ram, RAM_LIMIT)
            elapsed = time.time() - start_time

            # Inline status (overwrite same line)
            line = (
                f"  {Fore.WHITE}t={elapsed:6.0f}s  "
                f"{cpu_c}CPU: {cpu:5.1f}%{Style.RESET_ALL}  "
                f"{ram_c}RAM: {ram:5.1f}% "
                f"({mem.used // (1024**2):,}/{mem.total // (1024**2):,} MB)"
                f"{Style.RESET_ALL}"
            )
            print(f"\r{line}", end="", flush=True)

            samples.append({"t": elapsed, "cpu": cpu, "ram": ram})

            # Track violations
            if cpu > CPU_LIMIT or ram > RAM_LIMIT:
                violations.append({"time": elapsed, "cpu": cpu, "ram": ram})
                # Print violation on new line so it's visible
                parts = []
                if cpu > CPU_LIMIT:
                    parts.append(f"CPU {cpu:.1f}%")
                if ram > RAM_LIMIT:
                    parts.append(f"RAM {ram:.1f}%")
                print(f"\n  {Fore.RED}! VIOLATION at t={elapsed:.0f}s: {', '.join(parts)}{Style.RESET_ALL}", end="")

    except KeyboardInterrupt:
        print(f"\n\n  {Fore.YELLOW}Monitoring stopped by user{Style.RESET_ALL}")

    # ── Summary ──────────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    print(f"\n\n{Fore.CYAN}{'=' * 65}")
    print(f"{Fore.CYAN}  SUMMARY")
    print(f"{Fore.CYAN}{'=' * 65}")
    print(f"  Duration:    {elapsed:.1f}s ({len(samples)} samples)")

    if samples:
        cpus = [s["cpu"] for s in samples]
        rams = [s["ram"] for s in samples]
        print(f"  CPU avg:     {sum(cpus) / len(cpus):.1f}%  "
              f"(min {min(cpus):.1f}%, max {max(cpus):.1f}%)")
        print(f"  RAM avg:     {sum(rams) / len(rams):.1f}%  "
              f"(min {min(rams):.1f}%, max {max(rams):.1f}%)")

    print(f"  Violations:  {len(violations)}")

    if violations:
        print(f"\n  {Fore.RED}LIMIT VIOLATIONS:{Style.RESET_ALL}")
        for v in violations[:10]:
            cpu_flag = f" CPU={v['cpu']:.1f}%" if v["cpu"] > CPU_LIMIT else ""
            ram_flag = f" RAM={v['ram']:.1f}%" if v["ram"] > RAM_LIMIT else ""
            print(f"    t={v['time']:6.1f}s:{cpu_flag}{ram_flag}")
        if len(violations) > 10:
            print(f"    ... and {len(violations) - 10} more")
    else:
        print(f"\n  {Fore.GREEN}No violations - all resources within limits.{Style.RESET_ALL}")

    # Toolset status at end
    status, loaded_ram = _get_toolset_status()
    if status:
        loaded = [k for k, v in status.items() if v["loaded"]]
        if loaded:
            print(f"\n  Toolsets loaded at exit: {', '.join(loaded)} ({loaded_ram} MB)")

    print(f"{Fore.CYAN}{'=' * 65}")


# ── Load-test mode ──────────────────────────────────────────────────────────

def load_test():
    """Load each toolset one by one and show the resource impact."""
    import warnings

    print(f"{Fore.CYAN}{'=' * 65}")
    print(f"{Fore.CYAN}  FRANKENSTEIN 1.0 - Toolset Load Test")
    print(f"{Fore.CYAN}{'=' * 65}\n")

    try:
        from libs.local_toolsets import get_toolset_manager
    except ImportError:
        print(f"  {Fore.RED}ERROR: libs.local_toolsets not importable{Style.RESET_ALL}")
        sys.exit(1)

    mgr = get_toolset_manager()

    toolsets_to_load = [
        ("numpy", "load_numpy"),
        ("scipy", "load_scipy"),
        ("qutip", "load_qutip"),
        ("qiskit", "load_qiskit"),
        ("qencrypt", "load_qencrypt"),
    ]

    print(f"  {'Toolset':18s}  {'Status':10s}  {'RAM Before':>12s}  {'RAM After':>12s}  {'Delta':>8s}  {'Version'}")
    print(f"  {'-' * 80}")

    for key, loader_name in toolsets_to_load:
        mem_before = psutil.virtual_memory().used // (1024**2)

        try:
            from libs import local_toolsets
            loader = getattr(local_toolsets, loader_name)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                mod = loader()

            mem_after = psutil.virtual_memory().used // (1024**2)
            delta = mem_after - mem_before
            version = getattr(mod, "__version__", "?") if mod else "-"
            status = f"{Fore.GREEN}OK{Style.RESET_ALL}" if mod else f"{Fore.RED}BLOCKED{Style.RESET_ALL}"

            print(
                f"  {key:18s}  {status:20s}  {mem_before:>8,} MB  {mem_after:>8,} MB  "
                f"{'+' if delta >= 0 else ''}{delta:>5} MB  {version}"
            )
        except Exception as e:
            mem_after = psutil.virtual_memory().used // (1024**2)
            print(f"  {key:18s}  {Fore.RED}ERROR{Style.RESET_ALL}       {mem_before:>8,} MB  {mem_after:>8,} MB          {e}")

    # Final status
    print()
    mem = psutil.virtual_memory()
    ram_c = _color(mem.percent, RAM_LIMIT)
    print(f"  Final RAM: {ram_c}{mem.percent:.1f}%{Style.RESET_ALL}  "
          f"({mem.used // (1024**2):,} / {mem.total // (1024**2):,} MB)")
    print(f"  Toolset estimated total: {mgr.get_total_loaded_ram_mb()} MB")

    cpu = psutil.cpu_percent(interval=0.5)
    cpu_c = _color(cpu, CPU_LIMIT)
    print(f"  CPU: {cpu_c}{cpu:.1f}%{Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}{'=' * 65}")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="FRANKENSTEIN 1.0 - Phase 3.5 Resource Monitor",
    )
    parser.add_argument(
        "--duration", type=int, default=300,
        help="Live monitor duration in seconds (default 300)",
    )
    parser.add_argument(
        "--snapshot", action="store_true",
        help="One-shot resource and toolset status dump",
    )
    parser.add_argument(
        "--load-test", action="store_true", dest="load_test",
        help="Load each toolset and show resource impact",
    )
    args = parser.parse_args()

    if args.snapshot:
        snapshot()
    elif args.load_test:
        load_test()
    else:
        monitor_resources(args.duration)


if __name__ == "__main__":
    main()
