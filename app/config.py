import json
import os


def _load_config_values():
    default_secret = os.environ.get('SECRET_KEY', 'change-this-to-a-random-secret-key')
    db_uri = os.environ.get('DATABASE_URL')

    secrets_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'secrets', 'secrets.json'))
    if os.path.exists(secrets_path):
        try:
            with open(secrets_path, 'r', encoding='utf-8') as f:
                secrets_data = json.load(f)
            
            secret_key = secrets_data.get('secret_key', default_secret)
            encrypted_data = secrets_data.get('db_config_encrypted', '')
            
            if encrypted_data:
                from app.services.crypto_service import decrypt_with_key
                decrypted_json = decrypt_with_key(encrypted_data, secret_key)
                config = json.loads(decrypted_json)
                uri = config.get('database_url')
                if uri:
                    db_uri = uri
            
            return db_uri or 'sqlite:///:memory:', secret_key
        except Exception:
            pass
            
    # Legacy fallback
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'db_config.json'))
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            uri = config.get('database_url')
            if uri:
                return uri, default_secret
        except Exception:
            pass

    return db_uri or 'sqlite:///:memory:', default_secret


class Config:
    _db_uri, _secret = _load_config_values()

    SECRET_KEY = _secret
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'production')

    SQLALCHEMY_DATABASE_URI = _db_uri
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_SAMESITE = 'Strict'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # set True when deployed behind HTTPS
