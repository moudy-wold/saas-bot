from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("settings/general/", views.update_general_view, name="settings-general"),
    path("settings/form/", views.update_form_view, name="settings-form"),
    path("settings/profile/", views.update_profile_view, name="settings-profile"),
]
