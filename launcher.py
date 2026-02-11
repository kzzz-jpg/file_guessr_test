import customtkinter as ctk
import subprocess
import webbrowser
import sys
import os
import threading
import pystray
from PIL import Image, ImageDraw
import time

# Configuration
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("File Guessr Launcher")
        self.geometry("400x450")
        self.resizable(False, False)
        
        # Server process management
        self.server_process = None
        self.is_running = False

        # Build UI
        self._build_ui()
        
        # System Tray setup
        self.tray_icon = None
        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

    def _build_ui(self):
        # Header
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.pack(pady=20, padx=20, fill="x")
        
        self.logo_label = ctk.CTkLabel(
            self.header_frame, 
            text="File Guessr", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.logo_label.pack(pady=10)
        
        self.status_label = ctk.CTkLabel(
            self.header_frame,
            text="Service Stopped",
            text_color="red",
            font=ctk.CTkFont(size=14)
        )
        self.status_label.pack(pady=(0, 10))

        # Controls
        self.controls_frame = ctk.CTkFrame(self)
        self.controls_frame.pack(pady=10, padx=20, fill="x")

        self.start_button = ctk.CTkButton(
            self.controls_frame,
            text="Start Service",
            command=self.start_server,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.start_button.pack(pady=10, padx=20, fill="x")

        self.stop_button = ctk.CTkButton(
            self.controls_frame,
            text="Stop Service",
            command=self.stop_server,
            state="disabled",
            fg_color="red",
            hover_color="darkred"
        )
        self.stop_button.pack(pady=10, padx=20, fill="x")

        self.browser_button = ctk.CTkButton(
            self.controls_frame,
            text="Open Web Interface",
            command=self.open_browser,
            state="disabled"
        )
        self.browser_button.pack(pady=10, padx=20, fill="x")
        
        # Options
        self.options_frame = ctk.CTkFrame(self)
        self.options_frame.pack(pady=20, padx=20, fill="x")
        
        self.web_url_label = ctk.CTkLabel(
            self.options_frame,
            text="http://127.0.0.1:8000",
            text_color="gray"
        )
        self.web_url_label.pack(pady=10)

    def start_server(self):
        if self.is_running:
            return

        try:
            # Start uvicorn as a subprocess
            cmd = [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"]
            
            # Create startup info to hide window
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # Start process and capture output
            self.server_process = subprocess.Popen(
                cmd, 
                startupinfo=startupinfo,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Check if it died immediately
            try:
                stdout, stderr = self.server_process.communicate(timeout=1.0)
                # If we get here, the process finished (crashed)
                self.status_label.configure(text=f"Failed: {stderr or 'Unknown error'}", text_color="red")
                self.server_process = None
                return
            except subprocess.TimeoutExpired:
                # Process is still running, which is good!
                pass
            
            self.is_running = True
            self.status_label.configure(text="Service Running", text_color="green")
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            self.browser_button.configure(state="normal")
            
            # Auto-open browser
            self.after(2000, self.open_browser)
            
            # Start monitoring thread
            threading.Thread(target=self.monitor_process, daemon=True).start()
            
        except Exception as e:
            self.status_label.configure(text=f"Error: {str(e)}", text_color="red")

    def monitor_process(self):
        """Monitor the server process."""
        while self.is_running and self.server_process:
            if self.server_process.poll() is not None:
                # Process died
                _, stderr = self.server_process.communicate()
                self.after(0, lambda msg=stderr: self.status_label.configure(
                    text=f"Crashed: {msg[:50]}..." if msg else "Service Crashed", 
                    text_color="red"
                ))
                self.after(0, self.stop_server)
                break
            time.sleep(1)

    def stop_server(self):
        if self.server_process:
            self.server_process.terminate()
            self.server_process = None
        
        self.is_running = False
        self.status_label.configure(text="Service Stopped", text_color="red")
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.browser_button.configure(state="disabled")

    def open_browser(self):
        webbrowser.open("http://127.0.0.1:8000")

    def create_image(self):
        # Generate a simple icon
        width = 64
        height = 64
        color1 = (108, 92, 231) # #6c5ce7
        color2 = (255, 255, 255)
        image = Image.new('RGB', (width, height), color1)
        dc = ImageDraw.Draw(image)
        dc.rectangle((width // 4, height // 4, width * 3 // 4, height * 3 // 4), fill=color2)
        return image

    def minimize_to_tray(self):
        self.withdraw()
        if not self.tray_icon:
            image = self.create_image()
            menu = (
                pystray.MenuItem("Open", self.show_window),
                pystray.MenuItem("Stop Service", self.stop_server_from_tray),
                pystray.MenuItem("Exit", self.quit_app)
            )
            self.tray_icon = pystray.Icon("File Guessr", image, "File Guessr", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.after(0, self.deiconify)

    def stop_server_from_tray(self):
        self.after(0, self.stop_server)

    def quit_app(self, icon=None, item=None):
        self.stop_server()
        if self.tray_icon:
            self.tray_icon.stop()
        self.quit()
        sys.exit()

if __name__ == "__main__":
    app = App()
    app.mainloop()
