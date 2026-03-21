import os
import subprocess
from pathlib import Path

def launch():
    # 1. Define paths
    # Update 'keys_folder/groq_key.txt' to the actual path of your notepad file
    key_file_path = Path(r"D:\\API_KEYS\\GROK_API_KEY.txt") 
    app_path = Path("ui/streamlit_app_v2.py")

    # 2. Read the API key from the notepad file
    if not key_file_path.exists():
        print(f"❌ Error: Key file not found at {key_file_path}")
        return

    try:
        with open(key_file_path, "r") as f:
            api_key = f.read().strip()
        
        if not api_key:
            print("❌ Error: Key file is empty.")
            return
            
        print("🔑 API Key loaded successfully.")
    except Exception as e:
        print(f"❌ Error reading key: {e}")
        return

    # 3. Set the environment variable for the current process
    # This is the Python equivalent of $env:GROQ_API_KEY = '...'
    os.environ["GROQ_API_KEY"] = api_key

    # 4. Run Streamlit as a subprocess
    # We include the --server.fileWatcherType none flag to prevent the Torch crash
    print(f"🚀 Launching Streamlit app: {app_path}...")
    
    cmd = [
        "python", "-m", "streamlit", "run", 
        str(app_path), 
        "--server.fileWatcherType", "none"
    ]

    try:
        # shell=True is often needed on Windows for python -m commands
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 App stopped by user.")
    except Exception as e:
        print(f"❌ Failed to launch app: {e}")

if __name__ == "__main__":
    launch()