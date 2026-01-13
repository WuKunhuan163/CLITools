#!/usr/bin/env python3
"""
DOWNLOAD.py - Resource Download Tool
Downloads resources from URLs to specified destination folders
"""

import os
import sys
import requests
from pathlib import Path
from urllib.parse import urlparse, unquote

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

def get_filename_from_url(url: str) -> str:
    """从URL中提取文件名"""
    parsed = urlparse(url)
    filename = unquote(parsed.path.split('/')[-1])
    
    # 如果没有文件名或者文件名为空，使用默认名称
    if not filename or filename == '/':
        filename = 'downloaded_file'
    
    return filename

def download_file(url: str, destination: str):
    """下载文件"""
    
    # 验证URL
    if not url.startswith(('http://', 'https://')):
        print(f"Error: Invalid URL: {url}")
        return 1
    
    # 处理目标路径
    dest_path = Path(destination).expanduser().resolve()
    
    # 如果目标是目录，则在目录中创建文件
    if dest_path.is_dir() or destination.endswith('/'):
        dest_path = dest_path / get_filename_from_url(url)
    
    # 确保目标目录存在
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Downloading: {url}")
    print(f"Destination: {dest_path}")
    
    try:
        # 创建会话
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # 发送请求
        response = session.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        # 获取文件大小
        total_size = int(response.headers.get('content-length', 0))
        
        # 下载文件
        downloaded_size = 0
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    
                    # 显示进度
                    if total_size > 0:
                        progress = (downloaded_size / total_size) * 100
                        print(f"\rProgress: {progress:.1f}% ({downloaded_size}/{total_size} bytes)", end='', flush=True)
        
        print()  # 换行，确保进度显示结束
        print(f"Download completed successfully!")
        print(f"File saved to: {dest_path}")
        print(f"Size: {downloaded_size} bytes")
        
        return 0
        
    except requests.exceptions.RequestException as e:
        print(f"\nError: Download failed: {e}")
        return 1
    
    except Exception as e:
        print(f"\nError: Unexpected error: {e}")
        return 1

def show_help():
    """显示帮助信息"""
    help_text = """DOWNLOAD - Resource Download Tool

Usage: DOWNLOAD <url> [destination]

Arguments:
  url                  URL of the resource to download
  destination         Destination file path or directory (default: current directory)

Options:
  --help, -h          Show this help message

Examples:
  DOWNLOAD https://example.com/file.pdf                    # Download to current directory
  DOWNLOAD https://example.com/file.pdf ~/Desktop/        # Download to Desktop
  DOWNLOAD https://example.com/file.pdf ~/Desktop/my.pdf  # Download with custom name
  DOWNLOAD --help                                          # Show help

This tool will:
1. Download the resource from the specified URL
2. Save it to the specified destination (or current directory if not specified)
3. Show download progress and file information
4. Handle various file types and content types"""
    
    print(help_text)

def main():
    """主函数"""
    args = sys.argv[1:]
    
    if len(args) == 0:
        print(f"Error: No URL provided")
        print(f"Usage: DOWNLOAD <url> [destination]")
        print(f"Use --help for more information")
        return 1
    
    if args[0] in ['--help', '-h']:
        show_help()
        return 0
    
    # 获取URL和目标路径
    url = args[0]
    destination = args[1] if len(args) > 1 else '.'
    
    return download_file(url, destination)

if __name__ == "__main__":
    sys.exit(main())
