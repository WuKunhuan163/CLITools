from tool.DRAW.logic.engine import draw_rects_with_alpha, draw_labels, append_legend

def get_interface():
    """
    Returns a dictionary of callable functions from the DRAW tool's logic.
    This serves as a standardized interface for other tools to interact with DRAW.
    """
    return {
        "draw_rects_with_alpha": draw_rects_with_alpha,
        "draw_labels": draw_labels,
        "append_legend": append_legend
    }

