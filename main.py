import io, json, secrets, time, urllib.parse, zipfile
from typing import Optional
import httpx
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware
from .config import settings
from .store import PROJECTS, save_project
from .security import clean_files
from .ai import generate_code

app = FastAPI(title=settings.app_name, version="1.0.0")
# OAuth tokens remain in backend memory; only an opaque session key is stored in the signed cookie.
GITHUB_TOKENS: dict[str, str] = {}
def session_key(request: Request) -> str:
    key = request.session.get("session_key")
    if not key:
        key = secrets.token_urlsafe(32)
        request.session["session_key"] = key
    return key
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret, same_site="lax", https_only=settings.cookie_secure, max_age=3600)
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_url], allow_credentials=True, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type"])

class AnalyzeRequest(BaseModel):
    topic: str = Field(min_length=10, max_length=30000)
    language: str = "React + FastAPI"

class GenerateRequest(BaseModel):
    topic: str = Field(min_length=10, max_length=30000)
    language: str = "React + FastAPI"

class PublishRequest(BaseModel):
    project_id: str
    repo_name: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    description: str = Field(default="", max_length=350)
    visibility: str = "private"
    branch: str = Field(default="main", min_length=1, max_length=100)
    existing_repo: Optional[str] = None
    confirm: bool = False

@app.get("/api/health")
async def health():
    return {"status": "ok", "ai_configured": bool(settings.ai_api_key), "github_configured": bool(settings.github_client_id and settings.github_client_secret)}

