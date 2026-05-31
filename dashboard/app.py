import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from jinja2 import Environment, FileSystemLoader

from config import DASHBOARD_SESSION_SECRET, TENANTS_DIR
from services.tenant_db import TenantSettingsRepository, slugify_tenant

app = FastAPI(title="Bot Control Dashboard")
app.add_middleware(
    SessionMiddleware,
    secret_key=DASHBOARD_SESSION_SECRET,
    session_cookie="bot_dashboard_session",
)
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Initialize Jinja2 environment directly
jinja_env = Environment(loader=FileSystemLoader(str(BASE_DIR / "templates")))

def render_template(template_name: str, context: dict) -> str:
    """Render a Jinja2 template with the given context."""
    template = jinja_env.get_template(template_name)
    return template.render(**context)

def create_template_response(template_name: str, context: dict, status_code: int = 200):
    """Create an HTML response from a Jinja2 template."""
    html = render_template(template_name, context)
    return HTMLResponse(content=html, status_code=status_code)


def is_authenticated(request: Request) -> bool:
    return request.session.get("is_authenticated") is True


def redirect_to_login() -> RedirectResponse:
    return RedirectResponse(url="/login", status_code=303)


def get_current_tenant_slug(request: Request) -> str | None:
    value = request.session.get("tenant_slug")
    return value if isinstance(value, str) and value else None


def get_current_repo(request: Request) -> TenantSettingsRepository:
    tenant_slug = get_current_tenant_slug(request)
    if tenant_slug is None:
        raise ValueError("Tenant session is missing")

    return TenantSettingsRepository.for_slug(TENANTS_DIR, tenant_slug)


@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request) -> HTMLResponse:
    if not is_authenticated(request):
        return redirect_to_login()

    try:
        repo = get_current_repo(request)
    except ValueError:
        request.session.clear()
        return redirect_to_login()

    data = repo.get_dashboard_data()
    context = {
        "request": request,
        "message": "",
        "error": "",
        "tenant_slug": str(data["tenant_slug"]),
        "tenant_name": str(data["tenant_name"]),
        "bot_token": str(data["bot_token"]),
        "webhook_url": str(data["webhook_url"]),
        "form_json": str(data["form_json"]),
    }
    return create_template_response("dashboard.html", context)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    if is_authenticated(request):
        return RedirectResponse(url="/", status_code=303)

    return create_template_response(
        "login.html",
        {
            "request": request,
            "message": "",
            "error": "",
        }
    )




@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request) -> HTMLResponse:
    if is_authenticated(request):
        return RedirectResponse(url="/", status_code=303)

    context = {
        "request": request,
        "message": "",
        "error": "",
    }
    return create_template_response("register.html", context)


@app.post("/register", response_class=HTMLResponse)
async def register_action(
    request: Request,
    tenant_slug: str = Form(...),
    tenant_name: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
) -> HTMLResponse:
    if password != confirm_password:
        context = {
            "request": request,
            "message": "",
            "error": "Password and confirm password do not match",
        }
        return create_template_response("register.html", context, status_code=400)

    try:
        repo = TenantSettingsRepository.create_tenant(
            tenants_dir=TENANTS_DIR,
            tenant_slug=tenant_slug,
            tenant_name=tenant_name,
            admin_username=username,
            admin_password=password,
        )
    except ValueError as exc:
        context = {
            "request": request,
            "message": str(""),
            "error": str(exc),
        }
        return create_template_response("register.html", context, status_code=400)

    normalized_slug = repo.get_tenant_info()["slug"]
    request.session["is_authenticated"] = True
    request.session["tenant_slug"] = normalized_slug
    request.session["username"] = username.strip()
    return RedirectResponse(url="/", status_code=303)


