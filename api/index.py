import sys
import os

# Add parent directory to sys.path so the Flask application modules can be resolved
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import app

class VercelPathMiddleware:
    """WSGI middleware to normalize PATH_INFO from Vercel rewrite headers."""
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '')
        # Vercel provides the original browser path in x-forwarded-uri or x-matched-path
        forwarded_uri = environ.get('HTTP_X_FORWARDED_URI') or environ.get('HTTP_X_MATCHED_PATH')

        if path_info in ('/api/index.py', '/api/index', '/api'):
            if forwarded_uri:
                environ['PATH_INFO'] = forwarded_uri.split('?')[0]
            else:
                environ['PATH_INFO'] = '/'
        elif path_info.startswith('/api/index.py/'):
            environ['PATH_INFO'] = path_info[len('/api/index.py'):]
        elif path_info.startswith('/api/index/'):
            environ['PATH_INFO'] = path_info[len('/api/index'):]

        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathMiddleware(app.wsgi_app)