async def extract_upload(upload: UploadFile) -> str:
    max_bytes = settings.max_upload_mb * 1024 * 1024
    raw = await upload.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise HTTPException(413, f"Upload exceeds {settings.max_upload_mb} MB.")
    name = (upload.filename or "").lower()
    try:
        if name.endswith(".txt"):
            return raw.decode("utf-8-sig", errors="replace")
        if name.endswith(".pdf"):
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(raw))
            return "\n".join(page.extract_text() or "" for page in reader.pages)[:30000]
        if name.endswith(".docx"):
            from docx import Document
            doc = Document(io.BytesIO(raw))
            return "\n".join(p.text for p in doc.paragraphs)[:30000]
        if name.endswith((".png", ".jpg", ".jpeg", ".webp")):
            # Image bytes are accepted, but OCR is deliberately not guessed. Ask user to paste text if OCR is needed.
            raise HTTPException(415, "Image upload is accepted only as a source attachment in a future OCR extension. Please paste the specification text or upload PDF/DOCX/TXT.")
        raise HTTPException(415, "Supported formats: PDF, DOCX, TXT, PNG, JPG, JPEG, WEBP.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"Could not extract text from upload: {exc}") from exc

@app.post("/api/projects/analyze")
async def analyze(request: Request, topic: str = Form(default=""), language: str = Form(default="React + FastAPI"), file: UploadFile | None = File(default=None)):
    if file and file.filename:
        extracted = await extract_upload(file)
        topic = (topic + "\n\n" + extracted).strip()
    if len(topic.strip()) < 10:
        raise HTTPException(422, "Enter at least 10 characters of project requirements.")
    # Analysis is deterministic and transparent; code generation is handled by the configured AI provider.
    return {"topic": topic[:30000], "language": language, "characters": len(topic), "suggested_checks": ["Define core user flows", "Identify data models and APIs", "Add validation and error handling", "Document environment variables", "Review generated code before execution"]}

@app.post("/api/projects/generate")
async def generate(request: Request, body: GenerateRequest):
    try:
        result = await generate_code(body.topic, body.language)
        files = clean_files(result["files"])
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        detail = "AI provider rejected the request or credentials."
        if status == 429: detail = "AI provider rate limit reached. Wait and try again."
        elif status >= 500: detail = "AI provider is temporarily unavailable."
        raise HTTPException(502, f"{detail} (provider status {status})") from exc
    except (httpx.HTTPError, RuntimeError) as exc:
        raise HTTPException(502, str(exc)) from exc
    project_id = save_project(body.topic, body.language, files)
    request.session["last_project_id"] = project_id
    ids = request.session.get("project_ids", [])
    if project_id not in ids: ids.append(project_id)
    request.session["project_ids"] = ids[-20:]
    return {"project_id": project_id, "project_name": result.get("project_name", "generated-project"), "summary": result.get("summary", ""), "file_count": len(files), "files": list(files.keys())}

def get_project(project_id: str, request: Request):
    project = PROJECTS.get(project_id)
    if not project:
        raise HTTPException(404, "Project not found or server restarted. Generate it again.")
    # Session binding helps prevent accidental cross-session access in this starter.
    owned = request.session.get("project_ids", [])
    if project_id not in owned and request.session.get("last_project_id") != project_id:
        # Keep API usable when session cookie is blocked only for local development? Fail closed.
        raise HTTPException(403, "This project is not associated with your session. Generate it in this browser session.")
    return project

@app.get("/api/projects/{project_id}/files")
async def project_files(project_id: str, request: Request):
    project = get_project(project_id, request)
    return {"project_id": project_id, "files": project["files"]}

@app.get("/api/projects/{project_id}/download")
async def download_project(project_id: str, request: Request):
    project = get_project(project_id, request)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, content in clean_files(project["files"]).items():
            archive.writestr(path, content)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="ai-project-{project_id[:8]}.zip"'})

def github_ready():
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(503, "GitHub OAuth is not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in backend/.env.")

@app.get("/api/github/login")
async def github_login(request: Request):
    github_ready()
    state = secrets.token_urlsafe(24)
    request.session["github_oauth_state"] = state
    params = {"client_id": settings.github_client_id, "redirect_uri": settings.github_callback_url, "scope": "repo", "state": state}
    return RedirectResponse("https://github.com/login/oauth/authorize?" + urllib.parse.urlencode(params))

@app.get("/api/github/callback")
async def github_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error:
        raise HTTPException(400, "GitHub authorization was cancelled or denied.")
    expected = request.session.pop("github_oauth_state", None)
    if not expected or not secrets.compare_digest(expected, state):
        raise HTTPException(400, "Invalid OAuth state. Restart GitHub connection.")
    if not code:
        raise HTTPException(400, "GitHub did not return an authorization code.")
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post("https://github.com/login/oauth/access_token", headers={"Accept": "application/json"}, data={"client_id": settings.github_client_id, "client_secret": settings.github_client_secret, "code": code, "redirect_uri": settings.github_callback_url})
        if resp.is_error:
            raise HTTPException(502, "GitHub token exchange failed.")
        token_data = resp.json()
    token = token_data.get("access_token")
    if not token:
        raise HTTPException(502, "GitHub did not return an access token.")
    # Keep the access token server-side; the browser receives only an opaque session key.
    GITHUB_TOKENS[session_key(request)] = token
    request.session["github_connected"] = True
    return RedirectResponse(settings.frontend_url + "?github=connected")

@app.get("/api/github/repositories")
async def github_repositories(request: Request):
    token = GITHUB_TOKENS.get(session_key(request))
    if not token:
        raise HTTPException(401, "Connect GitHub first.")
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get("https://api.github.com/user/repos?per_page=100&sort=updated", headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
    if resp.status_code == 401:
        GITHUB_TOKENS.pop(session_key(request), None)
        raise HTTPException(401, "GitHub authorization expired. Connect again.")
    if resp.status_code == 403:
        raise HTTPException(429, "GitHub rate limit or permission restriction. Try again later.")
    if resp.is_error:
        raise HTTPException(502, "Could not retrieve GitHub repositories.")
    return [{"full_name": r["full_name"], "name": r["name"], "private": r["private"], "default_branch": r.get("default_branch", "main"), "html_url": r["html_url"]} for r in resp.json()]

async def github_api(method: str, url: str, token: str, **kwargs):
    headers = kwargs.pop("headers", {})
    headers.update({"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.request(method, url, headers=headers, **kwargs)
    if response.status_code == 401: raise HTTPException(401, "GitHub authorization expired. Connect again.")
    if response.status_code == 403: raise HTTPException(429, "GitHub denied the request or rate limit was reached.")
    if response.is_error:
        try: detail = response.json().get("message", "GitHub API error")
        except Exception: detail = "GitHub API error"
        raise HTTPException(response.status_code if response.status_code < 500 else 502, f"GitHub API: {detail}")
    return response.json() if response.content else {}

@app.post("/api/github/publish")
async def publish(request: Request, body: PublishRequest):
    if not body.confirm:
        raise HTTPException(400, "Confirm the file review before publishing.")
    token = GITHUB_TOKENS.get(session_key(request))
    if not token:
        raise HTTPException(401, "Connect GitHub first.")
    project = get_project(body.project_id, request)
    files = clean_files(project["files"])
    if body.visibility not in ("public", "private"):
        raise HTTPException(422, "Visibility must be public or private.")
    if body.existing_repo:
        full_name = body.existing_repo
        if full_name.count("/") != 1:
            raise HTTPException(422, "Existing repository must be in owner/repository format.")
        repo = await github_api("GET", f"https://api.github.com/repos/{full_name}", token)
    else:
        repo = await github_api("POST", "https://api.github.com/user/repos", token, json={"name": body.repo_name, "description": body.description, "private": body.visibility == "private", "auto_init": True})
        full_name = repo["full_name"]
    branch = body.branch
    # Ensure branch exists; if empty repository has no branch, create one using Git Data API after handling.
    try:
        ref = await github_api("GET", f"https://api.github.com/repos/{full_name}/git/ref/heads/{urllib.parse.quote(branch, safe='')}", token)
        base_sha = ref["object"]["sha"]
        commit = await github_api("GET", f"https://api.github.com/repos/{full_name}/git/commits/{base_sha}", token)
        tree_sha = commit["tree"]["sha"]
    except HTTPException as exc:
        if exc.status_code != 404: raise
        # Empty repository: create initial blobs/tree/commit/ref.
        tree_items = []
        for path, content in files.items():
            blob = await github_api("POST", f"https://api.github.com/repos/{full_name}/git/blobs", token, json={"content": content, "encoding": "utf-8"})
            tree_items.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        tree = await github_api("POST", f"https://api.github.com/repos/{full_name}/git/trees", token, json={"tree": tree_items})
        new_commit = await github_api("POST", f"https://api.github.com/repos/{full_name}/git/commits", token, json={"message": "Publish generated project", "tree": tree["sha"], "parents": []})
        await github_api("POST", f"https://api.github.com/repos/{full_name}/git/refs", token, json={"ref": f"refs/heads/{branch}", "sha": new_commit["sha"]})
        return {"success": True, "repository_url": repo.get("html_url", f"https://github.com/{full_name}"), "commit_sha": new_commit["sha"], "files_published": len(files)}
    # Create blobs and a new tree based on the branch tree; preserves unrelated existing files.
    tree_items = []
    for path, content in files.items():
        blob = await github_api("POST", f"https://api.github.com/repos/{full_name}/git/blobs", token, json={"content": content, "encoding": "utf-8"})
        tree_items.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    tree = await github_api("POST", f"https://api.github.com/repos/{full_name}/git/trees", token, json={"base_tree": tree_sha, "tree": tree_items})
    new_commit = await github_api("POST", f"https://api.github.com/repos/{full_name}/git/commits", token, json={"message": "Publish generated project", "tree": tree["sha"], "parents": [base_sha]})
    await github_api("PATCH", f"https://api.github.com/repos/{full_name}/git/refs/heads/{urllib.parse.quote(branch, safe='')}", token, json={"sha": new_commit["sha"], "force": False})
    return {"success": True, "repository_url": repo.get("html_url", f"https://github.com/{full_name}"), "commit_sha": new_commit["sha"], "files_published": len(files)}
