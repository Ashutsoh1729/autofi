import base64
import os
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from util.config import get_config_dir

_KEY_FILE = "fernet.key"
_SALT_FILE = "fernet.salt"


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _get_key_path() -> Path:
    return get_config_dir() / _KEY_FILE


def _get_salt_path() -> Path:
    return get_config_dir() / _SALT_FILE


def _get_or_create_fernet() -> Fernet:
    key_path = _get_key_path()
    salt_path = _get_salt_path()

    if key_path.exists() and salt_path.exists():
        key = key_path.read_bytes()
        return Fernet(key)

    _ensure_dir(key_path)

    salt = os.urandom(16)
    salt_path.write_bytes(salt)

    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
    key = base64.urlsafe_b64encode(kdf.derive(os.urandom(32)))
    key_path.write_bytes(key)

    return Fernet(key)


def encrypt_value(plaintext: str) -> str:
    fernet = _get_or_create_fernet()
    token = fernet.encrypt(plaintext.encode())
    return token.decode()


def decrypt_value(token: str) -> str:
    fernet = _get_or_create_fernet()
    plaintext = fernet.decrypt(token.encode())
    return plaintext.decode()
