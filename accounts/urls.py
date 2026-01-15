from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [

    # ================= AUTH =================
    path("login/seeker/", views.login_seeker, name="login_seeker"),
    path("login/company/", views.login_company, name="login_company"),
    path("logout/", views.logout_user, name="logout"),

    # ================= REGISTER =================
    path("register/seeker/", views.register_seeker, name="register_seeker"),
    path("register/company/", views.register_company, name="register_company"),

    # ================= EMAIL VERIFICATION =================
    path("verify/<str:token>/", views.verify_email, name="verify_email"),

    # ================= PROFILE SETUP (FORM) =================
    path(
        "seeker/profile/setup/",
        views.seeker_profile,
        name="seeker_profile_setup"
    ),
    path(
        "company/profile/setup/",
        views.company_profile,
        name="company_profile_setup"
    ),

    # ================= PROFILE VIEW (NAVBAR) =================
    path(
        "seeker/profile/",
        views.seeker_profile_view,
        name="seeker_profile_view"
    ),
    path(
        "company/profile/",
        views.company_profile_view,
        name="company_profile_view"
    ),

    # ================= PASSWORD RESET =================
    path("password/reset/", views.reset_password_request, name="reset_password_request"),
    path(
        "password/reset/<str:token>/",
        views.reset_password_confirm,
        name="reset_password_confirm"
    ),

    # ================= ACCOUNT =================
    path("delete/", views.delete_account, name="delete_account"),
]
