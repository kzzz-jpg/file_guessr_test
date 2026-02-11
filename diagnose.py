import sys
import os

print(f"Python Executable: {sys.executable}")
print(f"Python Version: {sys.version}")
print(f"CWD: {os.getcwd()}")
print("sys.path:")
for p in sys.path:
    print(f"  {p}")

print("\nAttempting import customtkinter...")
try:
    import customtkinter
    print(f"SUCCESS: customtkinter found at {customtkinter.__file__}")
except ImportError as e:
    print(f"FAILURE: {e}")

print("\nInstalled packages (pip freeze):")
try:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "freeze"])
except Exception as e:
    print(f"Failed to run pip freeze: {e}")
