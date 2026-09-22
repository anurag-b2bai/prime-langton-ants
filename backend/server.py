"""
Python HTTP API Server for Prime-Based Langton's Ant Simulation.
Provides REST API endpoints for file-based prime streaming,
checkpoint management, and static HTML UI hosting on Port 6969.
"""

import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from file_stream import stream_from_file


PRIMES_FILE = "primes_899m.txt"
CHECKPOINT_PATH = "checkpoint.json"
STATIC_HTML_PATH = "../prime_langton_ant.html"
PORT = 6969


class PrimeAPIServerHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Suppress verbose standard HTTP logging
        return

    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ["/api/checkpoint/reset"]:
            try:
                if os.path.exists(CHECKPOINT_PATH):
                    os.remove(CHECKPOINT_PATH)
                self._send_json(200, {"status": "ok", "message": "Checkpoint reset successfully"})
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return
        elif path == "/api/pause":
            try:
                open("pause.flag", "w").close()
                self._send_json(200, {"status": "ok", "message": "Simulation paused"})
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return
        elif path == "/api/resume":
            try:
                if os.path.exists("pause.flag"):
                    os.remove("pause.flag")
                self._send_json(200, {"status": "ok", "message": "Simulation resumed"})
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return
        elif path in ["/api/checkpoint", "/api/save_checkpoint"]:
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                data = json.loads(body.decode("utf-8"))
                grid_data = data.get("grid", [])
                step_cnt = data.get("stepCount", 0)
                if step_cnt > 100 and len(grid_data) == 0:
                    self._send_json(400, {"error": "Refused to save empty grid for non-zero stepCount"})
                    return
                with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
                    json.dump(data, f)
                self._send_json(200, {"status": "ok", "message": "Checkpoint saved to disk"})
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return
        self._send_json(404, {"error": "Endpoint not found"})

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/favicon.ico":
            self.send_response(204)
            self._set_cors_headers()
            self.end_headers()
            return

        # REST API: /api/status
        if path == "/api/status":
            try:
                file_exists = os.path.exists(PRIMES_FILE)
                file_size = os.path.getsize(PRIMES_FILE) if file_exists else 0
                self._send_json(200, {
                    "status": "online",
                    "source": "file",
                    "primes_file": PRIMES_FILE,
                    "file_size_gb": round(file_size / 1e9, 2),
                    "file_exists": file_exists
                })
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

        # REST API: /api/primes
        elif path == "/api/primes":
            try:
                start_idx = int(params.get("start", [1])[0])
                count = int(params.get("count", [10000])[0])
                primes_list = []
                for row in stream_from_file(PRIMES_FILE, start_prime_index=start_idx):
                    primes_list.append([row[0], row[1], row[2], row[3]])
                    if len(primes_list) >= count:
                        break
                self._send_json(200, {
                    "start": start_idx,
                    "count": len(primes_list),
                    "primes": primes_list
                })
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

        # REST API: /api/checkpoint
        elif path == "/api/checkpoint":
            try:
                if os.path.exists(CHECKPOINT_PATH):
                    file_size = os.path.getsize(CHECKPOINT_PATH)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(file_size))
                    self._set_cors_headers()
                    self.end_headers()
                    with open(CHECKPOINT_PATH, "rb") as f:
                        while True:
                            chunk = f.read(4 * 1024 * 1024)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                else:
                    self._send_json(200, {"checkpoint": None, "message": "No checkpoint found"})
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

        # Serve static HTML / assets
        else:
            file_to_serve = STATIC_HTML_PATH if path in ["/", "/prime_langton_ant.html"] else path.lstrip("/")
            possible_paths = [file_to_serve, os.path.join(".", file_to_serve), os.path.join("backend", file_to_serve), os.path.join("..", file_to_serve)]
            resolved_path = None
            for p in possible_paths:
                if os.path.exists(p) and os.path.isfile(p):
                    resolved_path = p
                    break

            if resolved_path:
                content_type = "text/html"
                if resolved_path.endswith(".js"): content_type = "application/javascript"
                elif resolved_path.endswith(".css"): content_type = "text/css"
                elif resolved_path.endswith(".json"): content_type = "application/json"
                elif resolved_path.endswith(".bmp"): content_type = "image/bmp"
                elif resolved_path.endswith(".png"): content_type = "image/png"

                with open(resolved_path, "rb") as f:
                    content = f.read()

                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(content)
            else:
                self._send_json(404, {"error": f"File or endpoint not found: {path}"})

    def _send_json(self, status_code: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(body)


def run_server(port: int = PORT):
    server_address = ("", port)
    httpd = HTTPServer(server_address, PrimeAPIServerHandler)
    print(f"[*] Prime API & Web Server running on http://localhost:{port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server shutting down...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
