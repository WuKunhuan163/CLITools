import re
from typing import List, Dict, Any

class NumberIdentifier:
    def __init__(self):
        # Patterns for years (1900-2099) - non-capturing group for findall
        self.year_pattern = re.compile(r'(?:19|20)\d{2}')
        # General number pattern: digits
        self.number_pattern = re.compile(r'\d+')

    def tag_tokens(self, tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for it in tokens:
            text = it.get("text", "").strip()
            if not text:
                continue
            
            # Initialize tags if not present
            if "tags" not in it:
                it["tags"] = {}

            # 1. Check for all years
            years = self.year_pattern.findall(text)
            if years:
                # We store all found years in the rationale
                it["tags"]["year"] = {"rationale": f"Found years: {', '.join(years)}"}
            
            # 2. Check for all numbers
            numbers = self.number_pattern.findall(text)
            if numbers:
                it["tags"]["number"] = {"rationale": f"Found numbers: {', '.join(numbers)}"}
                    
        return tokens
