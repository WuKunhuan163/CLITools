"""Abstract base class for brain backends.

Each backend implements the same interface for storing and retrieving
knowledge across the three memory tiers.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BrainBackend(ABC):
    """Abstract interface for brain storage backends."""

    @abstractmethod
    def store(self, tier: str, key: str, value: Any, metadata: Optional[Dict] = None) -> bool:
        """Store a value in the specified tier.

        Args:
            tier: Memory tier ('working', 'knowledge', 'episodic').
            key: Storage key (e.g., 'context', 'lessons', 'soul').
            value: Content to store.
            metadata: Optional metadata (timestamp, source, etc.).

        Returns:
            True if stored successfully.
        """

    @abstractmethod
    def retrieve(self, tier: str, key: str) -> Any:
        """Retrieve a value from the specified tier.

        Args:
            tier: Memory tier.
            key: Storage key.

        Returns:
            Stored content, or None if not found.
        """

    @abstractmethod
    def search(self, query: str, tier: Optional[str] = None, top_k: int = 10) -> List[Dict]:
        """Search across stored knowledge.

        Args:
            query: Search query string.
            tier: Optional tier to restrict search. None = all tiers.
            top_k: Maximum results.

        Returns:
            List of matching entries with metadata.
        """

    @abstractmethod
    def append(self, tier: str, key: str, entry: Dict) -> bool:
        """Append an entry to a log-style key (e.g., activity, lessons).

        Args:
            tier: Memory tier.
            key: Log key (e.g., 'activity', 'lessons').
            entry: JSON-serializable entry to append.

        Returns:
            True if appended successfully.
        """

    @abstractmethod
    def list_keys(self, tier: str) -> List[str]:
        """List all keys in a tier.

        Args:
            tier: Memory tier.

        Returns:
            List of key names.
        """
