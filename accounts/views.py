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
import pyotp
import qrcode
from io import BytesIO
import base64

from .models import (
    CustomUser,
    EmailVerification,
    SeekerProfile,
    CompanyProfile,
    PasswordResetToken,
    TOTPDevice,
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


def _generate_qr_code(user, secret):
    """Generate QR code sebagai base64 PNG untuk ditampilkan di template."""
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user.email,
        issuer_name="JETT Job Portal"
    )
    qr = qrcode.make(totp_uri)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()


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

            # ======= CEK TOTP =======
            try:
                totp_device = user.totp_device
                if totp_device.is_verified:
                    # Sudah setup TOTP → simpan di session, minta verifikasi
                    request.session["pre_mfa_user_id"] = str(user.id)
                    request.session["pre_mfa_role"] = role
                    return JsonResponse({"status": "require_mfa"})
            except TOTPDevice.DoesNotExist:
                pass

            # Belum setup TOTP → login dulu, lalu paksa setup
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return JsonResponse({"status": "setup_mfa"})

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

    # ← CEK EXPIRED
    if verification.is_expired():
        return render(request, "accounts/token_expired.html")

    user = verification.user
    user.is_active = True
    user.email_verified = True
    user.save()

    verification.is_used = True
    verification.save()

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

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

        # SETELAH LENGKAP → PAKSA SETUP MFA
        return redirect("accounts:mfa_setup")

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

        # SETELAH LENGKAP → PAKSA SETUP MFA
        return redirect("accounts:mfa_setup")

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

    # Ambil status TOTP
    try:
        totp_active = request.user.totp_device.is_verified
    except TOTPDevice.DoesNotExist:
        totp_active = False

    return render(request, "accounts/seeker_profile_view.html", {
        "seeker_profile": profile,
        "totp_active": totp_active,
    })


@login_required
def company_profile_view(request):
    if request.user.role != "company":
        return redirect("/")

    profile = get_object_or_404(
        CompanyProfile,
        user=request.user
    )

    # Ambil status TOTP
    try:
        totp_active = request.user.totp_device.is_verified
    except TOTPDevice.DoesNotExist:
        totp_active = False

    return render(request, "accounts/company_profile_view.html", {
        "company_profile": profile,
        "totp_active": totp_active,
    })


# ==================================================
# MFA — SETUP TOTP (Google Authenticator)
# ==================================================
@login_required
def mfa_setup(request):
    device, created = TOTPDevice.objects.get_or_create(user=request.user)

    if request.method == "POST":
        otp_input = request.POST.get("otp", "").strip()
        totp = pyotp.TOTP(device.secret)

        if totp.verify(otp_input, valid_window=1):
            device.is_verified = True
            device.save()
            messages.success(request, "Google Authenticator berhasil diaktifkan!")

            if request.user.role == "seeker":
                return redirect("jobs:job_list")
            return redirect("jobs:employer_home")
        else:
            return render(request, "accounts/mfa_setup.html", {
                "qr_code": _generate_qr_code(request.user, device.secret),
                "secret": device.secret,
                "error": "Kode OTP tidak valid. Pastikan waktu HP kamu sudah sinkron dan coba lagi."
            })

    # GET — generate secret baru kalau belum verified
    if created or not device.is_verified:
        device.secret = pyotp.random_base32()
        device.is_verified = False
        device.save()

    return render(request, "accounts/mfa_setup.html", {
        "qr_code": _generate_qr_code(request.user, device.secret),
        "secret": device.secret,
        "error": None
    })


# ==================================================
# MFA — VERIFY TOTP (saat login)
# ==================================================
def mfa_verify(request):
    user_id = request.session.get("pre_mfa_user_id")
    role = request.session.get("pre_mfa_role")

    if not user_id:
        return redirect("/")

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return redirect("/")

    if request.method == "POST":
        otp_input = request.POST.get("otp", "").strip()

        try:
            device = user.totp_device
            totp = pyotp.TOTP(device.secret)

            if totp.verify(otp_input, valid_window=1):
                # OTP valid → bersihkan session, login
                del request.session["pre_mfa_user_id"]
                del request.session["pre_mfa_role"]
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                return redirect("jobs:job_list")
                return redirect("jobs:employer_home")
            else:
                return render(request, "accounts/mfa_verify.html", {
                    "error": "Kode OTP salah atau sudah kedaluwarsa. Coba lagi."
                })

        except TOTPDevice.DoesNotExist:
            return redirect("/")

    return render(request, "accounts/mfa_verify.html", {"error": None})


# ==================================================
# MFA — DISABLE TOTP
# ==================================================
@login_required
def mfa_disable(request):
    if request.method == "POST":
        otp_input = request.POST.get("otp", "").strip()

        try:
            device = request.user.totp_device
            totp = pyotp.TOTP(device.secret)

            if totp.verify(otp_input, valid_window=1):
                device.delete()
                messages.success(request, "Google Authenticator berhasil dinonaktifkan.")
            else:
                messages.error(request, "Kode OTP salah. Google Authenticator tidak dinonaktifkan.")

        except TOTPDevice.DoesNotExist:
            pass

    if request.user.role == "seeker":
        return redirect("accounts:seeker_profile_view")
    return redirect("accounts:company_profile_view")


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

    # ← CEK EXPIRED
    if reset_obj.is_expired():
        return render(request, "accounts/token_expired.html")

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