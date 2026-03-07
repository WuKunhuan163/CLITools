# GOOGLE.GC

Google Colab automation via Chrome DevTools Protocol (CDP).

## Commands

```bash
GOOGLE.GC status              # Check CDP and Colab tab availability
GOOGLE.GC inject "print('hi')" --timeout 30  # Inject and run code
GOOGLE.GC reopen              # Reopen the configured Colab notebook tab
GOOGLE.GC oauth               # Handle OAuth dialog if present
```

## Interface

Other tools can import Colab functions:

```python
from tool.GOOGLE.logic.chrome.colab import (
    find_colab_tab, reopen_colab_tab, inject_and_execute,
)
from tool.GOOGLE.logic.chrome.oauth import (
    handle_oauth_if_needed, close_oauth_tabs,
)
```

## Dependencies

- **GOOGLE**: Provides core CDP session management and Chrome automation.
- **GOOGLE.GD**: Google Drive file operations (notebook creation/repair).
- **PYTHON**: Managed Python runtime.
