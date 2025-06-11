import http.server
import socketserver
import socket
import threading
import json
import os
from urllib.parse import urlparse, parse_qs
from datetime import datetime

PORT = 3000
SOCKET_PORT = 5000

BASE_DIR = os.path.dirname(__file__)
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
STORAGE_DIR = os.path.join(BASE_DIR, 'storage')
DATA_FILE = os.path.join(STORAGE_DIR, 'data.json')


class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.serve_html('index.html')
        elif self.path == '/message.html':
            self.serve_html('message.html')
        elif self.path.startswith('/static/'):
            self.serve_static()
        else:
            self.send_error_page()

    def do_POST(self):
        if self.path == '/message':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            post_str = post_data.decode('utf-8')
            parsed_data = parse_qs(post_str)

            username = parsed_data.get("username", [""])[0]
            message = parsed_data.get("message", [""])[0]

            data_dict = {
                "username": username,
                "message": message
            }

            # Відправлення даних на UDP Socket Server
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(json.dumps(data_dict).encode('utf-8'), ("localhost", SOCKET_PORT))

            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()
        else:
            self.send_error_page()

    def serve_html(self, filename):
        try:
            filepath = os.path.join(TEMPLATES_DIR, filename)
            with open(filepath, 'rb') as file:
                content = file.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error_page()

    def serve_static(self):
        filepath = os.path.join(BASE_DIR, self.path[1:])
        if os.path.exists(filepath):
            if filepath.endswith('.css'):
                content_type = 'text/css'
            elif filepath.endswith('.png'):
                content_type = 'image/png'
            else:
                content_type = 'application/octet-stream'

            with open(filepath, 'rb') as file:
                content = file.read()

            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error_page()

    def send_error_page(self):
        try:
            with open(os.path.join(TEMPLATES_DIR, 'error.html'), 'rb') as file:
                content = file.read()
            self.send_response(404)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, "Page not found")


def run_http_server():
    with socketserver.ThreadingTCPServer(("", PORT), CustomHandler) as httpd:
        print(f"HTTP сервер запущено на порту {PORT}")
        httpd.serve_forever()


def run_socket_server():
    if not os.path.exists(STORAGE_DIR):
        os.makedirs(STORAGE_DIR)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump({}, f)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("localhost", SOCKET_PORT))
    print(f"Socket сервер запущено на порту {SOCKET_PORT}")

    while True:
        data, _ = sock.recvfrom(1024)
        message = json.loads(data.decode('utf-8'))
        now = datetime.now().isoformat()

        with open(DATA_FILE, 'r') as f:
            try:
                db = json.load(f)
            except json.JSONDecodeError:
                db = {}

        db[now] = message

        with open(DATA_FILE, 'w') as f:
            json.dump(db, f, indent=2)


if __name__ == "__main__":
    threading.Thread(target=run_http_server).start()
    threading.Thread(target=run_socket_server).start()
