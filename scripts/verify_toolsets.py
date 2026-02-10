#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Toolset Verification Script
Phase 3.5: Validates all local toolsets are installed and functional.

Usage:
    python scripts/verify_toolsets.py

Checks:
    1. Each toolset is importable with correct version
    2. Integration layer loads and manages toolsets
    3. Agents instantiate without triggering toolset loads
    4. RAM/CPU safety limits are in place
    5. Key API functions are accessible
"""

import sys
import os
import time

# Ensure project root is on the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"
SKIP = "[SKIP]"

results = []


def check(name: str, condition: bool, detail: str = ""):
    status = PASS if condition else FAIL
    results.append((status, name, detail))
    tag = f"  {status} {name}"
    if detail:
        tag += f"  ({detail})"
    print(tag)
    return condition


def warn(name: str, detail: str = ""):
    results.append((WARN, name, detail))
    tag = f"  {WARN} {name}"
    if detail:
        tag += f"  ({detail})"
    print(tag)


def skip(name: str, detail: str = ""):
    results.append((SKIP, name, detail))
    tag = f"  {SKIP} {name}"
    if detail:
        tag += f"  ({detail})"
    print(tag)


def main():
    print("=" * 65)
    print("  FRANKENSTEIN 1.0 — Phase 3.5 Toolset Verification")
    print("=" * 65)
    print()

    # ── Section 1: Direct imports ────────────────────────────────────
    print("1. Toolset Imports")
    print("-" * 50)

    # numpy
    try:
        import numpy as np
        check("numpy import", True, f"v{np.__version__}")
    except ImportError as e:
        check("numpy import", False, str(e))

    # scipy
    try:
        import scipy
        check("scipy import", True, f"v{scipy.__version__}")
    except ImportError as e:
        check("scipy import", False, str(e))

    # qutip
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import qutip
        check("qutip import", True, f"v{qutip.__version__}")
    except ImportError as e:
        check("qutip import", False, str(e))

    # qiskit
    try:
        import qiskit
        check("qiskit import", True, f"v{qiskit.__version__}")
    except ImportError as e:
        check("qiskit import", False, str(e))

    # qencrypt_local
    try:
        from qencrypt_local import encrypt_text, decrypt_text
        check("qencrypt_local import", True, "encrypt_text, decrypt_text")
    except ImportError as e:
        check("qencrypt_local import", False, str(e))

    print()

    # ── Section 2: Integration layer ─────────────────────────────────
    print("2. Integration Layer (libs/local_toolsets.py)")
    print("-" * 50)

    try:
        from libs.local_toolsets import (
            get_toolset_manager,
            load_numpy, load_scipy, load_qutip, load_qiskit, load_qencrypt,
            RAM_MAX_PERCENT, CPU_MAX_PERCENT,
        )
        check("Integration layer import", True)
    except ImportError as e:
        check("Integration layer import", False, str(e))
        print("\n  Cannot proceed — integration layer missing.\n")
        _print_summary()
        return

    # Singleton
    mgr = get_toolset_manager()
    check("Manager singleton", mgr is not None)

    # RAM/CPU limits
    check("RAM limit set", RAM_MAX_PERCENT == 75, f"{RAM_MAX_PERCENT}%")
    check("CPU limit set", CPU_MAX_PERCENT == 80, f"{CPU_MAX_PERCENT}%")

    # All 5 toolsets registered
    expected = {"numpy", "scipy", "qutip", "qiskit", "qencrypt"}
    actual = set(mgr.toolsets.keys())
    check("All 5 toolsets registered", expected == actual, f"{sorted(actual)}")

    # None loaded at init
    status = mgr.get_loaded_status()
    none_loaded = all(not s["loaded"] for s in status.values())
    # Some may already be loaded if numpy was imported above — that's fine
    if not none_loaded:
        loaded_names = [k for k, s in status.items() if s["loaded"]]
        warn("Toolsets pre-loaded (expected from imports above)", ", ".join(loaded_names))
    else:
        check("No toolsets loaded at init", True)

    # Source discovery
    sources_found = [k for k, s in status.items() if s["source_available"]]
    check("Local source trees discovered", len(sources_found) == 5,
          f"{len(sources_found)}/5: {', '.join(sources_found)}")

    # System resources
    res = mgr.get_system_resources()
    check("System resource snapshot", "ram_used_mb" in res and "cpu_percent" in res,
          f"RAM: {res['ram_used_mb']}/{res['ram_total_mb']} MB ({res['ram_percent']:.1f}%)")

    print()

    # ── Section 3: Toolset loading via integration layer ─────────────
    print("3. Toolset Loading (via integration layer)")
    print("-" * 50)

    np_mod = load_numpy()
    check("load_numpy()", np_mod is not None, f"v{getattr(np_mod, '__version__', '?')}")

    sp_mod = load_scipy()
    check("load_scipy()", sp_mod is not None, f"v{getattr(sp_mod, '__version__', '?')}")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        qt_mod = load_qutip()
    check("load_qutip()", qt_mod is not None, f"v{getattr(qt_mod, '__version__', '?')}")

    qk_mod = load_qiskit()
    check("load_qiskit()", qk_mod is not None, f"v{getattr(qk_mod, '__version__', '?')}")

    qe_mod = load_qencrypt()
    check("load_qencrypt()", qe_mod is not None,
          f"has encrypt_text={hasattr(qe_mod, 'encrypt_text')}")

    total_ram = mgr.get_total_loaded_ram_mb()
    check("Total loaded RAM estimate", total_ram > 0, f"{total_ram} MB")

    print()

    # ── Section 4: Agent instantiation (no toolset load) ─────────────
    print("4. Agent Instantiation (lazy — no toolset load at init)")
    print("-" * 50)

    try:
        from agents.builtin.quantum_dynamics_agent import QuantumDynamicsAgent
        agent = QuantumDynamicsAgent()
        check("QuantumDynamicsAgent", agent._qutip is None,
              f"name={agent.name}, _qutip=None (lazy)")
    except Exception as e:
        check("QuantumDynamicsAgent", False, str(e))

    try:
        from agents.builtin.quantum_hardware_agent import QuantumHardwareAgent
        agent = QuantumHardwareAgent()
        check("QuantumHardwareAgent", agent._qiskit is None,
              f"name={agent.name}, _qiskit=None (lazy)")
    except Exception as e:
        check("QuantumHardwareAgent", False, str(e))

    try:
        from agents.builtin.quantum_crypto_agent import QuantumCryptoAgent
        agent = QuantumCryptoAgent()
        check("QuantumCryptoAgent", agent._qencrypt is None,
              f"name={agent.name}, _qencrypt=None (lazy)")
    except Exception as e:
        check("QuantumCryptoAgent", False, str(e))

    try:
        from agents.builtin.numerical_computing_agent import NumericalComputingAgent
        agent = NumericalComputingAgent()
        check("NumericalComputingAgent", agent._np is None,
              f"name={agent.name}, _np=None (lazy)")
    except Exception as e:
        check("NumericalComputingAgent", False, str(e))

    print()

    # ── Section 5: Key API smoke tests ───────────────────────────────
    print("5. Key API Smoke Tests")
    print("-" * 50)

    import numpy as np_test

    # numpy: array creation + linalg
    try:
        A = np_test.array([[1, 2], [3, 4]])
        det = np_test.linalg.det(A)
        check("numpy linalg.det", abs(det - (-2.0)) < 1e-10, f"det([[1,2],[3,4]])={det}")
    except Exception as e:
        check("numpy linalg.det", False, str(e))

    # scipy: matrix exponential
    try:
        from scipy.linalg import expm
        I = np_test.eye(2)
        result = expm(I * 0)
        check("scipy linalg.expm", np_test.allclose(result, I), "expm(0) = I")
    except Exception as e:
        check("scipy linalg.expm", False, str(e))

    # qutip: quantum object + sigmax
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import qutip as qt_test
        sx = qt_test.sigmax()
        check("qutip sigmax()", sx.shape == (2, 2), f"shape={sx.shape}")
    except Exception as e:
        check("qutip sigmax()", False, str(e))

    # qiskit: QuantumCircuit
    try:
        import qiskit as qk_test
        qc = qk_test.QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        check("qiskit QuantumCircuit", qc.num_qubits == 2 and qc.size() == 2,
              f"Bell circuit: {qc.num_qubits}q, {qc.size()} gates")
    except Exception as e:
        check("qiskit QuantumCircuit", False, str(e))

    # qencrypt: encrypt/decrypt round-trip
    try:
        from qencrypt_local import encrypt_text as enc, decrypt_text as dec
        pkg = enc("test", "pass", entropy_source="local")
        plain = dec(pkg, "pass")
        check("qencrypt round-trip", plain == "test", "encrypt->decrypt OK")
    except Exception as e:
        check("qencrypt round-trip", False, str(e))

    print()

    # ── Section 6: Synthesis engine integration ──────────────────────
    print("6. Synthesis Engine Integration")
    print("-" * 50)

    try:
        from synthesis.engine import (
            SynthesisEngine, _ensure_scipy, SCIPY_AVAILABLE,
            _sp_linalg, _solve_ivp, np as engine_np,
        )
        check("synthesis/engine.py imports", True, f"numpy via integration layer")
        check("Engine numpy available", engine_np is not None, f"v{engine_np.__version__}")

        _ensure_scipy()
        from synthesis.engine import SCIPY_AVAILABLE as sc_avail
        check("Engine scipy available", sc_avail, f"_sp_linalg={_sp_linalg is not None}")

        # Test actual computation
        se = SynthesisEngine(auto_visualize=False)
        se.reset(1)
        se.h(0)
        probs = se.get_probabilities()
        h_correct = abs(probs.get("0", 0) - 0.5) < 0.01
        check("Engine Hadamard gate", h_correct, f"P(0)={probs.get('0', 0):.4f}")

    except Exception as e:
        check("Synthesis engine integration", False, str(e))

    print()

    _print_summary()


def _print_summary():
    print("=" * 65)
    passed = sum(1 for s, _, _ in results if s == PASS)
    failed = sum(1 for s, _, _ in results if s == FAIL)
    warned = sum(1 for s, _, _ in results if s == WARN)
    skipped = sum(1 for s, _, _ in results if s == SKIP)
    total = len(results)

    print(f"  Results: {passed} passed, {failed} failed, {warned} warnings, {skipped} skipped")
    print(f"  Total:   {total} checks")

    if failed == 0:
        print()
        print("  ALL CHECKS PASSED — Phase 3.5 toolsets are fully operational.")
    else:
        print()
        print("  FAILURES DETECTED:")
        for status, name, detail in results:
            if status == FAIL:
                print(f"    {name}: {detail}")

    print("=" * 65)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
