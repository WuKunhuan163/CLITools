import re
from typing import List, Dict, Any

class EmailIdentifier:
    def __init__(self):
        # Basic email regex
        self.email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

    def tag_tokens(self, tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for it in tokens:
            text = it["text"].strip()
            if self.email_pattern.search(text):
                it["tags"]["email"] = {"rationale": "Matches email pattern"}
        return tokens
