"""Run the app on a throw-away database with demo data, for manual testing and screenshots.

    python scripts/serve_demo.py [port]            # default port 5000

Demo accounts (well-known passwords - local use only, never deploy this):
    admin@hms.test / admin123     warden@hms.test / warden123
    john@student.test / student123 (also jane@, bob@, alice@, carlos@, dana@student.test)
    accountant@hms.test / accountant123
The database lives in a temp file and is deleted when the process exits.
"""
import atexit
import os
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)

from hms_app import create_app          # noqa: E402
from hms_app.config import Config        # noqa: E402
from hms_app.seed import seed_demo_allocations  # noqa: E402

fd, DB_FILE = tempfile.mkstemp(suffix='.db', prefix='hms_demo_')
os.close(fd)
atexit.register(lambda: os.path.exists(DB_FILE) and os.remove(DB_FILE))


class DemoConfig(Config):
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DB_FILE}'
    SEED_DEMO_DATA = True
    SHOW_DEMO_CREDENTIALS = os.environ.get('SHOW_DEMO_CREDENTIALS', '0') == '1'
    SECRET_KEY = 'demo-only-not-a-secret'
    LOGIN_MAX_ATTEMPTS = int(os.environ.get('LOGIN_MAX_ATTEMPTS', '1000'))  # lenient by default; set to 5 to test lockout


if __name__ == '__main__':
    app = create_app(DemoConfig)
    if os.environ.get('DEMO_ALLOCATIONS', '1') == '1':
        with app.app_context():
            seed_demo_allocations()
    app.run(host='127.0.0.1', port=int(sys.argv[1]) if len(sys.argv) > 1 else 5000)
