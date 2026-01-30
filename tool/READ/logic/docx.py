#!/usr/bin/env python3
import hashlib
from pathlib import Path
from typing import List
from docx import Document

def extract_docx(docx_path: Path, output_images_dir: Path) -> str:
    """Extract text and images from a Word (.docx) file."""
    doc = Document(docx_path)
    content = []
    
    output_images_dir.mkdir(parents=True, exist_ok=True)
    
    image_counter = 0
    for para in doc.paragraphs:
        if para.text.strip():
            content.append(para.text + "\n")
    
    # Extract images from relationships
    for rel in doc.part.rels.values():
        if "image" in rel.target_ref:
            img_data = rel.target_part.blob
            img_ext = Path(rel.target_ref).suffix or ".png"
            img_hash = hashlib.md5(img_data).hexdigest()
            img_filename = f"word_img_{image_counter}_{img_hash[:8]}{img_ext}"
            img_path = output_images_dir / img_filename
            
            with open(img_path, "wb") as f:
                f.write(img_data)
            
            content.append(f"\n[placeholder: image]\n![]({img_path.absolute()})\n")
            image_counter += 1

    return '\n'.join(content)
