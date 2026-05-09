import os
from datetime import datetime, timedelta
from flask import Flask, send_from_directory, session, redirect, jsonify, request
from app.config import Config
from app.extensions import db, bcrypt
from app.models import SetupState, AppSettings


def create_app(config_class=Config):
    app = Flask(__name__, static_folder='../frontend', static_url_path='/frontend')
    app.config.from_object(config_class)

    db.init_app(app)
    bcrypt.init_app(app)

    with app.app_context():
        db.create_all()
        if not SetupState.query.get(1):
            setup_state = SetupState(id=1, is_complete=False, completed_at=None)
            db.session.add(setup_state)
            db.session.commit()

        if not AppSettings.query.get(1):
            settings = AppSettings(id=1)
            db.session.add(settings)
            db.session.commit()

    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.setup import setup_bp
    app.register_blueprint(setup_bp)

    from app.routes.users import users_bp
    app.register_blueprint(users_bp)

    from app.routes.notifications import notifications_bp
    app.register_blueprint(notifications_bp)

    from app.routes.logs import logs_bp
    app.register_blueprint(logs_bp)

    from app.routes.settings import settings_bp
    app.register_blueprint(settings_bp)

    from app.routes.profile import profile_bp
    app.register_blueprint(profile_bp)

    from app.routes.jumpserver import jumpserver_bp
    app.register_blueprint(jumpserver_bp)

    from app.routes.links import links_bp
    app.register_blueprint(links_bp)

    from app.routes.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)

    from app.routes.pinglog import pinglog_bp
    app.register_blueprint(pinglog_bp)

    from app.services.scheduler import init_scheduler
    app.scheduler = init_scheduler(app)

    def is_setup_allowed(path):
        allowed_prefixes = (
            '/setup',
            '/api/setup',
            '/login',
            '/api/auth',
            '/css/',
            '/js/',
            '/frontend/',
            '/favicon.ico'
        )
        return any(path.startswith(prefix) for prefix in allowed_prefixes)

    @app.before_request
    def global_before_request():
        path = request.path
        setup_state = SetupState.query.get(1)
        if not setup_state or not setup_state.is_complete:
            if not is_setup_allowed(path):
                return redirect('/setup')
            return
        else:
            if path == '/setup':
                return redirect('/login')

        user_id = session.get('user_id')
        if user_id and 'logged_in_at' in session:
            try:
                logged_in_at = datetime.fromisoformat(session['logged_in_at'])
            except ValueError:
                session.clear()
                if path.startswith('/api/'):
                    return jsonify({'error': 'Authentication required'}), 401
                return redirect('/login')

            app_settings = AppSettings.query.get(1)
            timeout_minutes = app_settings.session_timeout_minutes if app_settings else 480
            if datetime.utcnow() - logged_in_at > timedelta(minutes=timeout_minutes):
                session.clear()
                if path.startswith('/api/'):
                    return jsonify({'error': 'Authentication required'}), 401
                return redirect('/login')

    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    @app.route('/login')
    def login_page():
        return app.send_static_file('login.html')

    @app.route('/setup')
    def setup_page():
        return app.send_static_file('setup.html')

    @app.route('/change-password')
    def change_password_page():
        return app.send_static_file('change_password.html')

    @app.route('/css/<path:path>')
    def send_css(path):
        return send_from_directory(os.path.join(app.static_folder, 'css'), path)

    @app.route('/js/<path:path>')
    def send_js(path):
        return send_from_directory(os.path.join(app.static_folder, 'js'), path)

    return app
