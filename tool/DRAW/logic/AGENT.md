# DRAW Logic — Technical Reference

## engine.py

PIL-based drawing utilities:

- `draw_rects_with_alpha(image, rects)`: Draws rectangles with alpha transparency on a copy. Each rect has `bbox` [x0,y0,x1,y1], `fill` (r,g,b,a), optional `outline` and `width`.
- Additional functions for labels, legends, and composite annotations.

Uses `Image.alpha_composite` for proper transparency blending.

## Gotchas

1. **Returns new image**: `draw_rects_with_alpha` creates a copy — original image is not modified.
2. **RGBA mode**: Input image is converted to RGBA for compositing.
