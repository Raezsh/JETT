from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import uuid
from .utils.crypto import encrypt_value, decrypt_value
from django.utils import timezone
import datetime


# ==========================
# CUSTOM USER MANAGER
# ==========================
class CustomUserManager(BaseUserManager):
    def create_user(self, email, full_name, password=None, **extra_fields):
        if not email:
            raise ValueError("Email wajib diisi")

        email = self.normalize_email(email)
        user = self.model(email=email, full_name=full_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(email, full_name, password, **extra_fields)


# ==========================
# CUSTOM USER
# ==========================
class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ("seeker", "Job Seeker"),
        ("company", "Company"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.email} ({self.role})"


# ==========================
# EMAIL VERIFICATION
# ==========================
class EmailVerification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="verifications")
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)


# ==========================
# JOB SEEKER PROFILE
# ==========================
class SeekerProfile(models.Model):
    EDUCATION_CHOICES = (
        ("SMA", "SMA"),
        ("D3", "D3"),
        ("S1", "S1"),
        ("S2", "S2"),
        ("other", "Lainnya"),
    )

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="seeker_profile"
    )

    _date_of_birth = models.TextField(db_column="date_of_birth", null=True, blank=True)
    _address = models.TextField(db_column="address", null=True, blank=True)
    _phone = models.TextField(db_column="phone", null=True, blank=True)

    education = models.CharField(max_length=20, choices=EDUCATION_CHOICES, blank=True)

    # ========= date_of_birth =========
    @property
    def date_of_birth(self):
        if not self._date_of_birth:
            return None
        try:
            value = decrypt_value(self._date_of_birth)
            return datetime.date.fromisoformat(value)
        except Exception:
            return None

    @date_of_birth.setter
    def date_of_birth(self, value):
        if not value:
            self._date_of_birth = None
            return

        if isinstance(value, str):
            self._date_of_birth = encrypt_value(value)
            return

        if isinstance(value, datetime.date):
            self._date_of_birth = encrypt_value(value.isoformat())
            return

    # ========= address =========
    @property
    def address(self):
        if not self._address:
            return ""
        try:
            return decrypt_value(self._address)
        except Exception:
            return ""

    @address.setter
    def address(self, value):
        self._address = encrypt_value(value) if value else None

    # ========= phone =========
    @property
    def phone(self):
        if not self._phone:
            return ""
        try:
            return decrypt_value(self._phone)
        except Exception:
            return ""

    @phone.setter
    def phone(self, value):
        self._phone = encrypt_value(value) if value else None

    def __str__(self):
        return f"Seeker Profile — {self.user.email}"


# ==========================
# COMPANY PROFILE
# ==========================
class CompanyProfile(models.Model):
    INDUSTRY_CHOICES = (
        ("IT", "IT"),
        ("finance", "Finance"),
        ("manufacturing", "Manufacturing"),
        ("education", "Education"),
        ("services", "Services"),
        ("other", "Lainnya"),
    )

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="company_profile"
    )

    owner_name = models.CharField(max_length=100, blank=True)
    industry = models.CharField(max_length=30, choices=INDUSTRY_CHOICES, blank=True)
    description = models.TextField(blank=True)

    _address = models.TextField(db_column="address", null=True, blank=True)
    _phone = models.TextField(db_column="phone", null=True, blank=True)

    logo = models.ImageField(upload_to="company_logos/", null=True, blank=True)

    @property
    def address(self):
        if not self._address:
            return ""
        try:
            return decrypt_value(self._address)
        except Exception:
            return ""

    @address.setter
    def address(self, value):
        self._address = encrypt_value(value) if value else None

    @property
    def phone(self):
        if not self._phone:
            return ""
        try:
            return decrypt_value(self._phone)
        except Exception:
            return ""

    @phone.setter
    def phone(self, value):
        self._phone = encrypt_value(value) if value else None


# ==========================
# RESET PASSWORD
# ==========================
class PasswordResetToken(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    is_used = models.BooleanField(default=False)
