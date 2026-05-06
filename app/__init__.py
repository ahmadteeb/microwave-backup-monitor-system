import os
from flask import Flask, send_from_directory
from app.config import Config
from app.models import db

def create_app(config_class=Config):
    app = Flask(__name__, static_folder='../frontend', static_url_path='/frontend')
    app.config.from_object(config_class)

    db.init_app(app)

    with app.app_context():
        db.create_all()

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

    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    # Serve static assets from frontend folder
    @app.route('/css/<path:path>')
    def send_css(path):
        return send_from_directory(os.path.join(app.static_folder, 'css'), path)

    @app.route('/js/<path:path>')
    def send_js(path):
        return send_from_directory(os.path.join(app.static_folder, 'js'), path)

    return app
