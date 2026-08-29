import os
import sys
import time
import socket
import webbrowser
import threading

# Ensure PyInstaller _MEIPASS directory is resolved correctly when bundled
if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

backend_path = os.path.join(base_dir, 'backend')
if os.path.exists(backend_path) and backend_path not in sys.path:
    sys.path.insert(0, backend_path)
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from app.main import app

def find_free_port(start_port=8080, max_attempts=50):
    for p in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('127.0.0.1', p))
                return p
        except OSError:
            continue
    return start_port

def launch_browser(port):
    time.sleep(1.5)
    webbrowser.open(f"http://127.0.0.1:{port}")

if __name__ == '__main__':
    port = find_free_port(8080)
    print("======================================================================")
    print(" ETABS to RAM Concept Floor Exporter (Desktop Application)")
    print(" Native Windows Execution Mode - ETABS & RAM Concept API Ready")
    print("======================================================================")
    print(f"Starting Web Server at http://127.0.0.1:{port} ...")
    
    threading.Thread(target=launch_browser, args=(port,), daemon=True).start()
    
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")

