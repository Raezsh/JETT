from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.http import JsonResponse
from django.urls import reverse
from django.conf import settings
from django.db import transaction
import uuid
import hashlib

from .models import (
    CustomUser,
    EmailVerification,
    SeekerProfile,
    CompanyProfile,
    PasswordResetToken,
)
from .forms import RegisterSeekerForm, RegisterCompanyForm, LoginForm


# ==================================================
# UTILITIES
# ==================================================
def generate_token():
    raw_token = uuid.uuid4().hex
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    return raw_token, token_hash


def send_verification_email(request, user, raw_token, subject, intro_text):
    verify_url = request.build_absolute_uri(
        reverse("accounts:verify_email", args=[raw_token])
    )

    send_mail(
        subject=subject,
        message=f"""
Halo {user.full_name},

{intro_text}

Silakan klik tautan berikut untuk verifikasi akun Anda:

{verify_url}

Jika ini bukan Anda, silakan abaikan email ini.

—
JETT | Job Explore Top Talent
        """,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


# ==================================================
# REGISTER SEEKER
# ==================================================
def register_seeker(request):
    if request.method == "POST":
        form = RegisterSeekerForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.role = "seeker"
                    user.is_active = False
                    user.save()

                    raw_token, token_hash = generate_token()

                    EmailVerification.objects.create(
                        user=user,
                        token_hash=token_hash
                    )

                    send_verification_email(
                        request,
                        user,
                        raw_token,
                        "Verifikasi Email Akun JETT",
                        "Terima kasih telah mendaftar sebagai pencari kerja di JETT."
                    )

                return JsonResponse({"status": "success"})
            except Exception as e:
                return JsonResponse({"status": "error", "message": str(e)})

        return JsonResponse({"status": "error", "errors": form.errors})

    return render(request, "accounts/register_seeker.html", {
        "form": RegisterSeekerForm()
    })


# ==================================================
# REGISTER COMPANY
# ==================================================
def register_company(request):
    if request.method == "POST":
        form = RegisterCompanyForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.role = "company"
                    user.is_active = False
                    user.save()

                    raw_token, token_hash = generate_token()

                    EmailVerification.objects.create(
                        user=user,
                        token_hash=token_hash
                    )

                    send_verification_email(
                        request,
                        user,
                        raw_token,
                        "Verifikasi Email Perusahaan JETT",
                        "Terima kasih telah mendaftarkan akun perusahaan di JETT."
                    )

                return JsonResponse({"status": "success"})
            except Exception as e:
                return JsonResponse({"status": "error", "message": str(e)})

        return JsonResponse({"status": "error", "errors": form.errors})

    return render(request, "accounts/register_company.html", {
        "form": RegisterCompanyForm()
    })


# ==================================================
# LOGIN
# ==================================================
def login_seeker(request):
    return _login_user(request, role="seeker")


def login_company(request):
    return _login_user(request, role="company")


def _login_user(request, role):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
            )

            if not user or user.role != role or not user.is_active:
                return JsonResponse({"status": "error"})

            login(request, user)
            return JsonResponse({"status": "success"})

        return JsonResponse({"status": "error", "errors": form.errors})

    return render(request, f"accounts/login_{role}.html", {
        "form": LoginForm()
    })


# ==================================================
# EMAIL VERIFICATION
# ==================================================
def verify_email(request, token):
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    verification = get_object_or_404(
        EmailVerification,
        token_hash=token_hash,
        is_used=False
    )

    user = verification.user
    user.is_active = True
    user.email_verified = True
    user.save()

    verification.is_used = True
    verification.save()

    login(request, user)

    if user.role == "seeker":
        return redirect("accounts:seeker_profile_setup")

    return redirect("accounts:company_profile_setup")


# ==================================================
# PROFILE SETUP (FORM SETELAH VERIF)
# ==================================================
@login_required
def seeker_profile(request):
    if request.user.role != "seeker":
        return redirect("/")

    profile, _ = SeekerProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        profile.date_of_birth = request.POST.get("date_of_birth") or None
        profile.address = request.POST.get("address")
        profile.phone = request.POST.get("phone")
        profile.education = request.POST.get("education")
        profile.save()

        # SETELAH LENGKAP → CARI KERJA
        return redirect("jobs:job_list")

    return render(request, "accounts/seeker_profile.html", {
        "seeker_profile": profile
    })


@login_required
def company_profile(request):
    if request.user.role != "company":
        return redirect("/")

    profile, _ = CompanyProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        profile.owner_name = request.POST.get("owner_name")
        profile.address = request.POST.get("address")
        profile.phone = request.POST.get("phone")
        profile.industry = request.POST.get("industry")
        profile.description = request.POST.get("description")

        if request.FILES.get("logo"):
            profile.logo = request.FILES["logo"]

        profile.save()

        # SETELAH LENGKAP → DASHBOARD EMPLOYER
        return redirect("jobs:employer_home")

    return render(request, "accounts/company_profile.html", {
        "company_profile": profile
    })


# ==================================================
# PROFILE VIEW (READ ONLY – NAVBAR)
# ==================================================
@login_required
def seeker_profile_view(request):
    if request.user.role != "seeker":
        return redirect("/")

    profile = get_object_or_404(
        SeekerProfile,
        user=request.user
    )

    return render(request, "accounts/seeker_profile_view.html", {
        "seeker_profile": profile
    })


@login_required
def company_profile_view(request):
    if request.user.role != "company":
        return redirect("/")

    profile = get_object_or_404(
        CompanyProfile,
        user=request.user
    )

    return render(request, "accounts/company_profile_view.html", {
        "company_profile": profile
    })


# ==================================================
# PASSWORD RESET
# ==================================================
def reset_password_request(request):
    if request.method == "POST":
        email = request.POST.get("email")

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return JsonResponse({"status": "error"})

        PasswordResetToken.objects.filter(
            user=user,
            is_used=False
        ).update(is_used=True)

        raw_token, token_hash = generate_token()

        PasswordResetToken.objects.create(
            user=user,
            token_hash=token_hash
        )

        reset_url = request.build_absolute_uri(
            reverse("accounts:reset_password_confirm", args=[raw_token])
        )

        send_mail(
            subject="Reset Password Akun JETT",
            message=f"Klik link berikut untuk reset password:\n{reset_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,
        )

        return JsonResponse({"status": "success"})

    return JsonResponse({"status": "error"})


def reset_password_confirm(request, token):
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    reset_obj = get_object_or_404(
        PasswordResetToken,
        token_hash=token_hash,
        is_used=False
    )

    if request.method == "POST":
        if request.POST.get("password") != request.POST.get("password2"):
            return render(request, "accounts/reset_password_confirm.html", {
                "error": "Password tidak sama"
            })

        user = reset_obj.user
        user.set_password(request.POST.get("password"))
        user.save()

        reset_obj.is_used = True
        reset_obj.save()

        messages.success(request, "Password berhasil direset.")
        return redirect("/")

    return render(request, "accounts/reset_password_confirm.html")


# ==================================================
# LOGOUT & DELETE
# ==================================================
def logout_user(request):
    logout(request)
    return redirect("/")


@login_required
def delete_account(request):
    request.user.delete()
    return redirect("/")
