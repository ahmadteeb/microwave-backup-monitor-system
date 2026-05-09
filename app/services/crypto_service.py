import base64
from hashlib import sha256
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from flask import current_app

SALT = b'mw_link_monitor_fernet_salt'
ITERATIONS = 100_000


def _derive_key_pbkdf2(secret_key: str) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=ITERATIONS,
        backend=default_backend()
    )
    return base64.urlsafe_b64encode(kdf.derive(secret_key.encode('utf-8')))


def _derive_key_sha256(secret_key: str) -> bytes:
    return base64.urlsafe_b64encode(sha256(secret_key.encode('utf-8')).digest())


def encrypt(plaintext: str) -> str:
    secret = current_app.config['SECRET_KEY']
    key = _derive_key_pbkdf2(secret)
    f = Fernet(key)
    return f.encrypt(plaintext.encode('utf-8')).decode('utf-8')


def decrypt(ciphertext: str) -> str:
    secret = current_app.config['SECRET_KEY']
    key = _derive_key_pbkdf2(secret)
    f = Fernet(key)
    try:
        return f.decrypt(ciphertext.encode('utf-8')).decode('utf-8')
    except InvalidToken:
        fallback_key = _derive_key_sha256(secret)
        fallback_fernet = Fernet(fallback_key)
        try:
            return fallback_fernet.decrypt(ciphertext.encode('utf-8')).decode('utf-8')
        except InvalidToken:
            raise
