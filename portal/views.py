import json
from functools import wraps

from django.contrib import messages
from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render

from config import TENANTS_DIR
from services.tenant_db import TenantSettingsRepository, slugify_tenant
from .forms import BotProfileJsonForm, FormJsonForm, GeneralSettingsForm, LoginForm, TenantCreateForm


def _repo_for_session(request: HttpRequest) -> TenantSettingsRepository:
    tenant_slug = request.session.get("tenant_slug")
    if not isinstance(tenant_slug, str) or not tenant_slug:
        raise ValueError("Tenant is not selected")
    return TenantSettingsRepository.for_slug(TENANTS_DIR, tenant_slug)


def tenant_login_required(view_func):
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not request.session.get("is_authenticated"):
            return redirect("login")
        return view_func(request, *args, **kwargs)

    return wrapper


def index(request: HttpRequest) -> HttpResponse:
    if request.session.get("is_authenticated"):
        return redirect("dashboard")
    return redirect("login")


def login_view(request: HttpRequest) -> HttpResponse:
    if request.session.get("is_authenticated"):
        return redirect("dashboard")

    form = LoginForm(request.POST or None)
    error = ""

    if request.method == "POST" and form.is_valid():
        tenant_slug = slugify_tenant(form.cleaned_data["tenant_slug"])
        try:
            repo = TenantSettingsRepository.for_slug(TENANTS_DIR, tenant_slug)
        except ValueError:
            error = "Tenant not found"
        else:
            if repo.verify_admin_credentials(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
            ):
                request.session["is_authenticated"] = True
                request.session["tenant_slug"] = tenant_slug
                request.session["username"] = form.cleaned_data["username"].strip()
                return redirect("dashboard")
            error = "Invalid username or password"

    return render(request, "portal/login.html", {"form": form, "error": error})


def register_view(request: HttpRequest) -> HttpResponse:
    if request.session.get("is_authenticated"):
        return redirect("dashboard")

    form = TenantCreateForm(request.POST or None)
    error = ""

    if request.method == "POST" and form.is_valid():
        try:
            repo = TenantSettingsRepository.create_tenant(
                tenants_dir=TENANTS_DIR,
                tenant_slug=form.cleaned_data["tenant_slug"],
                tenant_name=form.cleaned_data["tenant_name"],
                admin_username=form.cleaned_data["username"],
                admin_password=form.cleaned_data["password"],
            )
        except ValueError as exc:
            error = str(exc)
        else:
            request.session["is_authenticated"] = True
            request.session["tenant_slug"] = repo.get_tenant_info()["slug"]
            request.session["username"] = form.cleaned_data["username"].strip()
            return redirect("dashboard")

    return render(request, "portal/register.html", {"form": form, "error": error})


@tenant_login_required
def dashboard_view(request: HttpRequest) -> HttpResponse:
    try:
        repo = _repo_for_session(request)
    except ValueError:
        request.session.flush()
        return redirect("login")

    data = repo.get_dashboard_data()
    context = {
        "tenant_slug": data["tenant_slug"],
        "tenant_name": data["tenant_name"],
        "general_form": GeneralSettingsForm(
            initial={"bot_token": data["bot_token"], "webhook_url": data["webhook_url"]}
        ),
        "form_form": FormJsonForm(initial={"form_json": data["form_json"]}),
        "profile_form": BotProfileJsonForm(initial={"bot_profile_json": data["bot_profile_json"]}),
    }
    return render(request, "portal/dashboard.html", context)


@tenant_login_required
def update_general_view(request: HttpRequest) -> HttpResponse:
    try:
        repo = _repo_for_session(request)
    except ValueError:
        request.session.flush()
        return redirect("login")

    form = GeneralSettingsForm(request.POST or None)
    data = repo.get_dashboard_data()

    if request.method == "POST" and form.is_valid():
        try:
            repo.update_general(
                bot_token=form.cleaned_data["bot_token"],
                webhook_url=form.cleaned_data["webhook_url"],
            )
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "General settings updated successfully.")
            return redirect("dashboard")
    elif request.method == "POST":
        messages.error(request, "Please correct the form errors.")

    context = {
        "general_form": form,
        "form_form": FormJsonForm(initial={"form_json": data["form_json"]}),
        "profile_form": BotProfileJsonForm(initial={"bot_profile_json": data["bot_profile_json"]}),
        "tenant_slug": data["tenant_slug"],
        "tenant_name": data["tenant_name"],
    }
    return render(request, "portal/dashboard.html", context)


@tenant_login_required
def update_form_view(request: HttpRequest) -> HttpResponse:
    try:
        repo = _repo_for_session(request)
    except ValueError:
        request.session.flush()
        return redirect("login")

    form = FormJsonForm(request.POST or None)
    data = repo.get_dashboard_data()

    if request.method == "POST" and form.is_valid():
        try:
            parsed_form = json.loads(form.cleaned_data["form_json"])
            repo.update_form(parsed_form)
        except json.JSONDecodeError as exc:
            messages.error(request, f"Invalid JSON format: {exc.msg}")
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Form configuration updated successfully.")
            return redirect("dashboard")
    elif request.method == "POST":
        messages.error(request, "Please correct the form errors.")

    context = {
        "general_form": GeneralSettingsForm(initial={"bot_token": data["bot_token"], "webhook_url": data["webhook_url"]}),
        "form_form": form,
        "profile_form": BotProfileJsonForm(initial={"bot_profile_json": data["bot_profile_json"]}),
        "tenant_slug": data["tenant_slug"],
        "tenant_name": data["tenant_name"],
    }
    return render(request, "portal/dashboard.html", context)


@tenant_login_required
def update_profile_view(request: HttpRequest) -> HttpResponse:
    try:
        repo = _repo_for_session(request)
    except ValueError:
        request.session.flush()
        return redirect("login")

    form = BotProfileJsonForm(request.POST or None)
    data = repo.get_dashboard_data()

    if request.method == "POST" and form.is_valid():
        try:
            parsed_profile = json.loads(form.cleaned_data["bot_profile_json"])
            repo.update_bot_profile(parsed_profile)
        except json.JSONDecodeError as exc:
            messages.error(request, f"Invalid bot profile JSON format: {exc.msg}")
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Bot profile updated successfully.")
            return redirect("dashboard")
    elif request.method == "POST":
        messages.error(request, "Please correct the bot profile form errors.")

    context = {
        "general_form": GeneralSettingsForm(initial={"bot_token": data["bot_token"], "webhook_url": data["webhook_url"]}),
        "form_form": FormJsonForm(initial={"form_json": data["form_json"]}),
        "profile_form": form,
        "tenant_slug": data["tenant_slug"],
        "tenant_name": data["tenant_name"],
    }
    return render(request, "portal/dashboard.html", context)


def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("login")