@app.post("/login", response_class=HTMLResponse)
async def login_action(
    request: Request,
    tenant_slug: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
) -> HTMLResponse:
    try:
        normalized_slug = slugify_tenant(tenant_slug)
        repo = TenantSettingsRepository.for_slug(TENANTS_DIR, normalized_slug)
    except ValueError:
        context = {
            "request": request,
            "message": "",
            "error": "Tenant not found",
        }
        return create_template_response("login.html", context, status_code=404)

    if repo.verify_admin_credentials(username=username, password=password):
        request.session["is_authenticated"] = True
        request.session["tenant_slug"] = normalized_slug
        request.session["username"] = username.strip()
        return RedirectResponse(url="/", status_code=303)

    context = {
        "request": request,
        "message": "",
        "error": "Invalid username or password",
    }
    return create_template_response("login.html", context, status_code=401)


@app.post("/logout")
async def logout_action(request: Request) -> RedirectResponse:
    request.session.clear()
    return redirect_to_login()


@app.post("/settings/general", response_class=HTMLResponse)
async def update_general(
    request: Request,
    bot_token: str = Form(...),
    webhook_url: str = Form(...),
) -> HTMLResponse:
    if not is_authenticated(request):
        return redirect_to_login()

    try:
        repo = get_current_repo(request)
        repo.update_general(bot_token=bot_token, webhook_url=webhook_url)
        data = repo.get_dashboard_data()
        context = {
            "request": request,
            "message": "General settings updated successfully.",
            "error": "",
            "tenant_slug": str(data["tenant_slug"]),
            "tenant_name": str(data["tenant_name"]),
            "bot_token": str(data["bot_token"]),
            "webhook_url": str(data["webhook_url"]),
            "form_json": str(data["form_json"]),
        }
        return create_template_response("dashboard.html", context)
    except ValueError as exc:
        try:
            repo = get_current_repo(request)
            data = repo.get_dashboard_data()
        except ValueError:
            request.session.clear()
            return redirect_to_login()

        context = {
            "request": request,
            "message": "",
            "error": str(exc),
            "tenant_slug": str(data["tenant_slug"]),
            "tenant_name": str(data["tenant_name"]),
            "bot_token": str(data["bot_token"]),
            "webhook_url": str(data["webhook_url"]),
            "form_json": str(data["form_json"]),
        }
        return create_template_response("dashboard.html", context, status_code=400)


@app.post("/settings/form", response_class=HTMLResponse)
async def update_form(request: Request, form_json: str = Form(...)) -> HTMLResponse:
    if not is_authenticated(request):
        return redirect_to_login()

    try:
        repo = get_current_repo(request)
    except ValueError:
        request.session.clear()
        return redirect_to_login()

    try:
        parsed_form = json.loads(form_json)
    except json.JSONDecodeError as exc:
        data = repo.get_dashboard_data()
        context = {
            "request": request,
            "message": "",
            "error": f"Invalid JSON format: {exc.msg}",
            "tenant_slug": str(data["tenant_slug"]),
            "tenant_name": str(data["tenant_name"]),
            "bot_token": str(data["bot_token"]),
            "webhook_url": str(data["webhook_url"]),
            "form_json": str(data["form_json"]),
        }
        return create_template_response("dashboard.html", context, status_code=400)

    try:
        repo.update_form(parsed_form)
        data = repo.get_dashboard_data()
        context = {
            "request": request,
            "message": "Form configuration updated successfully.",
            "error": "",
            "tenant_slug": str(data["tenant_slug"]),
            "tenant_name": str(data["tenant_name"]),
            "bot_token": str(data["bot_token"]),
            "webhook_url": str(data["webhook_url"]),
            "form_json": str(data["form_json"]),
        }
        return create_template_response("dashboard.html", context)
    except ValueError as exc:
        data = repo.get_dashboard_data()
        context = {
            "request": request,
            "message": "",
            "error": str(exc),
            "tenant_slug": str(data["tenant_slug"]),
            "tenant_name": str(data["tenant_name"]),
            "bot_token": str(data["bot_token"]),
            "webhook_url": str(data["webhook_url"]),
            "form_json": str(data["form_json"]),
        }
        return create_template_response("dashboard.html", context, status_code=400)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/restart")
async def restart_placeholder(request: Request) -> RedirectResponse:
    if not is_authenticated(request):
        return redirect_to_login()

    # Runtime restart orchestration can be added later via process manager.
    return RedirectResponse(url="/", status_code=303)

