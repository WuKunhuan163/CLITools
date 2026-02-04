import fitz
import os
import sys
from contextlib import redirect_stderr
from typing import Optional

# Global suppression of mupdf errors
fitz.TOOLS.mupdf_display_errors(False)

class FitzWrapper:
    """
    A wrapper around PyMuPDF (fitz) that suppresses unwanted output on stderr.
    """
    @staticmethod
    def open(filename: Optional[str] = None, **kwargs) -> fitz.Document:
        with open(os.devnull, 'w') as f:
            with redirect_stderr(f):
                if filename:
                    return fitz.open(filename, **kwargs)
                else:
                    return fitz.open(**kwargs)

    @staticmethod
    def save(doc: fitz.Document, filename: str, **kwargs):
        with open(os.devnull, 'w') as f:
            with redirect_stderr(f):
                doc.save(filename, **kwargs)

    @staticmethod
    def get_pixmap(page: fitz.Page, **kwargs) -> fitz.Pixmap:
        with open(os.devnull, 'w') as f:
            with redirect_stderr(f):
                return page.get_pixmap(**kwargs)
