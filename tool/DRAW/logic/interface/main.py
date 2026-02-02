from ..engine import draw_rects_with_alpha, draw_labels, append_legend

def get_interface():
    return {
        "draw_rects_with_alpha": draw_rects_with_alpha,
        "draw_labels": draw_labels,
        "append_legend": append_legend
    }

