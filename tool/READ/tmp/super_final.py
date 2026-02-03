import requests
import re
import os

def super_final_attempt(url):
    print(f"--- Super Final Attempt for {url} ---")
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    # 1. GET page
    print("Step 1: GET page...")
    r1 = session.get(url, headers=headers)
    csrf = session.cookies.get('csrftoken')
    if not csrf:
        csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r1.text)
        if csrf_match: csrf = csrf_match.group(1)
        
    print(f"CSRF: {csrf[:10] if csrf else 'NONE'}")
    
    # 2. POST
    print("Step 2: POST...")
    # Try the action URL as seen in the form
    action = re.search(r'form method="post" action="([^"]+)"', r1.text).group(1)
    if action.startswith("/"): action = "https://fontsgeek.com" + action
    
    post_data = {
        "csrfmiddlewaretoken": csrf,
        "method": "zip"
    }
    
    # MUST have Referer matching the POST action usually
    post_headers = headers.copy()
    post_headers["Referer"] = url
    
    # We follow redirects!
    r2 = session.post(action, data=post_data, headers=post_headers, stream=True)
    print(f"POST Status: {r2.status_code}")
    print(f"Final URL: {r2.url}")
    print(f"Content-Type: {r2.headers.get('Content-Type')}")
    print(f"Content-Length: {r2.headers.get('Content-Length')}")
    
    if 'zip' in r2.headers.get('Content-Type', '').lower() or (r2.status_code == 200 and int(r2.headers.get('Content-Length', 0) or 0) > 15000):
        out = f"tool/READ/tmp/super_final.zip"
        with open(out, 'wb') as f:
            for chunk in r2.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"SAVED to {out}! Size: {os.path.getsize(out)}")
        return True
    
    print("Failed to get ZIP.")
    return False

if __name__ == "__main__":
    # The user said lowercase and /download
    super_final_attempt("https://fontsgeek.com/fonts/arnhem-blond")

