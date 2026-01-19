from functools import wraps
from flask import g, request, current_app, abort


import requests
import time
import jwt


def get_auth_token():
  auth = request.headers.get("Authorization", None)
  if not auth:
    return None

  contents = auth.split()

  if len(contents) < 2 or contents[0] != 'Bearer':
    return None

  return contents[1]


def get_m2m_token():
    config = current_app.config.get('LOGTO')
    token_endpoint = current_app.config.get("LOGTO")["endpoint"]["token"]
    resource = config["api"]["management"]
    client_id = config["app"]["appId"]
    client_secret = config["app"]["appSecret"]

    if not all([token_endpoint, resource, client_id, client_secret]):
        raise RuntimeError("Missing Logto M2M configuration in app.config")
    
    resp = requests.post(token_endpoint, data={
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'resource': resource,
        'scope': 'all'
    }, timeout=10)
    
    if resp.status_code != 200:
        current_app.logger.error(f"Failed to get Logto token: {resp.text}")
        abort(500, description="Failed to authenticate with Logto")

    data = resp.json()
    access_token = data['access_token']
    expires_in = data.get('expires_in', 3600)
    return {
       'access_token': access_token,
       'expires_at': time.time() + expires_in - 60
    }


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_auth_token()
        jwks = jwt.PyJWKClient(current_app.config.get("LOGTO")["endpoint"]["jwksuri"]).get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            jwks.key,
            algorithms=[jwt.get_unverified_header(token).get('alg')],
            audience=current_app.config.get("LOGTO")["api"]["dormitory"],
            issuer=current_app.config.get("LOGTO")["endpoint"]["issuer"],
            leeway=30,
            options={
                'verify_at_hash': False
            }
        )
        g.current_user = payload
        return f(*args, **kwargs)
    return decorated


def with_logto_token(f):
    cache = {
        'access_token': None,
        'expires_at': 0
    }

    @wraps(f)
    def decorated(*args, **kwargs):
        now = time.time()
        if cache['access_token'] is None or cache['expires_at'] <= now:
            cache.update(get_m2m_token())
        
        g.logto_access_token = cache['access_token']
        return f(*args, **kwargs)
    return decorated
