from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Any, Tuple, Optional

def draw_rects_with_alpha(image: Image.Image, rects: List[Dict[str, Any]]) -> Image.Image:
    """Draw rectangles with alpha transparency on a copy of the image."""
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for r in rects:
        bbox = r["bbox"] # [x0, y0, x1, y1]
        fill = r["fill"] # (r, g, b, a)
        outline = r.get("outline")
        width = r.get("width", 1)
        draw.rectangle(bbox, fill=fill, outline=outline, width=width)
    return Image.alpha_composite(image.convert("RGBA"), overlay)

def draw_lines(image: Image.Image, lines: List[Dict[str, Any]]) -> Image.Image:
    """Draw lines with colors and optional labels."""
    res_img = image.convert("RGBA").copy()
    draw = ImageDraw.Draw(res_img)
    for l in lines:
        coords = l["coords"] # [x0, y0, x1, y1]
        color = l.get("color", (0, 0, 0, 255))
        width = l.get("width", 1)
        draw.line(coords, fill=color, width=width)
        
        if "label" in l:
            label_pos = (coords[0] + 5, coords[1] + 5)
            draw.text(label_pos, str(l["label"]), fill=color)
    return res_img

def draw_labels(image: Image.Image, labels: List[Dict[str, Any]]) -> Image.Image:
    """Draw text labels with background and optional border."""
    res_img = image.convert("RGBA").copy()
    draw = ImageDraw.Draw(res_img)
    for l in labels:
        pos = l["pos"] # (x, y)
        text = str(l["text"])
        font = l.get("font") or ImageFont.load_default()
        bg_color = l.get("bg_color", (255, 255, 255, 255))
        border_color = l.get("border_color", (0, 0, 0, 255))
        text_color = l.get("text_color", (0, 0, 0, 255))
        
        # Get text size
        bbox = draw.textbbox(pos, text, font=font)
        # Add some padding
        pad = l.get("padding", 2)
        bg_bbox = [bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad]
        
        # Draw background and border
        if bg_color:
            draw.rectangle(bg_bbox, fill=bg_color, outline=border_color)
        # Draw text
        draw.text(pos, text, fill=text_color, font=font)
    return res_img

def draw_token_boxes(image: Image.Image, tokens: List[Dict[str, Any]]) -> Image.Image:
    """
    Generalized token box drawing.
    tokens: List of {bbox, type ('text'|'visual'), is_unbroken (bool|None)}
    """
    rects = []
    for t in tokens:
        bbox = t["bbox"]
        if t["type"] == "text":
            if t.get("is_unbroken") is True:
                fill = (200, 255, 200, 60) # Light Green
            elif t.get("is_unbroken") is False:
                fill = (200, 200, 200, 60) # Light Gray
            else:
                fill = (200, 255, 200, 60) # Default Light Green
            rects.append({"bbox": bbox, "fill": fill, "outline": None})
        else: # visual
            if t.get("is_unbroken") is False:
                fill = (200, 200, 200, 80) # Gray overlay for broken images
            else:
                fill = (0, 0, 255, 20) # Very faint blue for normal images
            rects.append({"bbox": bbox, "fill": fill, "outline": (0, 0, 255, 100)})
    return draw_rects_with_alpha(image, rects)

def draw_numbered_boxes(image: Image.Image, boxes: List[Dict[str, Any]]) -> Image.Image:
    """
    Draws rectangles with numbers near the top-left corner.
    boxes: List of {bbox, number, color, outline_color}
    """
    res_img = image.convert("RGBA").copy()
    draw = ImageDraw.Draw(res_img)
    font = ImageFont.load_default() # Could be improved with PIL font loading
    
    for b in boxes:
        bbox = b["bbox"]
        num = b["number"]
        color = b.get("color", (0, 0, 255, 255))
        outline = b.get("outline_color", color)
        
        draw.rectangle(bbox, outline=outline, width=1)
        draw.text((bbox[0] - 15, bbox[1] - 15), str(num), fill=color, font=font)
    return res_img

def append_legend(image: Image.Image, items: List[Dict[str, Any]]) -> Image.Image:
    """Append a horizontal legend to the bottom of the image."""
    if not items:
        return image
        
    font = ImageFont.load_default()
    
    # Calculate dimensions
    line_h = 20
    item_spacing = 20
    
    def get_text_width(text, font):
        draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]

    total_w = sum(get_text_width(item["label"], font) + 30 for item in items) + (len(items) - 1) * item_spacing
    
    # Create legend canvas
    legend_h = 40
    legend_w = image.width
    legend_img = Image.new("RGBA", (legend_w, legend_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(legend_img)
    
    curr_x = (legend_w - total_w) // 2
    if curr_x < 10: curr_x = 10
    
    for item in items:
        label = item["label"]
        color = item["color"]
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

