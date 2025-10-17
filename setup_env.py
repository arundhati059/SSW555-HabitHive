import os
import subprocess
import sys

# Name of the virtual environment folder
venv_name = "venv"

# 1. Create virtual environment
if not os.path.exists(venv_name):
    subprocess.check_call([sys.executable, "-m", "venv", venv_name])
    print(f"Virtual environment '{venv_name}' created.")
else:
    print(f"Virtual environment '{venv_name}' already exists.")

# 2. Install requirements
req_file = "requirements.txt"
if os.path.exists(req_file):
    # Use the pip inside the venv
    if os.name == "nt":
        pip_path = os.path.join(venv_name, "Scripts", "pip.exe")
    else:
        pip_path = os.path.join(venv_name, "bin", "pip")

    subprocess.check_call([pip_path, "install", "-r", req_file])
    print("Dependencies installed from requirements.txt")
else:
    print("No requirements.txt found. Skipping dependency installation.")
