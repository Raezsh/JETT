from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .validators import StrongPasswordValidator

CustomUser = get_user_model()


# =======================================
# REGISTER SEEKER FORM
# =======================================
class RegisterSeekerForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Password"}),
        label="Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Konfirmasi Password"}),
        label="Konfirmasi Password"
    )

    class Meta:
        model = CustomUser
        fields = ["full_name", "email"]

        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "Nama lengkap"}),
            "email": forms.EmailInput(attrs={"placeholder": "Email"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")

        # ← FIX: hanya anggap "sudah digunakan" kalau user-nya aktif (sudah verifikasi)
        existing_user = CustomUser.objects.filter(email=email).first()

        if existing_user:
            if existing_user.is_active:
                raise forms.ValidationError("Email sudah digunakan.")
            else:
                # User lama belum verifikasi → hapus biar bisa register ulang
                existing_user.delete()

        return email

    def clean(self):
        cleaned_data = super().clean()
        pwd = cleaned_data.get("password")
        cpwd = cleaned_data.get("confirm_password")

        # Validasi password kuat
        validator = StrongPasswordValidator()
        try:
            validator.validate(pwd)
        except ValidationError as e:
            raise forms.ValidationError(e.messages)

        # Cek password dan konfirmasi
        if pwd and cpwd and pwd != cpwd:
            raise forms.ValidationError("Password dan konfirmasi tidak cocok.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


# =======================================
# REGISTER COMPANY FORM
# =======================================
class RegisterCompanyForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Password"}),
        label="Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Konfirmasi Password"}),
        label="Konfirmasi Password"
    )

    class Meta:
        model = CustomUser
        fields = ["full_name", "email"]

        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "Nama perusahaan / PIC"}),
            "email": forms.EmailInput(attrs={"placeholder": "Email perusahaan"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")

        # ← FIX: hanya anggap "sudah digunakan" kalau user-nya aktif (sudah verifikasi)
        existing_user = CustomUser.objects.filter(email=email).first()

        if existing_user:
            if existing_user.is_active:
                raise forms.ValidationError("Email sudah digunakan.")
            else:
                # User lama belum verifikasi → hapus biar bisa register ulang
                existing_user.delete()

        return email

    def clean(self):
        cleaned_data = super().clean()
        pwd = cleaned_data.get("password")
        cpwd = cleaned_data.get("confirm_password")

        # Validasi password kuat
        validator = StrongPasswordValidator()
        try:
            validator.validate(pwd)
        except ValidationError as e:
            raise forms.ValidationError(e.messages)

        # Cek password dan konfirmasi
        if pwd and cpwd and pwd != cpwd:
            raise forms.ValidationError("Password dan konfirmasi tidak cocok.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


# =======================================
# LOGIN FORM
# =======================================
class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "Email"}),
        label="Email"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Password"}),
        label="Password"
    )