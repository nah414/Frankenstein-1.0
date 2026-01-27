# Monster Terminal - New Features Test Prompts

## Quick Test Commands (copy/paste into terminal)

### 1. Git Commands
```
git --version
git status
```

### 2. SSH Commands  
```
ssh
scp
ssh-keygen --help
```

### 3. Package Managers
```
pip --version
pip list
npm --version
conda --version
```

### 4. Text Editors
```
notepad
code .
```

### 5. Environment Variables
```
export TEST_VAR=hello
echo $TEST_VAR
printenv TEST_VAR
set TEST_VAR
unset TEST_VAR
printenv TEST_VAR
env
```

### 6. Scripting
```
python --version
python -c "print('Hello from Python!')"
node --version
node -e "console.log('Hello from Node!')"
```

### 7. Help System
```
help
help git
help pip
help export
```

## Expected Results
- Git: Shows version and repo status (or "not a git repo" message)
- SSH: Shows usage info
- Package managers: Show versions
- Text editors: Open applications
- Environment: Variables set/unset correctly
- Scripting: Python/Node execute and show output
- Help: Shows expanded help with new sections
