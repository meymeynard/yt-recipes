import os
import subprocess
import re
from pathlib import Path

def get_youtube_api_key() -> str:
    """Retrieve YouTube API key from environment or by decrypting ~/.config/sops/secrets.enc.env"""
    # 1. Check direct env variable
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if api_key:
        clean_key = api_key.strip().strip('"').strip("'")
        if clean_key:
            return clean_key

    # 2. Try decrypting SOPS env file
    sops_path = Path(os.environ.get("SOPS_SECRETS_FILE", Path.home() / ".config/sops/secrets.enc.env"))
    if sops_path.exists():
        try:
            output = subprocess.check_output(["sops", "-d", str(sops_path)], stderr=subprocess.DEVNULL).decode("utf-8")
            for line in output.splitlines():
                line = line.strip()
                if line.startswith("YOUTUBE_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception as e:
            print(f"Warning: Failed to decrypt SOPS config: {e}")

    # 3. Fallback: check .env in current directory
    local_env = Path(".env")
    if local_env.exists():
        for line in local_env.read_text().splitlines():
            if line.startswith("YOUTUBE_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")

    raise RuntimeError("YOUTUBE_API_KEY not found in environment or SOPS file.")
