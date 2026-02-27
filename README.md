# FRANKENSTEIN 1.0

**A Physics-Based AI Desktop Assistant for Quantum & Classical Computing**

Transform your desktop into a powerful quantum-classical computing interface. Frankenstein 1.0 combines real quantum simulation, intelligent workload routing, and automated system adaptation—all through an elegant terminal interface.

---

## ⚡ Quick Start

```bash
git clone https://github.com/nah414/Frankenstein-1.0.git
cd Frankenstein-1.0
pip install -r requirements.txt
python launch_terminal.py
```

**Windows Users**: Simply double-click `RUN_FRANKENSTEIN.bat`

---

## 🎯 What Can It Do?

### Quantum Computing Made Simple
```bash
quantum              # Enter quantum mode
qubit 10             # Create 10 qubits
h 0                  # Apply Hadamard gate
cx 0 1               # Entangle qubits
measure              # See results + 3D visualization
```

### Smart Provider Routing
```bash
route --qubits 30 --priority accuracy    # Find best quantum hardware
providers                                 # See 29+ available providers
connect ibm_quantum                       # Connect with your credentials
```

### Real-Time Adaptation
```bash
adapt-status         # Monitor system performance
adapt-dashboard      # See real-time analytics
adapt-recommend quantum_simulation    # Get AI-powered recommendations
```

### FRANK AI Chat (NEW ✨)
```bash
frank chat           # Enter FRANK AI mode (auto-displays full command guide)
frank help           # Show complete command reference any time
!run git status      # Propose commands — FRANK guards and executes safely
!run rm -rf ./old    # FRANK asks CONFIRM before any destructive operation
```

---

## 🚀 Key Features

- **🖥️ 74+ Terminal Commands** - Full Git Bash experience (navigation, file ops, SSH, scripting)
- **⚛️ Quantum Simulation** - 16-qubit support with 26 quantum gates and 3D Bloch sphere
- **🌐 29 Provider Integrations** - IBM, AWS, Azure, Google, IonQ, Rigetti, and more
- **🧠 Intelligent Routing** - Auto-selects optimal provider based on your workload
- **📊 Real-Time Adaptation** - Learns from your usage and optimizes performance
- **🔒 Security & Permissions** - Role-based access control with audit logging
- **⚙️ Automated Workflows** - 6 background tasks for health monitoring and optimization
- **🤖 FRANK AI Chat** - Phi 3.5 mini 3.8B local LLM with 4-tier permission guard and full terminal oversight

---

## 🎮 Example Workflows

### Run a Quantum Circuit
```bash
$ quantum
>>> qubit 3
>>> h 0          # Superposition
>>> h 1
>>> cx 0 2       # Entanglement
>>> measure      # Auto-opens 3D Bloch sphere!
```

### Route to Best Provider
```bash
$ route --qubits 30 --priority cost
✓ Analyzing 29 providers...
✓ Recommended: ibm_quantum (Free tier, 127 qubits available)
✓ Fallbacks: aws_braket_local, local_cpu
```

### Monitor System Adaptation
```bash
$ adapt-dashboard
================================================================================
FRANKENSTEIN 1.0 - REAL-TIME ADAPTATION DASHBOARD
================================================================================

┌─────────────────────────────────────┐
│  REAL-TIME ADAPTATION STATUS        │
├─────────────────────────────────────┤
│ Monitoring: ACTIVE                  │
│ CPU:        24.3% ✓                 │
│ RAM:        45.1% ✓                 │
│ Safe:       YES                     │
└─────────────────────────────────────┘
```

---

## 📦 What's Inside

```
Frankenstein-1.0/
├── launch_terminal.py    # Start here
├── widget/               # Terminal interface
├── agents/               # AI agents (compute, quantum, crypto)
│   ├── adaptation/       # Real-time learning system
│   └── sauron/           # FRANK AI — Qwen 2.5 7B orchestrator (NEW)
├── router/               # Intelligent workload routing
├── integration/          # 29 provider adapters
├── permissions/          # Access control & automation
├── configs/              # Model and system configuration
└── synthesis/            # Quantum simulation engine
```

---

## 🔧 System Requirements

- **Python**: 3.10 or higher
- **OS**: Windows 10/11 (Linux/Mac compatible)
- **RAM**: 4GB minimum (8GB recommended)
- **Dependencies**: Installed automatically via `requirements.txt`

**Core Libraries**: NumPy, SciPy, Qiskit, QuTiP, Matplotlib

---

## 🌟 Latest Updates

### Phase 4 Day 7: FRANK AI Chat with Permission Guard (COMPLETE ✅)
*Released: February 2026*

