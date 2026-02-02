#!/usr/bin/env python3
import os
import sys
from pathlib import Path
import json
import re

# Add project root to sys.path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent.parent
sys.path.append(str(project_root))

def test_page_7_baseline():
    """
    Test the PDF extraction logic for page 7 of the NeRF paper.
    Expected:
    - Merged paragraph across columns: "...disparity between views. Additionally..."
    - References are merged and formatted with newlines.
    - Headings have newlines before body text.
    - Non-standard characters are removed.
    """
    from tool.READ.main import ReadTool
    
    # Path to test PDF
    pdf_path = project_root / "tool" / "READ" / "logic" / "test" / "001_nerf_representing_scenes_as_neural_radiance_fields_for_view_synthesis.pdf"
    if not pdf_path.exists():
        print(f"Error: Test PDF not found at {pdf_path}")
        return False

    # Create ReadTool instance
    tool = ReadTool()
    
    # Run extraction for page 7 in a temporary directory
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Override sys.argv to simulate command line
        sys.argv = ["READ", "extract", str(pdf_path), "--page", "7", "-o", str(tmp_path)]
        tool.run()
        
        # Check markdown content
        md_path = tmp_path / "pages" / "page_007" / "extracted.md"
        if not md_path.exists():
            print("Error: extracted.md not found in output")
            return False
            
        with open(md_path, 'r') as f:
            md_content = f.read()
            
        errors = []
        
        # 1. Check for paragraph merging across columns
        if not re.search(r"disparity between\s+views\. Additionally", md_content):
            errors.append("Paragraphs across columns were not correctly merged.")
            
        # 2. Check for heading formatting (newlines)
        # Match "**7. CONCLUSION ** \n\n Our work" or similar
        if not re.search(r"\*\*7\. CONCLUSION \*\* \n\n", md_content):
            errors.append("Heading '7. CONCLUSION' is missing expected double newline.")
            
        # 3. Check for reference split
        # References are now separate blocks, each starting with its number
        for i in range(1, 8):
            # Match block ID tag followed by reference number
            if not re.search(fr"type: reference -->\n{i}\.", md_content):
                # Try with tab
                if not re.search(fr"type: reference -->\n{i}\.\s", md_content):
                    errors.append(f"Reference {i} was not correctly split into its own block.")
            
        # 4. Check for non-standard characters
        if "\x08" in md_content:
            errors.append("Non-standard character \\x08 was not stripped.")
            
        if errors:
            print(f"DEBUG: md_content follows:\n{md_content}\n---")
            for err in errors:
                print(f"Error: {err}")
            return False

        print("Success: Page 7 baseline verification PASSED.")
        return True

if __name__ == "__main__":
    if test_page_7_baseline():
        print("\nOverall Status: PASS")
        sys.exit(0)
    else:
        print("\nOverall Status: FAIL")
        sys.exit(1)
