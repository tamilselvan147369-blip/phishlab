import sys
import os
import json
import urllib.parse

# Add parent directory to sys.path so the Flask application modules can be resolved
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import app

def handler(environ, start_response):
    """Vercel entrypoint handler with environment inspection and route normalization."""
    path_info = environ.get('PATH_INFO', '')
    
    # Debug endpoint to inspect exact Vercel proxy headers
    if path_info == '/__debug_headers' or environ.get('HTTP_X_DEBUG_HEADERS') == '1':
        start_response('200 OK', [('Content-Type', 'application/json')])
        debug_data = {k: str(v) for k, v in environ.items() if isinstance(v, (str, int, float, bool))}
        return [json.dumps(debug_data, indent=2).encode('utf-8')]

    # Check for original URL in common Vercel/proxy headers
    orig_url = (
        environ.get('HTTP_X_FORWARDED_URI')
        or environ.get('HTTP_X_MATCHED_PATH')
        or environ.get('HTTP_X_ORIGINAL_URI')
        or environ.get('HTTP_X_REWRITE_URL')
    )
    
    qs = environ.get('QUERY_STRING', '')
    if '__vercel_path' in qs:
        params = urllib.parse.parse_qs(qs, keep_blank_values=True)
        if '__vercel_path' in params and params['__vercel_path']:
            target = params['__vercel_path'][0]
            if not target.startswith('/'):
                target = '/' + target
            environ['PATH_INFO'] = target
            clean_params = {k: v for k, v in params.items() if k != '__vercel_path'}
            environ['QUERY_STRING'] = urllib.parse.urlencode(clean_params, doseq=True)
    elif orig_url and orig_url not in ('/api/index', '/api/index.py', '/api'):
        environ['PATH_INFO'] = orig_url.split('?')[0]
    elif path_info in ('/api/index', '/api/index.py', '/api'):
        environ['PATH_INFO'] = '/'

    return app(environ, start_response)

# Expose both app and handler for Vercel WSGI discovery
app_handler = handler



