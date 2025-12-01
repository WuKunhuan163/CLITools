# GDS Shell Installation Status

## ✅ Successfully Installed Shells

### 1. Zsh (Z Shell) 5.9
- **Binary Path**: `@/shell/zsh-install/bin/zsh`
- **Full Path**: `/content/drive/MyDrive/REMOTE_ENV/shell/zsh-install/bin/zsh`
- **Status**: ✅ Installed and tested
- **Usage**: `GDS @/shell/zsh-install/bin/zsh -c 'command'`
- **Test Result**: Working, but `@` placeholder in quoted strings is not expanded
- **Code Translation**: ⚠️ **REQUIRED** - Need to map `zsh -c` to full binary path

### 2. Tcsh (TENEX C Shell) 6.24.13
- **Binary Path**: `@/shell/tcsh-install/bin/tcsh`
- **Full Path**: `/content/drive/MyDrive/REMOTE_ENV/shell/tcsh-install/bin/tcsh`
- **Status**: ✅ Installed and tested
- **Usage**: `GDS @/shell/tcsh-install/bin/tcsh -c 'command'`
- **Test Result**: Working, but `@` placeholder in quoted strings is not expanded
- **Code Translation**: ⚠️ **REQUIRED** - Need to map `tcsh -c` to full binary path

---

## 🔄 In Progress

### 3. Fish (Friendly Interactive Shell) 3.7.0
- **Target Binary Path**: `@/shell/fish-install/bin/fish`
- **Target Full Path**: `/content/drive/MyDrive/REMOTE_ENV/shell/fish-install/bin/fish`
- **Status**: ⏳ Installation interrupted (remote session crash)
- **Progress**: Download step in progress
- **Next Steps**: 
  1. Complete download
  2. Extract and build
  3. Install to `@/shell/fish-install`
  4. Add execute permissions
- **Code Translation**: ⚠️ **REQUIRED** - Need to map `fish -c` to full binary path

---

## 🔧 System-Provided Shells (Already Available)

### 4. Bash (Bourne Again Shell)
- **Binary Path**: `/bin/bash`
- **Status**: ✅ System default, always available
- **Usage**: `GDS bash -c 'command'`
- **Test Result**: ✅ Working perfectly, `@` and `~` placeholders expand correctly
- **Code Translation**: ✅ Already implemented in GDS

### 5. Dash (Debian Almquist Shell)
- **Binary Path**: `/usr/bin/dash`
- **Status**: ✅ System provided
- **Usage**: `GDS dash -c 'command'`
- **Test Result**: Not yet tested
- **Code Translation**: ⚠️ **REQUIRED** - Need to add `dash -c` handler

### 6. Sh (Bourne Shell / POSIX Shell)
- **Binary Path**: `/bin/sh` (usually symlink to dash or bash)
- **Status**: ✅ System provided
- **Usage**: `GDS sh -c 'command'`
- **Test Result**: Not yet tested
- **Code Translation**: ⚠️ **REQUIRED** - Need to add `sh -c` handler

---

## ❌ Failed Installation Attempts

### 7. Mksh (MirBSD Korn Shell)
- **Target Binary Path**: `@/shell/mksh-install/bin/mksh`
- **Status**: ❌ Download failed (connection timeout to www.mirbsd.org)
- **Issue**: Network connectivity problem
- **Retry Strategy**: Try alternative download source or manual upload

---

## 📋 Shells Not Yet Attempted

### 8. Ksh (KornShell)
- **Description**: Traditional Unix shell with scripting features
- **Availability**: Needs installation
- **Priority**: Medium
- **Code Translation**: ⚠️ Will require mapping `ksh -c` to binary path

### 9. Ash (Almquist Shell)
- **Description**: Lightweight Bourne shell variant
- **Availability**: May be system-provided or needs installation
- **Priority**: Low
- **Code Translation**: ⚠️ Will require mapping `ash -c` to binary path

### 10. Elvish
- **Description**: Modern shell with advanced features
- **Availability**: Needs installation (requires Go compiler)
- **Priority**: Low
- **Complexity**: High (requires Go toolchain)

