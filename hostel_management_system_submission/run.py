import os
from hms_app import create_app

if __name__ == '__main__':
    # Debug mode (interactive debugger) is opt-in only: set FLASK_DEBUG=1 locally.
    create_app().run(host='127.0.0.1', debug=os.environ.get('FLASK_DEBUG') == '1')
