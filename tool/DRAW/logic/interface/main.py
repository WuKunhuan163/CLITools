from ..engine import draw_rects_with_alpha, draw_labels, append_legend, draw_lines, draw_token_boxes, draw_numbered_boxes

def get_interface():
    return {
        "draw_rects_with_alpha": draw_rects_with_alpha,
        "draw_labels": draw_labels,
        "append_legend": append_legend,
        "draw_lines": draw_lines,
        "draw_token_boxes": draw_token_boxes,
        "draw_numbered_boxes": draw_numbered_boxes
    }

