"""
Shared key loader for evaluation scripts.

Mirrors the pattern in launch_app.py: reads API keys from text files under
D:\\API_KEYS\\ and injects them into os.environ.

Expected files:
  D:\\API_KEYS\\GROK_API_KEY.txt        -> GROQ_API_KEY
  D:\\API_KEYS\\GEMINI_API_KEY.txt      -> GEMINI_API_KEY
  D:\\API_KEYS\\OPENROUTER_API_KEY.txt  -> OPENROUTER_API_KEY

Gemini key:     https://aistudio.google.com/app/apikey
OpenRouter key: https://openrouter.ai/keys
"""

import os
from pathlib import Path

_KEY_DIR = Path(r"D:\\API_KEYS")


def _load_key(env_var: str, filename: str, required: bool = True) -> str | None:
    if os.environ.get(env_var):
        return os.environ[env_var]
    key_file = _KEY_DIR / filename
    if not key_file.exists():
        if required:
            raise RuntimeError(
                f"{env_var} not in environment and key file not found at {key_file}"
            )
        return None
    key = key_file.read_text().strip()
    if not key:
        if required:
            raise RuntimeError(f"Key file is empty: {key_file}")
        return None
    os.environ[env_var] = key
    print(f"Loaded {env_var} from key file.")
    return key


def load_groq_api_key() -> str:
    return _load_key("GROQ_API_KEY", "GROK_API_KEY.txt", required=True)


def load_gemini_api_key() -> str | None:
    return _load_key("GEMINI_API_KEY", "GEMINI_API_KEY.txt", required=False)


def load_openrouter_api_key() -> str | None:
    return _load_key("OPENROUTER_API_KEY", "OPENROUTER_API_KEY.txt", required=False)


def load_all_available_keys() -> dict:
    """Load all keys that are available. Returns dict of env_var -> key."""
    keys = {}
    groq = load_groq_api_key()
    if groq:
        keys["GROQ_API_KEY"] = groq
    gemini = load_gemini_api_key()
    if gemini:
        keys["GEMINI_API_KEY"] = gemini
    openrouter = load_openrouter_api_key()
    if openrouter:
        keys["OPENROUTER_API_KEY"] = openrouter
    return keys
