import re
from pathlib import PurePosixPath

BLOCKED_NAMES = {".env", ".env.local", ".env.production", "id_rsa", "id_ed25519"}
BLOCKED_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next", ".pytest_cache"}
SECRET_PATTERNS = [re.compile(r"(secret|token|credential|private.?key)", re.I)]

def safe_path(path: str) -> str:
    path = path.replace("\\", "/").strip()
    p = PurePosixPath(path)
    if not path or p.is_absolute() or any(part in ("..", "") for part in p.parts):
        raise ValueError(f"Unsafe file path: {path!r}")
    if ":" in path or path.startswith("/"):
        raise ValueError(f"Unsafe file path: {path!r}")
    if any(part in BLOCKED_DIRS for part in p.parts):
        raise ValueError(f"Blocked directory in path: {path!r}")
    if p.name.lower() in BLOCKED_NAMES or p.name.lower().startswith(".env."):
        raise ValueError(f"Blocked secret file: {path!r}")
    return str(p)

def clean_files(files: dict[str, str]) -> dict[str, str]:
    if not isinstance(files, dict) or not files:
        raise ValueError("No project files were provided.")
    if len(files) > 150:
        raise ValueError("Project exceeds the 150-file limit.")
    cleaned = {}
    total = 0
    for path, content in files.items():
        safe = safe_path(path)
        if not isinstance(content, str):
            raise ValueError(f"File content must be text: {path}")
        if len(content) > 500_000:
            raise ValueError(f"File too large: {path}")
        total += len(content.encode("utf-8"))
        if total > 5_000_000:
            raise ValueError("Project exceeds the 5 MB source limit.")
        cleaned[safe] = content
    return cleaned
