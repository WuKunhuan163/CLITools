import os
import re
import shutil
import subprocess
from pathlib import Path

tmp_dir = Path("/Applications/AITerminalTools/tmp")
# Resource directory for separation
resource_root = Path("/Applications/AITerminalTools/resource/tool/PYTHON/proj/install")
resource_root.mkdir(parents=True, exist_ok=True)
download_cache = Path("/tmp/python_downloads_auto")
download_cache.mkdir(exist_ok=True)

base_url = "https://github.com"

# Platform tags mapping
PLATFORM_MAP = {
    "aarch64-apple-darwin-pgo": "macos-arm64",
    "x86_64-apple-darwin-pgo": "macos",
    "x86_64-unknown-linux-gnu-pgo": "linux64",
    "x86_64-unknown-linux-musl-noopt": "linux64-musl",
    "x86_64-pc-windows-msvc-shared-pgo": "windows-amd64",
    "i686-pc-windows-msvc-shared-pgo": "windows-x86",
}

def get_platform_tag(url):
    for key, tag in PLATFORM_MAP.items():
        if key in url: return tag
    return None

def parse_html_files(specific_files=None):
    if specific_files:
        html_files = [Path(f) for f in specific_files]
    else:
        html_files = sorted(list(tmp_dir.glob("*.html")))
    
    latest_links = {} # (version, tag) -> (date, url)
    
    for f in html_files:
        date_str = f.stem # YYYYMMDD
        with open(f, 'r') as h:
            content = h.read()
            links = re.findall(r'href="([^"]+\.zst)"', content)
            for link in links:
                # Match cpython-X.Y.Z
                match = re.search(r'cpython-(\d+\.\d+\.\d+)', link)
                if not match: continue
                version = match.group(1)
                tag = get_platform_tag(link)
                if not tag: continue
                
                key = (version, tag)
                if key not in latest_links or date_str >= latest_links[key][0]:
                    latest_links[key] = (date_str, link)
    
    return latest_links, [str(f) for f in html_files]

def deploy(version, tag, rel_url):
    full_url = base_url + rel_url
    fname = os.path.basename(rel_url)
    target_name = f"python{version}-{tag}"
    
    print(f"--- Deploying/Updating to resource: {target_name} from {rel_url} ---")
    download_path = download_cache / fname
    if not download_path.exists():
        subprocess.run(["curl", "-L", full_url, "-o", str(download_path)], check=True)
    
    tmp_extract = Path("/tmp") / f"auto_extract_{target_name}"
    if tmp_extract.exists(): shutil.rmtree(tmp_extract)
    tmp_extract.mkdir()
    
    subprocess.run(f"unzstd -c {download_path} | tar -xf - -C {tmp_extract}", shell=True, check=True)
    
    python_dir = tmp_extract / "python"
    if not python_dir.exists():
        items = list(tmp_extract.glob("*"))
        if len(items) == 1 and items[0].is_dir(): python_dir = items[0]
        else: return

    final_dest = resource_root / target_name
    if final_dest.exists():
        shutil.rmtree(final_dest)
    
    shutil.move(str(python_dir), str(final_dest))
    
    readme_content = f"""Step 1: Download source
curl -L {full_url} -o {fname}

Step 2: Extract from .zst to .tar
unzstd {fname}

Step 3: Extract from .tar
tar -xf {fname.replace('.zst', '')}

Step 4: Rename
mv python {target_name}
"""
    with open(final_dest / "README.md", "w") as f:
        f.write(readme_content)
    print(f"Successfully deployed {target_name}")

if __name__ == "__main__":
    import sys
    files = sys.argv[1:] if len(sys.argv) > 1 else None
    links_to_deploy, files_to_delete = parse_html_files(files)
    print(f"Found {len(links_to_deploy)} builds to deploy.")
    
    for (version, tag), (date, url) in links_to_deploy.items():
        try:
            deploy(version, tag, url)
        except Exception as e:
            print(f"Failed to deploy {version}-{tag}: {e}")
            
    # Cleanup HTML files
    for f in files_to_delete:
        print(f"Deleting evaluated HTML: {f}")
        os.remove(f)
