import http.server
import socketserver
import json
import subprocess
import threading
import os
import time

PORT = 8080
process_handle = None
process_lock = threading.Lock()
logs_history = []

def log_msg(msg, level="INFO"):
    timestamp = time.strftime("%H:%M:%S")
    entry = f"[{timestamp}] [{level}] {msg}"
    print(entry)
    logs_history.append(entry)
    if len(logs_history) > 100:
        logs_history.pop(0)

class DactylUIHandler(http.server.SimpleHTTPRequestHandler):
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        global process_handle
        if self.path == '/api/status':
            with process_lock:
                is_running = (process_handle is not None and process_handle.poll() is None)
                if not is_running and process_handle is not None:
                    process_handle = None
                    log_msg("Sistem Dactyl-AI berhenti secara eksternal.", "WARNING")

            # Check model availability
            model_exists = os.path.exists("models/svm_gesture_model.pkl")
            status_data = {
                "is_running": is_running,
                "model_available": model_exists,
                "logs": logs_history[-20:],
                "system_info": {
                    "version": "V2.5 Magic Cursor",
                    "engine": "MediaPipe Hands + SVM RBF",
                    "ema_alpha": 0.25,
                    "gui_opacity": "60%"
                }
            }
            self._send_json(status_data)
        elif self.path == '/' or self.path == '/index.html':
            if os.path.exists('run_system_ui.html'):
                self.path = '/run_system_ui.html'
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        else:
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        global process_handle
        if self.path == '/api/toggle':
            with process_lock:
                is_running = (process_handle is not None and process_handle.poll() is None)
                if is_running:
                    try:
                        process_handle.terminate()
                        process_handle.wait(timeout=3)
                    except Exception:
                        try:
                            process_handle.kill()
                        except Exception:
                            pass
                    process_handle = None
                    log_msg("Dactyl-AI Magic Cursor dimatikan oleh pengguna dari Dashboard UI.", "INFO")
                    self._send_json({"status": "stopped", "is_running": False})
                else:
                    try:
                        # Launch run_system.py asynchronously
                        python_cmd = "python"
                        if os.path.exists("venv/Scripts/python.exe"):
                            python_cmd = "venv/Scripts/python.exe"
                        elif os.path.exists(".venv/Scripts/python.exe"):
                            python_cmd = ".venv/Scripts/python.exe"
                            
                        log_msg(f"Memulai Dactyl-AI dengan perintah: {python_cmd} src/run_system.py...", "INFO")
                        process_handle = subprocess.Popen([python_cmd, "src/run_system.py"])
                        log_msg("Dactyl-AI Magic Cursor berhasil diluncurkan!", "SUCCESS")
                        self._send_json({"status": "started", "is_running": True})
                    except Exception as e:
                        log_msg(f"Gagal meluncurkan sistem: {e}", "ERROR")
                        self._send_json({"status": "error", "message": str(e), "is_running": False}, status=500)
        elif self.path == '/api/settings':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            settings = json.loads(post_data.decode('utf-8'))
            log_msg(f"Pengaturan sistem diperbarui: {settings}", "INFO")
            self._send_json({"status": "updated", "settings": settings})
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), DactylUIHandler) as httpd:
        print("="*70)
        print(f"  DACTYL-AI MODERN WEB DASHBOARD SERVER RUNNING")
        print(f"  Akses URL Dashboard di: http://localhost:{PORT}")
        print("="*70)
        log_msg("Server Web Dashboard Dactyl-AI V2.5 diaktifkan pada port 8080.", "INFO")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nMematikan server dashboard...")
            with process_lock:
                if process_handle and process_handle.poll() is None:
                    process_handle.terminate()

if __name__ == '__main__':
    run_server()
