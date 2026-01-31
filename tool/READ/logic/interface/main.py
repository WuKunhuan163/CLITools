#!/usr/bin/env python3
import sys
from pathlib import Path

def get_pdf_extractor_func():
    """Returns a function to extract content from PDF files."""
    from tool.READ.logic.pdf.extractor import extract_pdf_pages
    return extract_pdf_pages

def get_vision_analyzer_class():
    """Returns the GeminiAnalyzer class for image analysis."""
    from tool.READ.logic.vision.gemini import GeminiAnalyzer
    return GeminiAnalyzer

def get_docx_extractor_func():
    """Returns a function to extract content from Word files."""
    from tool.READ.logic.docx import extract_docx
    return extract_docx

def get_span_merger_func():
    """Returns a function to merge adjacent spans with identical styles."""
    from tool.READ.logic.pdf.formatter import merge_spans
    return merge_spans

