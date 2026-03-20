"""Language/translation interface for tools.

Provides access to the translation helper and language management commands.
"""
# TODO: [migration] This facade will be migrated/rewritten as part of the __/ architecture restructure.
from logic._.lang.utils import get_translation
from logic._.lang.commands import audit_lang, list_languages

__all__ = [
    "get_translation",
    "audit_lang",
    "list_languages",
]
