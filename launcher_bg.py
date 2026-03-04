import subprocess
import webbrowser
import sys
import os
import threading
import pystray
from PIL import Image, ImageDraw
import time
import socket
import logging

# Change working directory to the script's directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Setup logging
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launcher.log")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    force=True
)

logging.info("--- Launcher starting ---")

# Configuration
PROC_NAME = "uvicorn"
API_URL = "http://127.0.0.1:8000"

class BackgroundLauncher:
    def __init__(self):
        self.server_process = None
        self.is_running = False
        self.icon = None
        
    def create_icon_image(self):
        # Generate a sleek icon: Purple square with a white "F"
        width = 64
        height = 64
        color_bg = (108, 92, 231)  # Purple
        color_text = (255, 255, 255) # White
        
        image = Image.new('RGB', (width, height), color_bg)
        dc = ImageDraw.Draw(image)
        # Draw a simple search-icon like circle
        dc.ellipse((10, 10, 54, 54), outline=color_text, width=4)
        dc.line((45, 45, 58, 58), fill=color_text, width=6)
        return image

    def ensure_es_service(self):
        """Ensure Elasticsearch service is running on Windows."""
        if os.name != 'nt':
            return

        try:
            # Check service status
            result = subprocess.run(['sc', 'query', 'elasticsearch-service-x64'], 
                                   capture_output=True, text=True)
            if "RUNNING" in result.stdout:
                logging.info("Elasticsearch service is already running.")
                return

            if "SERVICE_NAME" in result.stdout:
                logging.info("Starting Elasticsearch service...")
                # Try starting (might require admin)
                start_res = subprocess.run(['sc', 'start', 'elasticsearch-service-x64'], 
                                          capture_output=True, text=True)
                
                if "Access is denied" in start_res.stderr or "Access is denied" in start_res.stdout:
                    logging.warning("Access denied when starting ES service. Attempting elevation...")
                    # Elevation trick using PowerShell
                    cmd = "Start-Process cmd -ArgumentList '/c sc start elasticsearch-service-x64' -Verb RunAs"
                    subprocess.run(['powershell', '-Command', cmd], creationflags=subprocess.CREATE_NO_WINDOW)
                    time.sleep(5)
                else:
                    # Wait a bit for it to spin up
                    time.sleep(5)
            else:
                logging.warning("Elasticsearch service 'elasticsearch-service-x64' not found.")
        except Exception as e:
            logging.error(f"Error checking/starting ES service: {e}")

    def start_server(self):
        logging.info("Starting server...")
        if self.is_running:
            logging.info("Server already marked as running.")
            return

        # Ensure ES is up before the app tries to connect
        self.ensure_es_service()

        # Check if port 8000 is already in use
        if self.is_port_in_use(8000):
            logging.info("Port 8000 already in use, assuming server is up.")
            self.is_running = True
            return

        try:
            # Start uvicorn as a subprocess
            cmd = [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"]
            logging.info(f"Running command: {' '.join(cmd)}")
            
            # Hide console window on Windows
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0 # SW_HIDE
            
            self.server_process = subprocess.Popen(
                cmd, 
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            logging.info(f"Server process started with PID {self.server_process.pid}")
            self.is_running = True
            # Auto-open browser after a short delay
            threading.Timer(2.0, self.open_browser).start()
            
            # Start monitoring thread
            threading.Thread(target=self.monitor_process, daemon=True).start()
            
        except Exception as e:
            logging.error(f"Failed to start server: {e}", exc_info=True)

    def is_port_in_use(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0

    def monitor_process(self):
        while self.is_running and self.server_process:
            if self.server_process.poll() is not None:
                self.is_running = False
                self.server_process = None
                break
            time.sleep(2)

    def stop_server(self):
        if self.server_process:
            self.server_process.terminate()
            self.server_process = None
        self.is_running = False

    def open_browser(self, icon=None, item=None):
        webbrowser.open(API_URL)

    def on_exit(self, icon, item):
        logging.info("Exiting launcher...")
        self.stop_server()
        icon.stop()
        sys.exit(0)

    def run(self):
        try:
            logging.info("Initializing Tray Icon...")
            # Initial server start
            self.start_server()
            
            # Setup Tray Icon
            image = self.create_icon_image()
            menu = pystray.Menu(
                pystray.MenuItem("開啟介面", self.open_browser),
                pystray.MenuItem("重啟服務", self.restart_service),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", self.on_exit)
            )
            self.icon = pystray.Icon("File Guessr", image, "File Guessr (Running)", menu)
            logging.info("Tray icon running.")
            self.icon.run()
        except Exception as e:
            logging.error(f"Runtime error in launcher: {e}", exc_info=True)
            sys.exit(1)

    def restart_service(self, icon=None, item=None):
        self.stop_server()
        time.sleep(1)
        self.start_server()

if __name__ == "__main__":
    launcher = BackgroundLauncher()
    launcher.run()