### 11. Nushell (Nu)
- **Description**: Modern structured data shell
- **Availability**: Needs installation (requires Rust compiler)
- **Priority**: Low
- **Complexity**: High (requires Rust toolchain)

---

## 🔧 Code Translation Requirements

### What is Code Translation?

When a user executes a command like:
```bash
GDS zsh -c 'echo test'
```

GDS needs to:
1. **Detect the wrapper pattern**: Recognize `zsh -c` as a shell invocation
2. **Map to binary path**: Translate `zsh` to `@/shell/zsh-install/bin/zsh`
3. **Preserve command structure**: Keep `-c 'echo test'` intact
4. **Expand placeholders**: Convert `@` and `~` in arguments to full paths

### Current Implementation Status

#### ✅ Implemented:
- `bash -c` → Uses system `/bin/bash`
- Full path detection: `@/shell/xxx/bin/shell -c` → Automatically expands `@`

#### ⚠️ **REQUIRED** (Not Yet Implemented):
- `zsh -c` → Should map to `@/shell/zsh-install/bin/zsh -c`
- `tcsh -c` → Should map to `@/shell/tcsh-install/bin/tcsh -c`
- `fish -c` → Should map to `@/shell/fish-install/bin/fish -c`
- `dash -c` → Should map to `/usr/bin/dash -c`
- `sh -c` → Should map to `/bin/sh -c`
- `ksh -c` → Should map to `@/shell/ksh-install/bin/ksh -c` (when installed)

### Implementation Location

The code translation logic should be added to:
- **File**: `GOOGLE_DRIVE_PROJ/google_drive_shell.py`
- **Function**: Around line 2300-2400 in the shell command handler
- **Current Logic**: Already detects `bash -c` patterns
- **Enhancement Needed**: Add a mapping dictionary for all custom-installed shells

### Proposed Implementation

```python
# Shell binary mapping (for custom-installed shells)
SHELL_BINARY_MAP = {
    'zsh': '@/shell/zsh-install/bin/zsh',
    'tcsh': '@/shell/tcsh-install/bin/tcsh',
    'fish': '@/shell/fish-install/bin/fish',
    'ksh': '@/shell/ksh-install/bin/ksh',
    'mksh': '@/shell/mksh-install/bin/mksh',
    # System shells (explicit paths)
    'dash': '/usr/bin/dash',
    'sh': '/bin/sh',
}

# When detecting shell -c pattern:
# 1. Extract shell name (e.g., 'zsh' from 'zsh -c')
# 2. Look up in SHELL_BINARY_MAP
# 3. Replace shell name with full path
# 4. Let path expansion handle @ and ~ placeholders
```

---

## 📝 Testing Checklist

Before marking a shell as fully functional, test:

- [ ] **Basic execution**: `GDS shell -c 'echo hello'`
- [ ] **Path expansion**: `GDS shell -c 'echo @/python'` (should expand `@`)
- [ ] **Tilde expansion**: `GDS shell -c 'echo ~/test'` (should expand `~`)
- [ ] **Special characters**: `GDS shell -c 'echo "test: @#$%"'`
- [ ] **Complex commands**: `GDS shell -c 'cd /tmp && pwd && ls'`
- [ ] **Command chaining**: `GDS shell -c 'echo A && echo B'`

---

## 🎯 Priority Action Items

1. **HIGH**: Implement code translation mapping for `zsh`, `tcsh`, `dash`, `sh`
2. **HIGH**: Complete fish installation
3. **MEDIUM**: Test all installed shells with standard test suite
4. **MEDIUM**: Document shell-specific quirks (e.g., tcsh vs bash syntax differences)
5. **LOW**: Retry mksh installation with alternative source
6. **LOW**: Consider installing ksh if needed

---

## 📚 References

- GDS wrapper detection: `google_drive_shell.py` line ~2318-2325 (deprecated logic)
- Path expansion: `command_generator.py` line ~216-280
- Shell command handling: `google_drive_shell.py` `execute_shell_command()` function

---

**Last Updated**: 2025-11-30  
**Document Version**: 1.0  
**Maintainer**: AI Assistant


