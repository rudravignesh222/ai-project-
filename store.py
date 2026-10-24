from uuid import uuid4
from typing import Any

PROJECTS: dict[str, dict[str, Any]] = {}

def save_project(topic: str, language: str, files: dict[str, str]) -> str:
    project_id = str(uuid4())
    PROJECTS[project_id] = {
        "id": project_id, "topic": topic, "language": language,
        "files": files, "created_at": __import__("datetime").datetime.utcnow().isoformat() + "Z"
    }
    return project_id
