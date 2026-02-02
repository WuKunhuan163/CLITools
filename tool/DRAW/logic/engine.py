from PIL import Image, ImageDraw, ImageFont
from typing import List, Tuple, Dict, Any

def draw_rects_with_alpha(image: Image.Image, rects: List[Dict[str, Any]]) -> Image.Image:
    """
    Draws semi-transparent rectangles on an image.
    `rects` is a list of dicts, each with "bbox" (scaled) and "fill" (RGBA tuple).
    """
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for rect in rects:
        draw.rectangle(rect["bbox"], fill=rect["fill"])
    return Image.alpha_composite(image, overlay)

def draw_labels(image: Image.Image, labels: List[Dict[str, Any]]) -> Image.Image:
    """
    Draws text labels with white background and black border.
    `labels` is a list of dicts, each with "pos" (x,y), "text", "font", "bg_color", "border_color".
    """
    draw = ImageDraw.Draw(image)
    for label in labels:
        text_bbox = draw.textbbox(label["pos"], label["text"], font=label["font"])
        # Add padding to background rectangle
        padding = 2
        bg_rect = (text_bbox[0] - padding, text_bbox[1] - padding, text_bbox[2] + padding, text_bbox[3] + padding)
        draw.rectangle(bg_rect, fill=label["bg_color"], outline=label["border_color"], width=1)
        draw.text(label["pos"], label["text"], fill=(0,0,0,255), font=label["font"])
    return image

def append_legend(image: Image.Image, legend_items: Dict[str, Tuple[int, int, int, int]]) -> Image.Image:
    """
    Appends a horizontal legend at the bottom of the image.
    `legend_items` is a dict mapping semantic type (str) to color (RGBA tuple).
    """
    if not legend_items:
        return image

    img_width, img_height = image.size
    # Adjust legend height based on image height, minimum 40
    legend_height = max(40, int(img_height * 0.05))
    
    new_img_height = img_height + legend_height
    new_image = Image.new("RGBA", (img_width, new_img_height), (255, 255, 255, 255))
    new_image.paste(image, (0, 0))
    
    draw = ImageDraw.Draw(new_image)
    
    # Draw legend background
    draw.rectangle([0, img_height, img_width, new_img_height], fill=(240, 240, 240, 255))
    
    # Calculate item spacing
    num_items = len(legend_items)
    item_width = img_width // max(1, num_items)
    
    try:
        # Try a reasonable font size for the legend
        font_size = max(12, int(legend_height * 0.4))
        font = ImageFont.truetype("Arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    for i, (label, color) in enumerate(legend_items.items()):
        x_offset = i * item_width
        
        # Draw color swatch
        swatch_size = int(legend_height * 0.4)
        swatch_x = x_offset + 10
        swatch_y = img_height + (legend_height - swatch_size) // 2
        draw.rectangle([swatch_x, swatch_y, swatch_x + swatch_size, swatch_y + swatch_size], fill=color, outline=(0,0,0,255), width=1)
        
        # Draw text label
        text_x = swatch_x + swatch_size + 5
        # Center text vertically in the legend area
        text_bbox = draw.textbbox((text_x, 0), label, font=font)
        text_h = text_bbox[3] - text_bbox[1]
        text_y = img_height + (legend_height - text_h) // 2
        draw.text((text_x, text_y), label, fill=(0,0,0,255), font=font)
        
    return new_image

