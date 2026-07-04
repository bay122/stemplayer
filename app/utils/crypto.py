import os
import stat
from cryptography.fernet import Fernet

from app.utils.paths import get_config_dir


def _get_key_path():
    return os.path.join(get_config_dir(), ".stemsplayer.key")


def _get_or_create_key() -> bytes:
    key_path = _get_key_path()
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            return f.read()
    key = Fernet.generate_key()
    with open(key_path, "wb") as f:
        f.write(key)
    os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)
    return key


_FERNET_PREFIX = "gAAAAA"


def _looks_like_fernet_token(value: str) -> bool:
    return value.startswith(_FERNET_PREFIX)


def encrypt_value(plaintext: str) -> str:
    if not plaintext:
        return ""
    if _looks_like_fernet_token(plaintext):
        return plaintext
    key = _get_or_create_key()
    f = Fernet(key)
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    if not _looks_like_fernet_token(ciphertext):
        return ciphertext
    try:
        key = _get_or_create_key()
        f = Fernet(key)
        return f.decrypt(ciphertext.encode()).decode()
    except Exception:
        return ""
