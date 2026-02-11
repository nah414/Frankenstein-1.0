# Quick Start: Permissions & Automation

**Phase 3 Step 6 - New Commands in Monster Terminal**

---

## 🚀 QUICK START (30 seconds)

```bash
# Launch Frankenstein 1.0 from your desktop shortcut
# In Monster Terminal, type:

setup --default         # Apply default settings (Admin role, automation on)
automation start        # Start automated workflows
permissions             # View your permissions
help automation         # See full automation help
```

---

## 📋 NEW COMMANDS (4 Total)

### 1. `permissions` - Manage Access Control

```bash
permissions                          # Show current role & permissions
permissions set-role Admin           # Change role (Admin/User/Agent/ReadOnly)
permissions check quantum_job_submit # Check specific permission
permissions providers                # Show accessible providers
permissions audit 7                  # Show 7-day audit log
```

### 2. `setup` - Configuration Wizard

```bash
setup              # Interactive setup (choose role, workflows)
setup --default    # Quick default (Admin, all workflows enabled)
```

### 3. `automation` - Workflow Management

```bash
automation                        # Show automation status
automation start                  # Start background workflows
automation stop                   # Stop all workflows
automation run quantum_queue      # Manually run optimization
automation consent quantum_queue  # Allow job termination
```

### 4. `scheduler` - Task Management

```bash
scheduler              # Show scheduler status
scheduler tasks        # List all scheduled tasks
scheduler pause TASK   # Pause a specific task
scheduler resume TASK  # Resume a paused task
```

---

## 🔑 ROLES EXPLAINED

| Role | What You Can Do |
|------|----------------|
| **Admin** | Everything - full access to all 28 providers, automation control |
| **User** | Submit quantum & classical jobs, connect to providers |
| **Agent** | Automated workflows only, no manual job submission |
| **ReadOnly** | View-only access, cannot submit jobs |

---

## 🤖 AUTOMATED WORKFLOWS (6 Total)

| Workflow | Runs | What It Does |
|----------|------|--------------|
| `quantum_queue` | Every 5 min | Optimizes quantum job queue |
| `classical_queue` | Every 5 min | Optimizes classical compute queue |
| `credential_expiry` | Daily | Checks for expiring credentials |
| `resource_report` | Daily | Generates usage reports |
| `provider_health` | Every 15 min | Monitors provider status |
| `hardware_tuning` | Hourly | Auto-tunes hardware settings |

---

## 💡 COMMON TASKS

### First-Time Setup
```bash
setup --default
automation start
permissions
```

### Check Your Access
```bash
permissions                    # See your role
permissions providers          # See accessible providers
permissions check quantum_job_submit  # Check specific permission
```

### View Activity
```bash
permissions audit 7            # Last 7 days of activity
automation status              # Current workflow status
scheduler tasks                # Scheduled tasks
```

### Change Settings
```bash
permissions set-role User      # Change to User role
automation stop                # Stop all workflows
automation run quantum_queue   # Run single workflow
```

---

## 🔒 SAFETY FEATURES

- **CPU Limit:** 80% maximum (workflows auto-pause if exceeded)
- **RAM Limit:** 75% maximum (workflows auto-pause if exceeded)
- **Audit Log:** All actions logged for security
- **Consent Required:** User approval needed for job termination

---

## 📖 FULL HELP

```bash
help permissions    # Full permission command help
help setup          # Setup wizard help
help automation     # Automation workflow help
help scheduler      # Task scheduler help
```

---

## 🎯 EXAMPLE SESSION

```bash
# Launch Frankenstein 1.0 from desktop

# 1. Initial setup
setup --default
# → Sets Admin role, enables automation

# 2. Start automation
automation start
# → Starts 6 background workflows

# 3. Check status
permissions
# → Shows: Role=Admin, 28 providers accessible

automation status
# → Shows: 6 workflows running

# 4. Submit a quantum job
permissions check quantum_job_submit
# → ALLOWED ✓

connect ibm_quantum
# → Connected to IBM Quantum

# 5. View activity
permissions audit 7
# → Shows last 7 days of actions

scheduler tasks
# → Lists all scheduled workflows
```

---

## ❓ TROUBLESHOOTING

**Q: Commands not showing up?**
A: Make sure you launched Frankenstein 1.0 from the desktop shortcut. Type `help` to see all commands.

**Q: Automation not starting?**
A: Check `permissions` - automation requires Admin or Agent role.

**Q: Where are logs stored?**
A: Audit logs in `~/.frankenstein/audit/`

**Q: How to reset everything?**
A: Run `permissions reset` then `setup --default`

---

## 📊 STATS

- **Roles:** 4 (Admin, User, Agent, ReadOnly)
- **Permissions:** 6 types
- **Providers:** 28 (15 quantum + 13 classical)
- **Workflows:** 6 automated
- **Commands:** 4 new terminal commands
- **Tests:** 346 (all passing ✅)

---

**Need More Help?**

Run `help <command>` for detailed help on any command:
- `help permissions`
- `help setup`
- `help automation`
- `help scheduler`

---

*Phase 3 Step 6 - Frankenstein 1.0 Team - February 10, 2026*
