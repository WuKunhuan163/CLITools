def print_width_check(width, is_auto=False, actual_detected=True, project_root=None, translation_func=None):
    """Unified display for terminal width check."""
    _ = translation_func or (lambda k, d, **kwargs: d.format(**kwargs))
    from logic.utils import print_terminal_width_separator

    if is_auto:
        from logic.turing.display.manager import _get_configured_width
        detected = _get_configured_width()
        if detected and isinstance(detected, int) and detected > 0:
            status = str(detected)
        else:
            status = f"{_('config_width_unknown', 'unknown')} ({_('config_using_fallback', 'using fallback')}: {detected})"
        print(_("config_updated_dynamic", "Global configuration updated: {key} will be calculated dynamically.", key="terminal_width") + " Current detected width: " + status)
        display_width = detected
    else:
        display_width = int(width) if isinstance(width, (int, float)) else 60
        print(_("config_updated", "Global configuration updated: {key} = {value}", key="terminal_width", value=display_width))

    print("\n" + _("config_check_row", "Please check whether the below line of '=' ({width}) exactly expands one terminal row:", width=display_width))
    print_terminal_width_separator(display_width)
    print("")
