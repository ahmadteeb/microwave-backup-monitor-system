import os
from datetime import datetime, timedelta
from flask import Flask, session, redirect, jsonify, request, render_template

from app.config import Config
from app.extensions import db, bcrypt, socketio
from app.models import SetupState, AppSettings, User


def create_app(config_class=Config):
    app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    app = Flask(
        __name__,
        static_folder=os.path.join(app_root, 'static'),
        template_folder=os.path.join(app_root, 'templates'),
        instance_path=os.path.join(app_root, 'data', 'instance'),
        static_url_path='/static'
    )
    app.config.from_object(config_class)

    db.init_app(app)
    bcrypt.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')

    global APP_START_TIME
    APP_START_TIME = datetime.utcnow()

    with app.app_context():
        db.create_all()
        
        # Seed SetupState
        if not db.session.get(SetupState, 1):
            setup_state = SetupState(id=1, is_complete=False, completed_at=None)
            db.session.add(setup_state)
            
        # Seed AppSettings
        if not db.session.get(AppSettings, 1):
            settings = AppSettings(id=1)
            db.session.add(settings)
            
        # Seed Roles and Permissions
        from app.models import Role, RolePermission
        from app.permissions import ROLE_DEFAULTS
        
        roles_to_seed = [
            ('admin', 'System Administrator with full access'),
            ('operator', 'Operations user capable of managing links and users'),
            ('viewer', 'Read-only access to monitoring data')
        ]
        
        for role_name, desc in roles_to_seed:
            role = Role.query.filter_by(name=role_name).first()
            if not role:
                role = Role(name=role_name, description=desc, is_system=True)
                db.session.add(role)
                db.session.flush() # ensure role is added before permissions
                
                # Seed default permissions for this role
                defaults = ROLE_DEFAULTS.get(role_name, {})
                for perm_key, is_granted in defaults.items():
                    rp = RolePermission(role_name=role_name, permission_key=perm_key, is_granted=is_granted)
                    db.session.add(rp)
                    
        db.session.commit()

    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.setup import setup_bp
    app.register_blueprint(setup_bp)

    from app.routes.users import users_bp
    app.register_blueprint(users_bp)
    
    from app.routes.roles import roles_bp
    app.register_blueprint(roles_bp)

    from app.routes.notifications import notifications_bp
    app.register_blueprint(notifications_bp)

    from app.routes.logs import logs_bp
    app.register_blueprint(logs_bp)

    from app.routes.settings import settings_bp
    app.register_blueprint(settings_bp)

    from app.routes.profile import profile_bp
    app.register_blueprint(profile_bp)

    from app.routes.links import links_bp
    app.register_blueprint(links_bp)

    from app.routes.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)

    from app.routes.pinglog import pinglog_bp
    app.register_blueprint(pinglog_bp)

    # SocketIO event handlers
    @socketio.on('connect')
    def handle_connect():
        pass

    @socketio.on('disconnect')
    def handle_disconnect():
        pass

    def is_setup_allowed(path):
        allowed_prefixes = (
            '/setup',
            '/api/setup',
            '/static/',
            '/favicon.ico'
        )
        return any(path.startswith(prefix) for prefix in allowed_prefixes)

    def _secrets_file_exists():
        app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        secrets_path = os.path.abspath(os.path.join(app_root, 'data', 'secrets', 'secrets.json'))
        if os.path.exists(secrets_path):
            return True
        legacy_path = os.path.abspath(os.path.join(app_root, 'secrets', 'secrets.json'))
        return os.path.exists(legacy_path)

    @app.before_request
    def global_before_request():
        path = request.path
        setup_state = db.session.get(SetupState, 1)
        
        is_setup_complete = setup_state and setup_state.is_complete
        if not is_setup_complete and _secrets_file_exists():
            is_setup_complete = True

        if not is_setup_complete:
            if not is_setup_allowed(path):
                if path.startswith('/api/'):
                    return jsonify({'error': 'Setup required'}), 403
                return redirect('/setup')
            return
        else:
            if path == '/setup' or path.startswith('/api/setup'):
                if path.startswith('/api/'):
                    return jsonify({'error': 'Setup already completed'}), 403
                return redirect('/login')

            # Allow public access to login and static resources
            public_paths = (
                '/login',
                '/static/',
                '/favicon.ico',
                '/api/auth/login',
                '/socket.io/'
            )
            if any(path.startswith(prefix) for prefix in public_paths):
                return

        user_id = session.get('user_id')
        if not user_id or 'logged_in_at' not in session:
            session.clear()
            if path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            return redirect('/login')

        try:
            logged_in_at = datetime.fromisoformat(session['logged_in_at'])
        except ValueError:
            session.clear()
            if path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            return redirect('/login')

        user = db.session.get(User, user_id)
        if user and user.force_password_change:
            allowed_force_change = ('/api/auth/change-password', '/api/auth/logout', '/api/auth/me')
            if not any(path.startswith(p) for p in allowed_force_change):
                if path.startswith('/api/'):
                    return jsonify({'error': 'Password change required', 'code': 'FORCE_PASSWORD_CHANGE'}), 403

        app_settings = db.session.get(AppSettings, 1)
        timeout_minutes = app_settings.session_timeout_minutes if app_settings else 480
        if datetime.utcnow() - logged_in_at > timedelta(minutes=timeout_minutes):
            session.clear()
            if path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            return redirect('/login')

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/login')
    def login_page():
        return render_template('login.html')

    @app.route('/setup')
    def setup_page():
        return render_template('setup.html')

    return app
