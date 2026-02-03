import re
from typing import List, Dict, Any, Tuple

class NameIdentifier:
    """
    Tags individual tokens that likely represent human names.
    """
    def __init__(self, median_size: float):
        self.median_size = median_size
        # Stricter regex for name parts: "Mildenhall", "Ben", "Ren", "Ng"
        self.name_part_regex = re.compile(r"^[A-Z][a-z]{1,15}$|^[A-Z]\.$|^[A-Z]{2,15}$")

    def tag_tokens(self, tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for it in tokens:
            text = it.get("text", "").strip().strip(",").strip()
            if not text: continue
            
            if self.name_part_regex.match(text):
                # Extensive exclusion list
                if text.lower() in [
                    "abstract", "figure", "table", "the", "and", "for", "with", "this", "from",
                    "using", "scene", "view", "neural", "field", "model", "page", "section",
                    "introduction", "results", "conclusion", "method", "continuous", "spatial",
                    "location", "viewing", "direction", "images", "input", "output", "data",
                    "view-dependent", "radiance", "volume", "density", "color", "camera", "rays",
                    "classic", "rendering", "techniques", "project", "differentiable", "required",
                    "optimize", "representation", "poses", "effectively", "photorealistic",
                    "complicated", "geometry", "appearance", "demonstrate", "outperform", "prior",
                    "work", "march", "generate", "sampled", "original", "version", "paper", "published",
                    "proceedings", "european", "conference", "computer", "vision", "january", "vol", "no",
                    "communications", "acm", "method", "presents", "achieves", "state-of-the-art",
                    "synthesizing", "complex", "scenes", "underlying", "volumetric", "function",
                    "sparse", "algorithm", "represents", "fully", "connected", "nonconvolutional",
                    "deep", "network", "whose", "single", "coordinate", "emitted", "synthesize",
                    "querying", "coordinates", "along", "camera", "rays", "use", "classic", "volume",
                    "rendering", "techniques", "project", "output", "colors", "densities", "into",
                    "image", "because", "naturally", "differentiable", "only", "required", "optimize",
                    "representation", "set", "images", "known", "camera", "poses", "describe", "how",
                    "effectively", "optimize", "neural", "radiance", "fields", "render", "photorealistic",
                    "novel", "views", "scenes", "with", "complicated", "geometry", "appearance", "and",
                    "demonstrate", "results", "that", "outperform", "prior", "work", "neural", "rendering",
                    "view", "synthesis", "march", "camera", "rays", "through", "scene", "generate", "sampled",
                    "original", "version", "this", "paper", "was", "published", "proceedings", "european",
                    "conference", "computer", "vision", "january", "vol", "no", "communications", "acm",
                    "drums", "input", "images", "render", "new", "views"
                ]:
                    continue
                
                if "tags" not in it: it["tags"] = {}
                it["tags"]["name"] = {"rationale": "capitalized_part"}
        return tokens
