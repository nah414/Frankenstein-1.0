# Multi-Qubit Bloch Sphere Visualization Guide

## ✅ Feature Status: INSTALLED AND WORKING

The multi-qubit Bloch sphere visualization has been successfully installed.

## How to Use

### Step 1: Launch Frankenstein Terminal
```bash
cd C:\Users\adamn\Frankenstein-1.0
python launch_terminal.py
```

### Step 2: Enter Quantum Mode
```
quantum
```

### Step 3: Create a Multi-Qubit Entangled State
```
qubit 4
h 0
cx 0 1
cx 0 2
cx 0 3
```

### Step 4: Launch Bloch Sphere Visualization
```
bloch
```

**IMPORTANT:** Use `bloch` command, NOT `measure` command!

### Expected Result
- Browser opens automatically
- Shows 4 Bloch spheres in a 2×2 grid
- Top-right panel shows "⚛️ ENTANGLED"
- Schmidt Rank: 2
- Entropy ≈ 1.0 bits
- Individual qubit cards at bottom showing coordinates

## Commands Overview

| Command | Purpose | Shows Multi-Qubit? |
|---------|---------|-------------------|
| `bloch` | Launch 3D visualization | ✅ YES |
| `measure` | Run measurement shots | ❌ NO (just shows counts) |
| `measure 1000` | Measure with N shots | ❌ NO (just shows counts) |
| `statevector` | Show state amplitudes | ❌ NO (terminal output) |

## Verification Test

Try this complete sequence:
```
quantum
qubit 2
h 0
cx 0 1
bloch
```

You should see:
- 2 Bloch spheres side by side
- "⚛️ ENTANGLED" badge in purple panel
- Schmidt Rank: 2
- Entropy: 1.000 bits

## Troubleshooting

### Issue: Browser doesn't open
**Solution:** Manually open the generated file:
```
C:\Users\adamn\.frankenstein\visualizations\bloch_multi_multi.html
```

### Issue: Shows old single-qubit visualization
**Solution:** 
1. Clear cache: Delete `C:\Users\adamn\Frankenstein-1.0\widget\__pycache__`
2. Restart terminal
3. Try again

### Issue: Template shows {{PLACEHOLDERS}}
**Solution:** File sync issue. Run:
```bash
cp C:\Users\adamn\Frankenstein-1.0\widget\bloch_sphere_multi.html C:\Users\adamn\OneDrive\Desktop\Frankenstein_Terminal\widget\
```

## File Locations

**Template:** `C:\Users\adamn\Frankenstein-1.0\widget\bloch_sphere_multi.html`  
**Generated HTML:** `C:\Users\adamn\.frankenstein\visualizations\bloch_multi_multi.html`  
**Code:** `widget/quantum_mode.py` line 1432 `_cmd_bloch()`

## Test Cases

### Test 1: Bell State (2 qubits)
```
quantum
qubit 2
h 0
cx 0 1
bloch
```
Expected: 2 spheres, ENTANGLED, rank 2

### Test 2: GHZ State (4 qubits)
```
quantum
qubit 4
h 0
cx 0 1
cx 0 2
cx 0 3
bloch
```
Expected: 4 spheres in 2×2 grid, ENTANGLED, rank 2

### Test 3: Separable State (3 qubits)
```
quantum
qubit 3
h 0
h 1
h 2
bloch
```
Expected: 3 spheres, SEPARABLE, rank 1

## Advanced Features

- **Drag:** Rotate the sphere group
- **Scroll:** Zoom in/out
- **Double-click:** Reset camera position
- **Auto-rotation:** Gentle rotation when not interacting
- **Pulsing:** Entangled states pulse with glow effect

## Confirmed Working

✅ Multi-qubit visualization launches  
✅ Template variables replaced correctly  
✅ Entanglement detection working  
✅ Schmidt rank calculation accurate  
✅ File generation: 15,880 bytes  
✅ Browser launch command executed  

Last verified: 2026-02-16 16:30 CST
