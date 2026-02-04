import fitz
import os
import requests
import time
import re

def extract_fonts_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    fonts = set()
    for page in doc:
        for font in page.get_fonts():
            # font format: (xref, ext, type, basefont, name, encoding)
            basefont = font[3]
            # Remove subset prefix (e.g., 'ABCDEF+FontName' -> 'FontName')
            if '+' in basefont:
                basefont = basefont.split('+')[1]
            fonts.add(basefont)
    return fonts

def check_fontsgeek_availability(font_name):
    # Normalize font name for fontsgeek URL
    # Arnhem-Blond -> Arnhem-Blond
    # TimesNewRomanPSMT -> Times-New-Roman-PSMT
    
    # FontsGeek seems to use Title-Case or the exact name with hyphens
    # Let's try a few variations
    variations = [
        font_name, # Exact
        re.sub(r'[^a-zA-Z0-9]+', '-', font_name), # Hyphenated
        re.sub(r'([a-z])([A-Z])', r'\1-\2', font_name), # CamelCase to Hyphenated
    ]
    
    # Deduplicate and normalize (remove trailing hyphens, etc.)
    variations = list(set([v.strip('-') for v in variations]))
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for v in variations:
        url = f"https://fontsgeek.com/fonts/{v}"
        try:
            # Use a small timeout and check status
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                if "Download" in response.text and "font" in response.text.lower():
                    return True, url
        except:
            continue
            
    return False, f"https://fontsgeek.com/fonts/{font_name}"

def run_font_research():
    papers_dir = "/Users/wukunhuan/Desktop/test_papers/"
    nerf_pdf = "tool/READ/logic/test/001_nerf_representing_scenes_as_neural_radiance_fields_for_view_synthesis.pdf"
    
    pdfs = [nerf_pdf]
    if os.path.exists(papers_dir):
        for f in os.listdir(papers_dir):
            if f.endswith(".pdf"):
                pdfs.append(os.path.join(papers_dir, f))
    
    all_fonts = set()
    print("--- Extracting Fonts from Papers ---")
    for pdf in pdfs:
        try:
            fonts = extract_fonts_from_pdf(pdf)
            print(f"PDF: {os.path.basename(pdf)} -> {len(fonts)} fonts found")
            all_fonts.update(fonts)
        except Exception as e:
            print(f"Error processing {pdf}: {e}")
            
    print(f"\nTotal unique fonts: {len(all_fonts)}")
    print("\n--- Checking FontsGeek Availability ---")
    
    results = []
    for font in sorted(list(all_fonts)):
        # Skip common system fonts or obvious subsets that might fail
        if len(font) < 3: continue
        
        available, url = check_fontsgeek_availability(font)
        status = "AVAILABLE" if available else "NOT FOUND"
        print(f"[{status}] {font:30} -> {url}")
        results.append((font, available, url))
        time.sleep(0.5) # Be polite
        
    # Summary
    available_count = sum(1 for _, a, _ in results if a)
    print(f"\nSummary: {available_count}/{len(results)} fonts potentially available on FontsGeek.")

if __name__ == "__main__":
    run_font_research()

