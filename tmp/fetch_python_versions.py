#!/usr/bin/env python3
"""
从Python官方FTP获取所有可用版本列表
"""

import re
import urllib.request
from html.parser import HTMLParser

class PythonFTPParser(HTMLParser):
    """解析Python FTP目录页面"""
    
    def __init__(self):
        super().__init__()
        self.versions = []
        self.in_link = False
        
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.in_link = True
            for attr, value in attrs:
                if attr == 'href':
                    # 匹配形如 "3.9.18/" 的链接
                    match = re.match(r'^(\d+\.\d+\.\d+)/$', value)
                    if match:
                        version = match.group(1)
                        self.versions.append(version)
    
    def handle_endtag(self, tag):
        if tag == 'a':
            self.in_link = False

def fetch_python_versions_from_ftp():
    """从Python官方FTP获取版本列表"""
    ftp_url = "https://www.python.org/ftp/python/"
    
    print(f"📡 正在抓取: {ftp_url}")
    print()
    
    try:
        # 发送HTTP请求
        req = urllib.request.Request(ftp_url)
        req.add_header('User-Agent', 'Mozilla/5.0 (GDS Python Version Checker)')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
        
        # 解析HTML
        parser = PythonFTPParser()
        parser.feed(html)
        
        versions = sorted(parser.versions, key=lambda v: [int(x) for x in v.split('.')])
        
        print(f"✅ 成功抓取 {len(versions)} 个Python版本\n")
        
        # 按大版本分组
        version_groups = {}
        for ver in versions:
            major_minor = '.'.join(ver.split('.')[:2])
            if major_minor not in version_groups:
                version_groups[major_minor] = []
            version_groups[major_minor].append(ver)
        
        # 显示统计
        print("📊 版本统计:")
        for major_minor in sorted(version_groups.keys(), key=lambda v: [int(x) for x in v.split('.')]):
            count = len(version_groups[major_minor])
            latest = version_groups[major_minor][-1]
            print(f"  Python {major_minor}: {count}个版本 (最新: {latest})")
        
        print(f"\n🎯 推荐硬编码版本（每个系列最新3个）:")
        recommended = []
        for major_minor in sorted(version_groups.keys(), key=lambda v: [int(x) for x in v.split('.')], reverse=True):
            group = version_groups[major_minor]
            if len(group) >= 3:
                # 取最新3个
                recommended.extend(group[-3:])
            else:
                # 不足3个就全取
                recommended.extend(group)
            
            # 只推荐3.8+的版本
            major, minor = map(int, major_minor.split('.'))
            if (major, minor) < (3, 8):
                continue
            
            if len(group) >= 3:
                print(f"  {major_minor}: {', '.join(group[-3:])}")
            else:
                print(f"  {major_minor}: {', '.join(group)}")
        
        # 输出Python列表格式
        print(f"\n🐍 硬编码用的Python列表:")
        print("COLAB_VERIFIED_VERSIONS = [")
        for major_minor in sorted(version_groups.keys(), key=lambda v: [int(x) for x in v.split('.')], reverse=True):
            major, minor = map(int, major_minor.split('.'))
            if (major, minor) < (3, 8):
                continue
            
            group = version_groups[major_minor]
            if len(group) >= 3:
                for ver in group[-3:]:
                    print(f"    '{ver}',")
        print("]")
        
        # 测试几个版本的下载URL
        print(f"\n🧪 测试下载URL可用性:")
        test_versions = []
        for major_minor in sorted(version_groups.keys(), key=lambda v: [int(x) for x in v.split('.')], reverse=True)[:3]:
            group = version_groups[major_minor]
            test_versions.append(group[-1])  # 最新版本
        
        for ver in test_versions:
            download_url = f"https://www.python.org/ftp/python/{ver}/Python-{ver}.tgz"
            try:
                req = urllib.request.Request(download_url, method='HEAD')
                req.add_header('User-Agent', 'Mozilla/5.0')
                with urllib.request.urlopen(req, timeout=5) as response:
                    size = int(response.headers.get('Content-Length', 0))
                    print(f"  ✅ Python {ver}: {size / 1024 / 1024:.1f} MB")
            except Exception as e:
                print(f"  ❌ Python {ver}: {e}")
        
        return versions
        
    except Exception as e:
        print(f"❌ 抓取失败: {e}")
        return []

if __name__ == '__main__':
    versions = fetch_python_versions_from_ftp()
    print(f"\n📋 共找到 {len(versions)} 个可用版本")

