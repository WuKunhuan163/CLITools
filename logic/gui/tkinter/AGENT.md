# Tkinter GUI Layer - Agent Guide

## Style Module (style.py)

Config loaded from `{style_module_parent}/data/config.json` under key `gui_style`. Defaults used when missing.

### Functions

| Function | Returns |
|----------|---------|
| `get_gui_config()` | Dict of style config |
| `get_label_style()` | Font tuple, e.g. ("Arial", 10) |
| `get_secondary_label_style()` | Smaller italic font |
| `get_button_style(primary=False)` | Font tuple for buttons |
| `get_status_style()` | Font for status labels |
| `get_gui_colors()` | Dict: blue, green, red, pulse |

### Config Keys

`font_family`, `label_font_size`, `button_font_size`, `primary_button_font_size`, `status_font_size`, `primary_button_weight`, `status_color_blue`, `status_color_green`, `status_color_red`, `status_pulse_color`

## Blueprint Hierarchy

```
base.py (BaseGUIWindow, setup_common_bottom_bar)
  -> timed_bottom_bar (re-export)
  -> bottom_bar (BottomBarWindow)
  -> button_bar (ButtonBarWindow)
  -> account_login, two_step_login, two_factor_auth, tutorial (timed)
  -> editable_list (via bottom_bar)
```

## Connection Points

- Blueprints use `window._(key, default)` for translation; resolves via `internal_dir` and `logic/gui/translation`
- `engine.setup_gui_environment()` must be called before Tk() in sandboxed environments
- `manager.run_gui_subprocess()` launches GUI as child; parses `GDS_GUI_RESULT_JSON:` from stdout
