import json, re
import httpx
from .config import settings

SYSTEM_PROMPT = '''You are a senior software engineer generating a complete, coherent software project.
Return ONLY valid JSON with this shape:
{"project_name":"short-name","summary":"one sentence","files":{"relative/path.ext":"complete file content"}}
Generate real, runnable source files, not placeholders. Include README.md, .gitignore, .env.example (with placeholders only), and dependency manifests appropriate to the selected stack. Do not include secrets, real credentials, binaries, node_modules, virtual environments, or generated build output. Keep the scope appropriate to the user's requirements. Use safe relative file paths. The JSON must be parseable; escape newlines in strings correctly.'''

async def generate_code(topic: str, language: str) -> dict:
    if not settings.ai_api_key:
        raise RuntimeError("AI provider is not configured. Set AI_API_KEY in backend/.env.")
    url = settings.ai_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.ai_model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Preferred language/framework: {language}\nProject specification:\n{topic}\nGenerate the project now."}
        ]
    }
    async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
        response = await client.post(url, headers={"Authorization": f"Bearer {settings.ai_api_key}"}, json=payload)
        response.raise_for_status()
        data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("The AI provider returned an invalid project response. Try a more specific prompt.") from exc
    if not isinstance(parsed.get("files"), dict):
        raise RuntimeError("The AI response did not contain a valid files object.")
    return parsed
