#!/usr/bin/env python3
"""一键启动本地服务并打开背单词页面。

用法:
    python3 serve.py            # 默认端口 8000
    python3 serve.py 9000       # 指定端口
"""
import http.server
import socketserver
import sys
import webbrowser
from pathlib import Path


class Handler(http.server.SimpleHTTPRequestHandler):
    # 启用对 .db 的范围请求支持（SimpleHTTPRequestHandler 已经支持 Range）
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        '.db': 'application/octet-stream',
        '.wasm': 'application/wasm',
    }
    def end_headers(self):
        # 允许浏览器缓存 db 文件
        if self.path.endswith('.db'):
            self.send_header('Cache-Control', 'public, max-age=31536000, immutable')
        super().end_headers()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    root = Path(__file__).parent
    import os
    os.chdir(root)
    with socketserver.TCPServer(('127.0.0.1', port), Handler) as httpd:
        url = f'http://127.0.0.1:{port}/index.html'
        print(f'\n  程序员英语背单词\n  → {url}\n  (Ctrl+C 退出)\n')
        try:
            webbrowser.open(url)
        except Exception:
            pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
