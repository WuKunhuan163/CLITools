import requests
import re
import sys
import os
from pathlib import Path

def download_font(font_url, output_path):
    print(f"--- Starting download for {font_url} ---")
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": font_url
    }
    
    # 1. GET the page to get cookies and CSRF token
    try:
        print("GETting page...")
        response = session.get(font_url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Failed to load page: {response.status_code}")
            return False
            
        # Extract CSRF token
        csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.text)
        if not csrf_match:
            print("Could not find CSRF token in page.")
            return False
        
        csrf_token = csrf_match.group(1)
        print(f"Found CSRF token: {csrf_token[:10]}...")
        
        # 2. Prepare POST data
        # Based on user feedback, method should be 'zip'
        post_data = {
            "csrfmiddlewaretoken": csrf_token,
            "method": "zip"
        }
        
        # 3. POST to trigger download
        # Action URL is usually the same as current URL
        print("POSTing to trigger download...")
        # Use stream=True for large files
        download_res = session.post(font_url, data=post_data, headers=headers, stream=True, timeout=30)
        
        if download_res.status_code != 200:
            print(f"POST failed: {download_res.status_code}")
            return False
            
        # Check content type
        content_type = download_res.headers.get('Content-Type', '')
        print(f"Response Content-Type: {content_type}")
        
        if 'zip' in content_type.lower() or 'octet-stream' in content_type.lower():
            print(f"Success! Saving to {output_path}")
            with open(output_path, 'wb') as f:
                for chunk in download_res.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"File saved. Size: {os.path.getsize(output_path)} bytes")
            return True
        else:
            print("Received unexpected content type (not a ZIP).")
            # Peek at content
            peek = download_res.content[:200].decode('utf-8', errors='ignore')
            if '<!DOCTYPE html>' in peek or '<html>' in peek:
                print("Response appears to be HTML.")
            return False
            
    except Exception as e:
        print(f"Error during process: {e}")
        return False

if __name__ == "__main__":
    # Test cases
    fonts = [
        ("https://fontsgeek.com/fonts/Arnhem-Blond", "tool/READ/tmp/arnhem_downloaded.zip"),
        ("https://fontsgeek.com/open-sans-font", "tool/READ/tmp/opensans_downloaded.zip")
    ]
    
    for url, path in fonts:
        if download_font(url, path):
            print(f"Successfully downloaded {url}")
        else:
            print(f"Failed to download {url}")
        print("-" * 30)