Frankenstein now has a local AI brain. FRANK (powered by Qwen 2.5 7B via Ollama) can
converse naturally AND execute all 74+ terminal commands safely through a hard-coded
4-tier permission system:

- **🤖 FRANK AI Chat** - `frank chat` launches full AI mode with command guide on entry
- **🛡️ 4-Tier Permission Guard** - Every command classified before execution:
  - 🟢 **TIER 3** Read-only — auto-executes (`git status`, `ls`, `hardware`, `adapt-*`)
  - 🟡 **TIER 2** Modify — requires `y` approval (`git commit`, `pip install`, `cp`, `mv`)
  - 🔴 **TIER 1** Destructive — requires typing `CONFIRM` (`rm -r`, `git reset --hard`)
  - ⛔ **TIER 0** Forbidden — permanently blocked (`rm -rf /`, `format c:`, fork bombs)
- **`::EXEC::` Auto-Detection** - AI embeds commands in its stream; guard intercepts automatically
- **`!run` Manual Proposals** - You can propose any command directly inside chat
- **`frank help`** - Full command guide with tier labels for every command category
- **Audit Trail** - `!history` shows every proposal: tier, status, timestamp

```bash
frank chat             # Enter FRANK AI (guide auto-displays)
frank help             # Full command reference (outside chat)
!run git log           # Manual command proposal (auto-approved — TIER 3)
!run git push          # Manual command proposal (requires y — TIER 2)
!history               # Session audit log
```

**Test Coverage**: 399/399 tests passing ✅
**Safety**: CPU limit 80%, RAM limit 75% (never exceeded)

---

### Phase 3 Step 7: Real-Time Adaptation (COMPLETE ✅)
*Released: February 2026*

The system now learns from your usage patterns and automatically optimizes:

- **Smart Provider Selection** - Recommends best provider based on your history
- **Performance Tracking** - Monitors latency, throughput, and success rates
- **Auto-Failover** - Switches providers when performance degrades
- **Pattern Learning** - Builds knowledge from every execution
- **7 Terminal Commands** - Full control via `adapt-*` commands

**Test Coverage**: 98/98 tests passing ✅
**Safety**: CPU limit 80%, RAM limit 75% (never exceeded)

---

## 📚 Documentation

- **[Quick Start Guide](docs/QUICKSTART.md)** - Get up and running in 5 minutes
- **[Command Reference](docs/COMMANDS.md)** - All 74+ terminal commands
- **[Provider Setup](docs/PROVIDERS.md)** - Connect to quantum hardware
- **[Adaptation Guide](README_ADAPTATION.md)** - Real-time learning system

**Need Help?** Type `help` in the terminal for interactive guides

---

## 🛤️ Development Roadmap

| Phase | Status | Features |
|-------|--------|----------|
| **Phase 1** | ✅ Complete | Terminal, safety system, resource management |
| **Phase 2** | ✅ Complete | Quantum simulation, Bloch visualization, 26 gates |
| **Phase 3** | ✅ Complete | 29 providers, intelligent routing, permissions, **real-time adaptation** |
| **Phase 4** | 🚧 In Progress | FRANK AI chat, 4-tier permission guard, Eye of Sauron orchestrator |
| **Phase 5** | 🔜 Planned | Advanced ML models, federated learning |

---

## 🎓 Learn More

### Quantum Computing Basics
New to quantum computing? No problem! Our interactive quantum mode includes:
- Built-in tutorials (`help quantum`)
- Pre-built circuits (Bell states, GHZ, QFT)
- Real-time 3D visualization
- Progressive difficulty levels

### Provider Ecosystem
Access real quantum hardware from top providers:
- **IBM Quantum** - Up to 127 qubits
- **AWS Braket** - IonQ, Rigetti, and simulators
- **Azure Quantum** - IonQ, Quantinuum integration
- **Google Quantum AI** - Experimental access
- **29+ total providers** - Including local simulators

---

## 🤝 Contributing

We welcome contributions! Whether you're fixing bugs, adding features, or improving documentation:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

---

## 🙏 Acknowledgments

Built with:
- **QuTiP** - Quantum Toolbox in Python
- **Qiskit** - IBM's quantum computing framework
- **NumPy/SciPy** - Scientific computing foundations
- **CustomTkinter** - Modern terminal interface

Special thanks to the quantum computing community for making this possible.

---

## 📬 Contact & Support

- **Issues**: [GitHub Issues](https://github.com/nah414/Frankenstein-1.0/issues)
- **Discussions**: [GitHub Discussions](https://github.com/nah414/Frankenstein-1.0/discussions)
- **Terminal Help**: Type `help` or `frank quote` for guidance

---

**🧪 IT'S ALIVE!** Start your quantum computing journey today.

```bash
python launch_terminal.py
```
