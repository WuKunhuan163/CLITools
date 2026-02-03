import copy
from typing import List, Dict, Any
from tool.READ.logic.pdf.formatter import get_span_style

def create_settled_block(lines: List[List[Dict[str, Any]]], type_hint: str, median_size: float) -> Dict[str, Any]:
    """
    Common helper to create a settled block from a list of lines.
    Each line is a list of word tokens.
    """
    all_t = [t for l in lines for t in l]
    if not all_t: return {}
    
    block_bbox = [min(t['bbox'][0] for t in all_t), min(t['bbox'][1] for t in all_t),
                  max(t['bbox'][2] for t in all_t), max(t['bbox'][3] for t in all_t)]
    
    formatted_lines = []
    segments = []
    
    for line in lines:
        if not line: continue
        line_bbox = [min(t['bbox'][0] for t in line), min(t['bbox'][1] for t in line),
                     max(t['bbox'][2] for t in line), max(t['bbox'][3] for t in line)]
        
        formatted_lines.append({"spans": copy.deepcopy(line), "bbox": line_bbox})
        
        line_y = line[0].get("origin", [0, 0])[1]
        for span in line:
            style = get_span_style(span, median_size, line_y)
            text = span["text"]
            if not segments:
                segments.append([text, style])
            else:
                if segments[-1][1] == style:
                    # Space insertion between word tokens
                    if not segments[-1][0].endswith(" ") and not text.startswith(" "):
                        segments[-1][0] += " "
                    segments[-1][0] += text
                else:
                    segments.append([text, style])
        
        # Add space between lines if multiple lines are being merged into segments
        if len(lines) > 1 and segments and not segments[-1][0].endswith(" "):
            segments[-1][0] += " "

    full_text = " ".join([" ".join([t["text"] for t in l]).strip() for l in lines]).strip()
    
    return {
        "type": type_hint,
        "bbox": block_bbox,
        "lines": formatted_lines,
        "segments": segments,
        "text": full_text
    }

