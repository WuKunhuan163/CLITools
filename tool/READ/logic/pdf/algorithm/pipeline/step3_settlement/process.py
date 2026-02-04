import re
from typing import List, Dict, Any

class Settlement:
    """
    Final phase: handles formatting refinement, reference splitting, and output generation.
    """
    def __init__(self, median_size: float):
        self.median_size = median_size

    def settle(self, merged_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        settled = []
        for item in merged_items:
            if item["type"] == "reference":
                # Splitting logic for references
                entries = self._split_references(item)
                settled.extend(entries)
            else:
                settled.append(self._format_item(item))
        return settled

    def _split_references(self, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Simplified reference splitting
        entries = []
        current_lines = []
        for line in item["lines"]:
            text = "".join([s["text"] for s in line["spans"]]).strip()
            if re.match(r'^(?:\[\d+\]|\d+\.)', text) or text.lower() == "references":
                if current_lines: entries.append(self._create_ref_item(current_lines))
                current_lines = [line]
            else:
                current_lines.append(line)
        if current_lines: entries.append(self._create_ref_item(current_lines))
        return entries

    def _create_ref_item(self, lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        all_spans = [s for l in lines for s in l["spans"]]
        bbox = [min(s["bbox"][0] for s in all_spans), min(s["bbox"][1] for s in all_spans),
                max(s["bbox"][2] for s in all_spans), max(s["bbox"][3] for s in all_spans)]
        text = "".join([s["text"] for s in all_spans]).strip()
        return {"type": "reference", "bbox": bbox, "text": text, "lines": lines}

    def _format_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        # Apply formatting like bolding titles
        if item["type"] in ["title", "heading"]:
            item["text"] = f"**{item['text']}**"
        return item

