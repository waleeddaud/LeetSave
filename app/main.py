from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse

from api.v1.router import api_router
from config import get_settings

settings = get_settings()
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="LeetSave API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok", "env": settings.app_env}


def _render_page(filename: str) -> HTMLResponse:
    path = STATIC_DIR / filename
    return HTMLResponse(path.read_text(encoding="utf-8"))


@app.get("/", response_class=HTMLResponse)
def onboarding():
    return _render_page("onboarding.html")


@app.get("/onboarding", response_class=HTMLResponse)
def onboarding_alias():
    return _render_page("onboarding.html")


@app.get("/onboarding/success", response_class=HTMLResponse)
def onboarding_success():
    return _render_page("success.html")


@app.get("/onboarding/error", response_class=HTMLResponse)
def onboarding_error(reason: str = "unknown"):
    page = (STATIC_DIR / "error.html").read_text(encoding="utf-8")
    return HTMLResponse(page.replace("{{reason}}", reason))


@app.get("/github/callback")
def legacy_github_callback(code: str):
    return RedirectResponse(f"/api/v1/auth/github/callback?code={code}")

