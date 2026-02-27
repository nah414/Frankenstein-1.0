# Frankenstein 1.0

**A Physics-Based AI Desktop Assistant for Quantum & Classical Computing**

Frankenstein 1.0 is a complete, terminal-first platform for running quantum simulations, routing workloads across providers, and managing AI-assisted operations with built-in safety controls.

---

## ✅ Project Status

**Production baseline (completed project).**

This repository is maintained as a stable foundation: core capabilities are implemented, command surfaces are documented, and test suites are included for validation and extension.

---

## ⚡ Quick Start

```bash
git clone https://github.com/nah414/Frankenstein-1.0.git
cd Frankenstein-1.0
pip install -r requirements.txt
python launch_terminal.py
```

**Windows Users:** run `RUN_FRANKENSTEIN.bat`

---

## 🚀 Platform Highlights

- **🖥️ Terminal-first UX** with 74+ command workflows and guided help.
- **⚛️ Quantum simulation toolkit** with multi-qubit operations, gate libraries, and Bloch visualization support.
- **🌐 Multi-provider integrations** (IBM, AWS, Azure, Google, IonQ, Rigetti, and additional adapters).
- **🧠 Intelligent routing layer** to select providers by workload constraints (cost, accuracy, qubits, fallback).
- **🤖 FRANK AI assistant mode** with guarded command proposal/execution.
- **🔒 Security controls** including RBAC, permission policies, audit trails, and safety filtering.
- **📊 Adaptation and telemetry** for runtime insight, health monitoring, and optimization recommendations.

---

## 🧭 Typical Workflows

### 1) Quantum circuit workflow
```bash
quantum
qubit 3
h 0
cx 0 1
measure
```

### 2) Provider routing workflow
```bash
providers
route --qubits 30 --priority accuracy
connect ibm_quantum
```

### 3) FRANK assistant workflow
```bash
frank chat
frank help
!run git status
```

---

## 🛡️ Safety Model (FRANK + Terminal Controls)

Frankenstein applies a permission-first execution model:

- **Read-only commands:** can be auto-approved.
- **Mutating commands:** require explicit user confirmation.
- **Destructive commands:** require elevated confirmation phrases.
- **Forbidden patterns:** blocked at policy level.

Supporting modules include permission management, RBAC integration, safety filters, and audit logging.

---

## 🏗️ Repository Layout

```text
Frankenstein-1.0/
├── launch_terminal.py      # Main terminal launcher
├── widget/                 # Terminal UI + visualization surface
├── synthesis/              # Quantum/physics compute and simulation engine
├── integration/            # Provider registry, adapters, credential bridges
├── router/                 # Workload scoring, decisions, fallback logic
├── permissions/            # RBAC, policy checks, audit integration
├── automation/             # Scheduler and automation workflows
├── security/               # Filters, monitoring, protection layers
├── agents/                 # Built-in agents + orchestration framework
├── data/                   # Telemetry, metrics, and event pipelines
└── tests/                  # Unit and integration tests
```

---

## 🧰 System Requirements

- **Python:** 3.10+
- **OS:** Windows 10/11, Linux, or macOS
- **Memory:** 4 GB minimum (8 GB recommended)

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## ✅ Validation

Run tests:

```bash
pytest
```

If you are working on a subsystem, run targeted tests first to shorten feedback loops (for example `pytest tests/unit -q`).

---

## 📚 Documentation Index

- `README_ADAPTATION.md` — adaptation system overview
- `QUICK_START_PERMISSIONS.md` — permission and RBAC quick start
- `DEPLOYMENT_CHECKLIST.md` — deployment and release checks
- `BUILD_NOTES.md` — build and environment notes
- `docs/TOOLSET_INSTALLATION.md` — toolset install flow
- `docs/TOOLSET_AUDIT_REPORT.md` — audit report and findings

---

## 🤝 Contributing

Contributions are welcome, especially in reliability, test coverage, provider integrations, and documentation clarity.

1. Fork the repository
2. Create a feature branch
3. Add or update tests with your change
4. Run validation locally
5. Open a pull request with a clear summary

---

## 📄 License

MIT License. See [LICENSE](LICENSE).
