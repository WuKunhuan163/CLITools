"""Brain instance management.

Handles creation, switching, exporting, loading, and migration of brain
instances (sessions). Each instance is an isolated namespace with its own
working memory, knowledge, and episodic data.

Instance directory: data/_/runtime/_/eco/brain/sessions/<name>/
"""
from logic._.brain.instance.session import BrainSessionManager

__all__ = ["BrainSessionManager"]
