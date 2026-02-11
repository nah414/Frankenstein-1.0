# Test Phase 3 Step 6 in Monster Terminal

**What to test when you launch Frankenstein 1.0 from your desktop shortcut**

---

## ✅ CHECKLIST - Test These Commands

### Test 1: Verify Commands Appear in Help

```bash
help
```

**Expected:** You should see these new sections:
- `permissions` - Permission management system
- `setup` - Setup wizard for permissions and automation
- `automation` - Automation workflow management
- `scheduler` - Task scheduler management

---

### Test 2: View Detailed Help for Each Command

```bash
help permissions
help setup
help automation
help scheduler
```

**Expected:** Each command shows detailed help text with:
- Description
- Usage examples
- Subcommands
- Options
- Related commands

---

### Test 3: Run Setup Wizard (Default Mode)

```bash
setup --default
```

**Expected Output:**
```
Default configuration applied successfully!

Role: Admin
Automation: Enabled

Automated Workflows:
  ✓ Quantum queue optimization
  ✓ Classical queue optimization
  ✗ Credential expiry checking
  ✓ Resource report generation
  ✓ Provider health monitoring
  ✗ Hardware auto-tuning

Setup complete! Use 'permissions' to view your permissions.
```

---

### Test 4: View Permissions Summary

```bash
permissions
```

**Expected Output:**
```
═══════════════════════════════════════════════════════════════
PERMISSION SUMMARY
═══════════════════════════════════════════════════════════════

Current Role: Admin

PERMISSIONS GRANTED:
  ✓ quantum_job_submit         Submit quantum computing jobs
  ✓ classical_compute_submit   Submit classical compute jobs
  ✓ automation_control         Control automated workflows
  ✓ permission_modify          Modify permission settings
  ✓ provider_connect           Connect to compute providers
  ✓ credential_modify          Modify credentials

PROVIDER ACCESS:
  Quantum Providers: 15 accessible
  Classical Providers: 13 accessible
  Total: 28 providers available

Use 'permissions providers' to see full provider list.
Use 'permissions check <permission>' to verify specific permissions.
```

---

### Test 5: View Accessible Providers

```bash
permissions providers
```

**Expected Output:**
```
═══════════════════════════════════════════════════════════════
ACCESSIBLE PROVIDERS (Admin Role)
═══════════════════════════════════════════════════════════════

QUANTUM PROVIDERS (15):
  • local_simulator
  • ibm_quantum
  • aws_braket
  • azure_quantum
  • google_cirq
  • nvidia_quantum_cloud
  • ionq
  • rigetti
  • quantinuum
  • xanadu
  • dwave
  • iqm
  • quera
  • qiskit_aer
  • cuquantum

CLASSICAL PROVIDERS (13):
  • local_cpu
  • intel
  • amd
  • arm
  • risc_v
  • nvidia_cuda
  • amd_rocm
  • intel_oneapi
  • apple_metal
  • tpu
  • fpga
  • npu
  • local_classical

Total: 28 providers accessible
```

---

### Test 6: Check Specific Permission

```bash
permissions check quantum_job_submit
```

**Expected Output:**
```
Permission check: quantum_job_submit
Role: Admin
Result: ALLOWED ✓
```

---

### Test 7: View Automation Status

```bash
automation
```

**Expected Output:**
```
═══════════════════════════════════════════════════════════════
AUTOMATION STATUS
═══════════════════════════════════════════════════════════════

Automation: Enabled
Scheduler: Not running

WORKFLOWS:
  ✓ quantum_queue          Optimize quantum job queue (enabled)
  ✓ classical_queue        Optimize classical compute queue (enabled)
  ✗ credential_expiry      Check credential expiry (disabled)
  ✓ resource_report        Generate resource reports (enabled)
  ✓ provider_health        Monitor provider health (enabled)
  ✗ hardware_tuning        Auto-tune hardware (disabled)

Use 'automation start' to start automation engine.
Use 'automation run <workflow>' to run a workflow manually.
```

---

### Test 8: Start Automation

```bash
automation start
```

**Expected Output:**
```
Automation started successfully!

4 workflows scheduled:
  • quantum_queue (every 5 minutes)
  • classical_queue (every 5 minutes)
  • resource_report (daily)
  • provider_health (every 15 minutes)

Use 'automation status' to monitor execution.
```

---

### Test 9: View Scheduler Status

```bash
scheduler
```

**Expected Output:**
```
═══════════════════════════════════════════════════════════════
TASK SCHEDULER STATUS
═══════════════════════════════════════════════════════════════

Scheduler: Running ✓
Active Tasks: 4
Total Tasks: 4

Resource Usage:
  CPU: 12%
  RAM: 35%

Safety Limits:
  Max CPU: 80%
  Max RAM: 75%

Use 'scheduler tasks' to view all tasks.
```

---

### Test 10: List Scheduled Tasks

```bash
scheduler tasks
```

