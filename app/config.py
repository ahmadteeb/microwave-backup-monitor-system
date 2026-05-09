import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-this-to-a-random-secret-key')
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'production')

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///mw_monitor.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
