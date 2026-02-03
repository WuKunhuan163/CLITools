import re
from typing import List, Dict, Any

class NumberIdentifier:
    def __init__(self):
        # Patterns for years (1900-2099) - require word boundaries
        self.year_pattern = re.compile(r'\b(?:19|20)\d{2}\b')
        # General number pattern: digits, require word boundaries
        # This will match "1", "100", but not "5D" (unless D is a boundary?)
        # Actually \b matches between \w and \W. D is \w. So \b\d+\b will NOT match 5 in 5D.
        self.number_pattern = re.compile(r'\b\d+\b')

    def tag_tokens(self, tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for it in tokens:
            text = it.get("text", "").strip()
            if not text:
                continue
            
            # Initialize tags if not present
            if "tags" not in it:
                it["tags"] = {}

            # 1. Check for whole-word years
            years = self.year_pattern.findall(text)
            if years:
                it["tags"]["year"] = {"rationale": f"Found years: {', '.join(years)}"}
            
            # 2. Check for whole-word numbers
            numbers = self.number_pattern.findall(text)
            if numbers:
                it["tags"]["number"] = {"rationale": f"Found numbers: {', '.join(numbers)}"}
                    
        return tokens
