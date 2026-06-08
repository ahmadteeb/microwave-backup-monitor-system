import logging
from app import create_app
from app.extensions import socketio
from app.services.scheduler import init_scheduler

# Suppress expected APScheduler "skipped: maximum number of running instances" warnings
logging.getLogger('apscheduler.scheduler').setLevel(logging.ERROR)

app = create_app()

# Initialize the scheduler
app.scheduler = init_scheduler(app)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
