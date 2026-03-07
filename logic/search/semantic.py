"""Lightweight semantic text search using TF-IDF with stdlib only.

Indexes text documents (README, for_agent, interface docstrings, skill files)
and ranks them by cosine similarity against a query.  No external dependencies.

Usage::

    from logic.search.semantic import SemanticIndex

    idx = SemanticIndex()
    idx.add("GOOGLE", "Chrome automation tool for browser control", {"type": "tool"})
    idx.add("GMAIL", "Send and read emails via Gmail", {"type": "tool"})
    results = idx.search("open a Chrome tab", top_k=3)
"""
import math
import re
from collections import Counter
from typing import Dict, List, Optional, Any, Tuple

_STOP_WORDS = frozenset(
    "a an the is are was were be been being have has had do does did will "
    "would shall should may might can could of in to for on with at by from "
    "as into through during before after above below between out off over "
    "up and but or nor not so yet both either neither each every all any few "
    "more most other some such no only same than too very just about also "
    "back how its let new now old see way who what where when which this that "
    "these those then there here if it he she they we you i me my your his "
    "her our their use used using via".split()
)


def _tokenize(text: str) -> List[str]:
    """Lowercase, split on non-alphanumeric, filter stop words and short tokens."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]


class SemanticIndex:
    """In-memory TF-IDF index for fast semantic search."""

    def __init__(self):
        self._docs: List[Tuple[str, List[str], Dict[str, Any]]] = []
        self._idf: Dict[str, float] = {}
        self._dirty = True

    def add(self, doc_id: str, text: str, meta: Optional[Dict[str, Any]] = None):
        """Add a document to the index.

        Parameters
        ----------
        doc_id : str
            Unique identifier (e.g. tool name, skill name).
        text : str
            Full text content to index.
        meta : dict, optional
            Arbitrary metadata returned with search results.
        """
        tokens = _tokenize(text)
        self._docs.append((doc_id, tokens, meta or {}))
        self._dirty = True

    def _build_idf(self):
        n = len(self._docs)
        if n == 0:
            return
        df: Counter = Counter()
        for _, tokens, _ in self._docs:
            unique = set(tokens)
            for t in unique:
                df[t] += 1
        self._idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}
        self._dirty = False

    def _tfidf_vector(self, tokens: List[str]) -> Dict[str, float]:
        tf = Counter(tokens)
        total = len(tokens) or 1
        vec: Dict[str, float] = {}
        for t, count in tf.items():
            idf = self._idf.get(t, 1.0)
            vec[t] = (count / total) * idf
        return vec

    @staticmethod
    def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
        keys = set(a) & set(b)
        if not keys:
            return 0.0
        dot = sum(a[k] * b[k] for k in keys)
        mag_a = math.sqrt(sum(v * v for v in a.values()))
        mag_b = math.sqrt(sum(v * v for v in b.values()))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    def search(self, query: str, top_k: int = 5, min_score: float = 0.01) -> List[Dict[str, Any]]:
        """Search the index and return ranked results.

        Parameters
        ----------
        query : str
            Natural language query.
        top_k : int
            Maximum number of results.
        min_score : float
            Minimum cosine similarity threshold.

        Returns
        -------
        list[dict]
            Each dict has ``id``, ``score``, ``meta``.
        """
        if self._dirty:
            self._build_idf()

        q_tokens = _tokenize(query)
        if not q_tokens:
            return []

        q_vec = self._tfidf_vector(q_tokens)
        scored = []
        for doc_id, tokens, meta in self._docs:
            d_vec = self._tfidf_vector(tokens)
            score = self._cosine(q_vec, d_vec)
            if score >= min_score:
                scored.append({"id": doc_id, "score": round(score, 4), "meta": meta})

        scored.sort(key=lambda x: -x["score"])
        return scored[:top_k]

    def __len__(self):
        return len(self._docs)
