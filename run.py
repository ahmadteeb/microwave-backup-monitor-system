import os
import logging
from app import create_app
from app.extensions import socketio

# Suppress expected APScheduler "skipped: maximum number of running instances" warnings
# These are normal when ping cycles take longer than the interval
logging.getLogger('apscheduler.scheduler').setLevel(logging.ERROR)

app = create_app()

if __name__ == '__main__':
    logging.basicConfig(level=app.config.get('LOG_LEVEL', 'INFO'))

    # In debug mode with reloader, only start the scheduler in the child process
    # (WERKZEUG_RUN_MAIN is set to 'true' in the child).
    # In production (no reloader), always start it.
    is_reloader_parent = os.environ.get('WERKZEUG_RUN_MAIN') != 'true'
    if not is_reloader_parent:
        from app.services.scheduler import init_scheduler
        app.scheduler = init_scheduler(app)

    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)
