import requests
import re
import sys
import os
from pathlib import Path

def trace_download(url):
    print(f"--- Tracing {url} ---")
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    try:
        # 1. First GET to main page to get cookies
        main_url = url.replace("/download", "")
        print(f"Initial GET to {main_url}...")
        r1 = session.get(main_url, headers=headers, timeout=10)
        print(f"Status: {r1.status_code}, Cookies: {session.cookies.get_dict()}")
        
        # 2. GET the download URL
        print(f"GET to {url}...")
        # We don't allow automatic redirects to see what happens
        r2 = session.get(url, headers=headers, timeout=10, allow_redirects=False)
        print(f"Status: {r2.status_code}")
        for k, v in r2.headers.items():
            print(f"Header: {k}: {v}")
            
        if r2.status_code in [301, 302, 303, 307, 308]:
            redirect_url = r2.headers.get('Location')
            print(f"Redirecting to: {redirect_url}")
            # Follow redirect
            if redirect_url.startswith("/"):
                redirect_url = "https://fontsgeek.com" + redirect_url
            r3 = session.get(redirect_url, headers=headers, timeout=10)
            print(f"Final Status: {r3.status_code}, Content-Type: {r3.headers.get('Content-Type')}")
            
            # If it's a ZIP, save it
            if 'zip' in r3.headers.get('Content-Type', '').lower():
                out = "tool/READ/tmp/trace_result.zip"
                with open(out, 'wb') as f:
                    f.write(r3.content)
                print(f"Saved ZIP to {out}")
            else:
                print("Final result is not a ZIP.")
                print(f"Body starts with: {r3.text[:100]}")
        else:
            print("No redirect found.")
            print(f"Body starts with: {r2.text[:100]}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    trace_download("https://fontsgeek.com/fonts/arnhem-blond/download")

