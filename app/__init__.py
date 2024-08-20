from flask import Flask
 
class ReverseProxied(object):
  def __init__(self, app):
      self.app = app
  def __call__(self, environ, start_response):
      script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
      if script_name:
          environ['SCRIPT_NAME'] = script_name
          path_info = environ['PATH_INFO']
          if path_info.startswith(script_name):
              environ['PATH_INFO'] = path_info[len(script_name):]
      # Setting wsgi.url_scheme from Headers set by proxy before app
      scheme = environ.get('HTTP_X_SCHEME', 'https')
      if scheme:
        environ['wsgi.url_scheme'] = scheme
      # Setting HTTP_HOST from Headers set by proxy before app
      remote_host = environ.get('HTTP_X_FORWARDED_HOST', '')
      remote_port = environ.get('HTTP_X_FORWARDED_PORT', '')
      if remote_host and remote_port:
          environ['HTTP_HOST'] = f'{remote_host}:{remote_port}'
      return self.app(environ, start_response)
 
app = Flask(__name__)
 
from app import views
app.wsgi_app = ReverseProxied(app.wsgi_app)