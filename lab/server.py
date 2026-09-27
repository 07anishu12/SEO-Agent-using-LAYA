"""
Local HTTP Server serving the synthetic defect testbench site for testing and regression baselines.
"""
import threading
import urllib.parse
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional
from lab.site_generator import SyntheticSiteGenerator


class SyntheticSiteHandler(BaseHTTPRequestHandler):
    generator: Optional[SyntheticSiteGenerator] = None
    delay_sec: float = 0.0

    def log_message(self, format, *args):
        # Silence console log noise during test and crawler execution
        pass

    def do_GET(self):
        if self.delay_sec > 0:
            time.sleep(self.delay_sec)
        if not self.generator:
            self.send_response(500)
            self.end_headers()
            return

        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        query = parsed.query
        full_path = path + (f"?{query}" if query else "")

        base = self.generator.base_url.rstrip("/")
        req_url = f"{base}{full_path}"
        match_urls = [req_url]
        if req_url.endswith("/"):
            match_urls.append(req_url.rstrip("/"))
        else:
            match_urls.append(req_url + "/")

        # 1. Robots.txt
        if path == "/robots.txt":
            content = f"User-agent: *\nAllow: /\nDisallow: /bikes/draft-release\nSitemap: {base}/sitemap.xml\n"
            data = content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        # 2. Sitemap.xml
        if path == "/sitemap.xml":
            xml_lines = [
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            ]
            for u in self.generator.sitemap_urls:
                xml_lines.append(f'  <url><loc>{u}</loc></url>')
            xml_lines.append('</urlset>')
            xml_content = "\n".join(xml_lines)
            data = xml_content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/xml; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        # 3. Handle redirect hops
        if path == "/hop-1":
            self.send_response(301)
            self.send_header("Location", f"{base}/hop-2")
            self.end_headers()
            return
        elif path == "/hop-2":
            self.send_response(301)
            self.send_header("Location", f"{base}/final-target")
            self.end_headers()
            return
        elif path == "/final-target":
            body = "<html><body><h1>Final Target</h1><a href='/'>Home</a></body></html>".encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # 4. Match page in generator
        page = None
        for u in match_urls:
            if u in self.generator.pages:
                page = self.generator.pages[u]
                break

        if not page:
            not_found = "<html><body><h1>404 Not Found</h1></body></html>".encode("utf-8")
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(not_found)))
            self.end_headers()
            self.wfile.write(not_found)
            return

        status = page.get("status_code", 200)
        # Check redirect
        if status in (301, 302, 307, 308):
            chain = page.get("redirect_chain", [])
            target = chain[0] if chain else f"{base}/"
            self.send_response(status)
            self.send_header("Location", target)
            self.end_headers()
            return

        html = page.get("html", "")
        data = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class SyntheticSiteServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8899, delay_sec: float = 0.0):
        self.host = host
        self.port = port
        self.delay_sec = delay_sec
        self.base_url = f"http://{host}:{port}"
        self.generator = SyntheticSiteGenerator(base_url=self.base_url)
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self):
        handler = SyntheticSiteHandler
        handler.generator = self.generator
        handler.delay_sec = self.delay_sec
        self.server = HTTPServer((self.host, self.port), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=2.0)
