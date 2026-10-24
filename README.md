# AI Project Builder

A full-stack starter application for generating project code with a server-side AI provider, previewing files, downloading a ZIP, and publishing to GitHub after OAuth authorization.

## Stack
- Frontend: React + Vite
- Backend: FastAPI
- AI: configurable OpenAI-compatible Chat Completions API (server-side only)
- GitHub: OAuth web flow + GitHub REST API
- ZIP: Python standard library

## Requirements
- Python 3.10+
- Node.js 20+
- An AI provider API key and compatible API URL/model for code generation
- A GitHub OAuth App for GitHub publishing (optional; local generation/download works without it)

## Quick start

### 1. Backend
```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env
# Edit .env. On macOS/Linux use: cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend
Open a second terminal:
```bash
cd frontend
npm install
npm run dev
```
Visit http://localhost:5173. Vite proxies `/api` to the backend.

## Configure AI
Set `AI_API_KEY`, `AI_BASE_URL`, and `AI_MODEL` in `backend/.env`. The base URL should be the provider's API base that supports `POST {AI_BASE_URL}/chat/completions`. The key is never sent to the browser. If the key is absent, generation returns a clear configuration error rather than fake output.

## Configure GitHub OAuth (optional)
1. Create a GitHub OAuth App in GitHub Developer Settings.
2. Set callback URL to `http://localhost:8000/api/github/callback`.
3. Set `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` in `backend/.env`.
4. Set a strong random `SESSION_SECRET`.
5. Restart the backend and use **Connect GitHub**.

The OAuth flow requests `repo` scope because publishing to private repositories and writing files requires repository access. GitHub access tokens are kept in backend memory keyed by an opaque session ID; restarting the backend clears sessions. For production, use a durable server-side session store, HTTPS, secure cookie settings, encryption at rest, CSRF protections, and a dedicated GitHub App where possible.

## Security notes
- Generated file paths are normalized and traversal paths are rejected.
- ZIPs exclude `.env`, `.git`, dependency folders, caches, build outputs, and credential-like files.
- Uploads are size-limited and accept PDF, DOCX, TXT, and common image types. PDF/DOCX text extraction requires optional parser libraries included in requirements.
- Publishing requires an explicit confirmation flag and re-validates file paths and blocked files.
- This is a functional starter, not a production security certification. Review generated code before running or publishing it. Never execute generated code on the server.

## API
- `POST /api/projects/analyze`
- `POST /api/projects/generate`
- `GET /api/projects/{project_id}/files`
- `GET /api/projects/{project_id}/download`
- `GET /api/github/login`
- `GET /api/github/callback`
- `GET /api/github/repositories`
- `POST /api/github/publish`

## Test
```bash
cd backend
pytest
```