**Expected Output:**
```
═══════════════════════════════════════════════════════════════
SCHEDULED TASKS
═══════════════════════════════════════════════════════════════

[1] quantum_queue_task
    Status: running
    Schedule: recurring (every 300 seconds)
    Run Count: 3
    Last Run: 2026-02-10T15:30:00
    Providers: 15 quantum providers

[2] classical_queue_task
    Status: running
    Schedule: recurring (every 300 seconds)
    Run Count: 3
    Last Run: 2026-02-10T15:30:00
    Providers: 13 classical providers

[3] resource_report_task
    Status: pending
    Schedule: daily
    Run Count: 0
    Next Run: 2026-02-11T00:00:00

[4] provider_health_task
    Status: running
    Schedule: recurring (every 900 seconds)
    Run Count: 1
    Last Run: 2026-02-10T15:20:00
    Providers: 28 total providers

Total Tasks: 4 (3 running, 1 pending)
```

---

### Test 11: Run Manual Workflow

```bash
automation run quantum_queue
```

**Expected Output:**
```
Running workflow: optimize_quantum_queue

Checking 15 quantum providers...
Optimizing job queue...

WORKFLOW RESULTS:
  Providers Checked: 15
  Jobs Optimized: 0
  Status: success

Workflow completed successfully!
Execution time: 0.45s
```

---

### Test 12: View Audit Log

```bash
permissions audit 1
```

**Expected Output:**
```
═══════════════════════════════════════════════════════════════
AUDIT LOG (Last 1 Days)
═══════════════════════════════════════════════════════════════

[2026-02-10T15:35:22] Role: Admin
  Action: automation_control
  Result: success
  Details: Started automation workflows

[2026-02-10T15:34:10] Role: Admin
  Action: quantum_job_submit
  Result: allowed
  Provider: ibm_quantum

[2026-02-10T15:30:00] Role: Admin
  Action: permission_check
  Result: success
  Permission: quantum_job_submit

Total entries: 3
Use 'permissions audit <days>' to view more history.
```

---

### Test 13: Change User Role

```bash
permissions set-role User
```

**Expected Output:**
```
Role changed to: User

Updated permissions:
  ✓ quantum_job_submit
  ✓ classical_compute_submit
  ✓ provider_connect
  ✗ automation_control (denied)
  ✗ permission_modify (denied)
  ✗ credential_modify (denied)

Use 'permissions' to view full summary.
```

---

### Test 14: Interactive Setup Wizard

```bash
setup
```

**Expected:** Interactive prompts like:
```
═══════════════════════════════════════════════════════════════
FRANKENSTEIN 1.0 - SETUP WIZARD
═══════════════════════════════════════════════════════════════

This wizard will help you configure permissions and automation.

[1/3] Select Your Role
  1. Admin      - Full access (default)
  2. User       - Job submission only
  3. Agent      - Automation only
  4. ReadOnly   - View only

Your choice (1-4): [1] _
```

---

### Test 15: Stop Automation

```bash
automation stop
```

**Expected Output:**
```
Stopping automation...

Workflows stopped:
  • quantum_queue
  • classical_queue
  • resource_report
  • provider_health

Automation stopped successfully!
Scheduler is no longer running.
```

---

## 🎯 SUCCESS CRITERIA

All 15 tests should work without errors. You should see:

✅ Commands appear in `help` output
✅ Detailed help for each command (`help permissions`, etc.)
✅ `setup --default` creates default config
✅ `permissions` shows role and permissions
✅ `permissions providers` lists all 28 providers
✅ `permissions check` validates permissions
✅ `automation` shows workflow status
✅ `automation start` starts background workflows
✅ `scheduler` shows scheduler status
✅ `scheduler tasks` lists scheduled tasks
✅ `automation run` executes workflows manually
✅ `permissions audit` shows activity log
✅ `permissions set-role` changes user role
✅ `setup` runs interactive wizard
✅ `automation stop` stops workflows

---

## 🐛 TROUBLESHOOTING

**If commands don't appear:**
1. Make sure you launched Frankenstein 1.0 from desktop shortcut
2. Type `help` and scroll through - look for "permissions", "setup", "automation", "scheduler"
3. If still missing, check `C:\Users\adamn\Frankenstein-1.0\widget\terminal.py` was deployed

**If imports fail:**
1. Check modules exist: `ls permissions/` and `ls automation/`
2. Clear cache: `find . -name "__pycache__" -type d -exec rm -rf {} +`
3. Restart Frankenstein

**If help text missing:**
1. Type `help permissions` - should show full help
2. If blank, check lines 3193+ in `widget/terminal.py`

---

## 📝 NOTES

- All commands support tab completion
- Help text is searchable (`help | grep workflow`)
- Audit logs stored in `~/.frankenstein/audit/`
- Config stored in `~/.frankenstein/config/permissions.json`

---

**Ready to test?**

1. Launch Frankenstein 1.0 from desktop
2. Type `help` and verify new commands appear
3. Run through the 15 tests above
4. Enjoy your new permissions & automation system! 🎉

---

*Phase 3 Step 6 - Test Guide - February 10, 2026*
