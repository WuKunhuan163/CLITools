import requests
import re
import sys

def check_headers(url):
    print(f"--- Checking headers for {url} ---")
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    # 1. GET page
    r1 = session.get(url, headers=headers)
    csrf = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r1.text).group(1)
    
    # 2. POST
    post_data = {
        "csrfmiddlewaretoken": csrf,
        "method": "zip"
    }
    post_headers = headers.copy()
    post_headers["Referer"] = url
    
    r2 = session.post(url, data=post_data, headers=post_headers, stream=True)
    print(f"POST Status: {r2.status_code}")
    print(f"POST Content-Type: {r2.headers.get('Content-Type')}")
    print(f"POST Content-Disposition: {r2.headers.get('Content-Disposition')}")
    
    # 3. If it's a ZIP, save it
    if 'zip' in r2.headers.get('Content-Type', '').lower() or 'zip' in r2.headers.get('Content-Disposition', '').lower():
        fname = "tool/READ/tmp/test_headers.zip"
        if r2.headers.get('Content-Disposition'):
            match = re.search(r'filename="([^"]+)"', r2.headers.get('Content-Disposition'))
            if match: fname = f"tool/READ/tmp/{match.group(1)}"
            
        with open(fname, 'wb') as f:
            for chunk in r2.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Saved to {fname}")
    else:
        print("Not a ZIP.")

if __name__ == "__main__":
    check_headers("https://fontsgeek.com/fonts/Arnhem-Blond")
    check_headers("https://fontsgeek.com/open-sans-font")

