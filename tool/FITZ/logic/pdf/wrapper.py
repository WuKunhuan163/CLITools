import fitz
import os
import sys
from typing import Optional, Any

# Global suppression of mupdf errors
fitz.TOOLS.mupdf_display_errors(False)

class FitzWrapper:
    """
    A wrapper around PyMuPDF (fitz) that suppresses unwanted output on stderr.
    Uses low-level os.dup2 to catch output from the underlying C library.
    """
    @staticmethod
    def _suppress_stderr():
        """Redirects stderr to /dev/null at the OS level."""
        try:
            stderr_fd = sys.stderr.fileno()
            old_stderr_fd = os.dup(stderr_fd)
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, stderr_fd)
            return old_stderr_fd, devnull
        except:
            return None, None

    @staticmethod
    def _restore_stderr(old_stderr_fd, devnull):
        """Restores stderr from the saved file descriptor."""
        if old_stderr_fd is not None:
            try:
                stderr_fd = sys.stderr.fileno()
                os.dup2(old_stderr_fd, stderr_fd)
                os.close(old_stderr_fd)
                os.close(devnull)
            except:
                pass

    @staticmethod
    def open(filename: Optional[str] = None, **kwargs) -> fitz.Document:
        old_fd, devnull = FitzWrapper._suppress_stderr()
        try:
            if filename:
                return fitz.open(filename, **kwargs)
            else:
                return fitz.open(**kwargs)
        finally:
            FitzWrapper._restore_stderr(old_fd, devnull)

    @staticmethod
    def save(doc: fitz.Document, filename: str, **kwargs):
        old_fd, devnull = FitzWrapper._suppress_stderr()
        try:
            doc.save(filename, **kwargs)
        finally:
            FitzWrapper._restore_stderr(old_fd, devnull)

    @staticmethod
    def get_pixmap(page: fitz.Page, **kwargs) -> fitz.Pixmap:
        old_fd, devnull = FitzWrapper._suppress_stderr()
        try:
            return page.get_pixmap(**kwargs)
        finally:
            FitzWrapper._restore_stderr(old_fd, devnull)
