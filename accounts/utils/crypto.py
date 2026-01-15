from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
import base64
import hashlib

def _get_fernet():
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))

fernet = _get_fernet()


def encrypt_value(value):
    if value in (None, "", b""):
        return None
    return fernet.encrypt(str(value).encode()).decode()


def decrypt_value(value):
    if value in (None, "", b""):
        return None
    try:
        return fernet.decrypt(value.encode()).decode()
    except InvalidToken:
        # DATA LAMA / RUSAK / BUKAN ENKRIPSI
        return None
