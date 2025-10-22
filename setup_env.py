import os
import subprocess
import sys

#python script
#what this does is create a virtual enviornment to run the project fresh without comflicts from your local machine
#Just hit run and it should create a "venv" Folder, then if using vscode, you can select the Interpreter of the created virtual env
# I created ths for me just so i dont run into errors with the packages or library and to save space when trying to run the APP

# 1. Create virtual environment
# Name of the virtual environment folder
venv_name = "venv"

if not os.path.exists(venv_name):
    subprocess.check_call([sys.executable, "-m", "venv", venv_name])
    print(f"Virtual environment '{venv_name}' created.")
else:
    print(f"Virtual environment '{venv_name}' already exists.")

# 2. Install requirements safely
req_file = "requirements.txt"
if os.path.exists(req_file):
    # Determine pip path inside venv
    if os.name == "nt":
        pip_path = os.path.join(venv_name, "Scripts", "pip.exe")
    else:
        pip_path = os.path.join(venv_name, "bin", "pip")

    # Read packages from requirements.txt
    with open(req_file) as f:
        packages = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    for pkg in packages:
        print(f"Installing {pkg} ...")
        try:
            subprocess.check_call([pip_path, "install", pkg])
            print(f"{pkg} installed successfully!\n")
        except subprocess.CalledProcessError:
            print(f"⚠️  Failed to install {pkg}, skipping...\n")

    print("Finished installing dependencies (errors ignored).")
else:
    print("No requirements.txt found. Skipping dependency installation.")

# Terminal command to activate the venv:
# Windows PowerShell: .\venv\Scripts\Activate.ps1
# macOS/Linux: source: ./venv/bin/activate OR source venv/bin/activate
# use this command to grant permission: chmod +x venv/bin/activate
# To get out of venv, just put: deactivate

# Python 3.14 is way too new, downgradeed to 3.13 for packages
# now i get no error!
