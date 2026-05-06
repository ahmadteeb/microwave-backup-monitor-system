import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask Application
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-this-to-a-random-secret-key')
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///mw_monitor.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Jump Server Defaults (Used as fallback/initial seeding)
    JUMP_HOST = os.environ.get('JUMP_HOST')
    JUMP_PORT = int(os.environ.get('JUMP_PORT', 22))
    JUMP_USER = os.environ.get('JUMP_USER')
    JUMP_PASSWORD = os.environ.get('JUMP_PASSWORD')

    # Ping Configuration
    PING_INTERVAL_SECONDS = max(10, int(os.environ.get('PING_INTERVAL_SECONDS', 60)))
    PING_COUNT = int(os.environ.get('PING_COUNT', 3))
    PING_TIMEOUT = int(os.environ.get('PING_TIMEOUT', 2))
