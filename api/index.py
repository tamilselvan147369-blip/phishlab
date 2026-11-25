import sys
import os
import urllib.parse

# Add parent directory to sys.path so the Flask application modules can be resolved
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import app

class VercelPathMiddleware:
    """WSGI middleware to normalize PATH_INFO from Vercel rewrite parameter or headers."""
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        qs = environ.get('QUERY_STRING', '')
        if '__vercel_path' in qs:
            params = urllib.parse.parse_qs(qs, keep_blank_values=True)
            if '__vercel_path' in params and params['__vercel_path']:
                target_path = params['__vercel_path'][0]
                if not target_path.startswith('/'):
                    target_path = '/' + target_path
                environ['PATH_INFO'] = target_path
                clean_params = {k: v for k, v in params.items() if k != '__vercel_path'}
                environ['QUERY_STRING'] = urllib.parse.urlencode(clean_params, doseq=True)
        else:
            path_info = environ.get('PATH_INFO', '')
            if path_info in ('/api/index.py', '/api/index', '/api'):
                environ['PATH_INFO'] = '/'

        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathMiddleware(app.wsgi_app)


