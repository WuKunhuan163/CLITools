import requests
import re
import sys
import os

def final_attempt(url):
    print(f"--- Final Attempt for {url} ---")
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": url
    }
    
    # 1. GET page
    print("Step 1: GET page...")
    r1 = session.get(url, headers=headers)
    print(f"Status: {r1.status_code}")
    
    # 2. Extract CSRF and form action
    csrf = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r1.text).group(1)
    # The action might be a path
    action = re.search(r'form method="post" action="([^"]+)"', r1.text).group(1)
    if action.startswith("/"):
        action = "https://fontsgeek.com" + action
    print(f"Action: {action}, CSRF: {csrf[:10]}...")
    
    # 3. POST to trigger download
    print("Step 2: POST to action...")
    post_data = {
        "csrfmiddlewaretoken": csrf,
        "method": "zip"
    }
    post_headers = headers.copy()
    post_headers["Referer"] = url
    
    r2 = session.post(action, data=post_data, headers=post_headers)
    print(f"POST Status: {r2.status_code}")
    
    # 4. GET the /download URL in the same session
    download_url = url.rstrip("/") + "/download"
    print(f"Step 3: GET {download_url}...")
    r3 = session.get(download_url, headers=headers)
    print(f"Final Status: {r3.status_code}, Content-Type: {r3.headers.get('Content-Type')}")
    
    if 'zip' in r3.headers.get('Content-Type', '').lower() or r3.status_code == 200 and len(r3.content) > 15000:
        with open("tool/READ/tmp/final_result.zip", 'wb') as f:
            f.write(r3.content)
        print(f"SAVED! Size: {len(r3.content)} bytes")
        return True
    else:
        print("Final result is not a ZIP.")
        print(f"Body starts with: {r3.text[:100]}")
            
    return False

if __name__ == "__main__":
    final_attempt("https://fontsgeek.com/fonts/Arnhem-Blond")

