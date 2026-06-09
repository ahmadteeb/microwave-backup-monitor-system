from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Shared Flask extensions

db = SQLAlchemy()
bcrypt = Bcrypt()
socketio = SocketIO()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per minute"])
