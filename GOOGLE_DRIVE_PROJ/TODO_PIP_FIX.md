# TODO: Fix GDS pip to use `python3 -m pip` instead of `pip`

## Problem
Currently `GDS pip install` directly calls `pip` command, which fails when pip executable is not available in PATH.

**Current implementation** (pip_command.py line 402):
```python
pip_cmd_parts = ["pip"] + "{pip_command}".split()
```

## Root Cause
- `make altinstall` may not create pip3 executable in bin/
- pip module exists in site-packages but no executable wrapper
- GDS pip fails even though `python3 -m pip` would work

## Solution
Change pip execution to use `python3 -m pip` instead of direct `pip` command:

```python
pip_cmd_parts = ["python3", "-m", "pip"] + "{pip_command}".split()
```

## Benefits
1. Works even when pip3 executable is missing
2. Uses the correct Python interpreter's pip
3. More reliable and portable
4. Consistent with Python best practices

## Files to Modify
- `/Users/wukunhuan/.local/bin/GOOGLE_DRIVE_PROJ/modules/commands/pip_command.py`
  - Line 402: Change `["pip"]` to `["python3", "-m", "pip"]`

## Testing
After fix:
1. Test `GDS pip install requests` with fresh Python installation
2. Test `GDS pip list` (should continue to work)
3. Test `GDS pip uninstall <package>`

## Related Issues
- pyenv install now skips pip3 verification to avoid window crashes
- This fix will make pip fully functional even without pip3 executable

