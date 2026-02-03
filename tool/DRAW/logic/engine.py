from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Any, Tuple

def draw_rects_with_alpha(image: Image.Image, rects: List[Dict[str, Any]]) -> Image.Image:
    """Draw rectangles with alpha transparency on a copy of the image."""
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for r in rects:
        bbox = r["bbox"] # [x0, y0, x1, y1]
        fill = r["fill"] # (r, g, b, a)
        draw.rectangle(bbox, fill=fill)
    return Image.alpha_composite(image.convert("RGBA"), overlay)

def draw_labels(image: Image.Image, labels: List[Dict[str, Any]]) -> Image.Image:
    """Draw text labels with white background and black border."""
    res_img = image.copy()
    draw = ImageDraw.Draw(res_img)
    for l in labels:
        pos = l["pos"] # (x, y)
        text = str(l["text"])
        font = l.get("font") or ImageFont.load_default()
        bg_color = l.get("bg_color", (255, 255, 255, 255))
        border_color = l.get("border_color", (0, 0, 0, 255))
        
        # Get text size
        bbox = draw.textbbox(pos, text, font=font)
        # Add some padding
        pad = 2
        bg_bbox = [bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad]
        
        # Draw background and border
        draw.rectangle(bg_bbox, fill=bg_color, outline=border_color)
        # Draw text
        draw.text(pos, text, fill=(0, 0, 0, 255), font=font)
    return res_img

def append_legend(image: Image.Image, items: Dict[str, Tuple[int, int, int, int]]) -> Image.Image:
    """Append a horizontal legend to the bottom of the image."""
    if not items:
        return image
        
    font = ImageFont.load_default()
    item_list = list(items.items())
    
    # Calculate dimensions
    char_w = 8
    line_h = 20
    item_spacing = 20
    
    total_w = sum(get_text_width(k, font) + 30 for k, v in item_list) + (len(item_list) - 1) * item_spacing
    
    # Create legend canvas
    legend_h = 40
    legend_w = image.width
    legend_img = Image.new("RGBA", (legend_w, legend_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(legend_img)
    
    curr_x = (legend_w - total_w) // 2
    if curr_x < 10: curr_x = 10
    
    for label, color in item_list:
        # Draw color box
        box_size = 12
        box_y = (legend_h - box_size) // 2
        draw.rectangle([curr_x, box_y, curr_x + box_size, box_y + box_size], fill=color, outline=(0,0,0,255))
        curr_x += box_size + 5
        
        # Draw label
        text_y = (legend_h - 12) // 2
        draw.text((curr_x, text_y), label, fill=(0, 0, 0, 255), font=font)
        curr_x += get_text_width(label, font) + item_spacing
        
    # Combine
    new_img = Image.new("RGBA", (image.width, image.height + legend_h), (255, 255, 255, 255))
    new_img.paste(image, (0, 0))
    new_img.paste(legend_img, (0, image.height))
    return new_img

def get_text_width(text, font):
    draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]

