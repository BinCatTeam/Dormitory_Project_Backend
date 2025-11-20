from functools import wraps
from flask import g, request


import requests
import jwt


from common.constants import ISSUER, JWKSURI, AUDIENCE


def get_auth_token():
  auth = request.headers.get("Authorization", None)
  if not auth:
    return None

  contents = auth.split()

  if len(contents) < 2 or contents[0] != 'Bearer':
    return None

  return contents[1]


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_auth_token()
        jwks = jwt.PyJWKClient(JWKSURI).get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            jwks.key,
            algorithms=[jwt.get_unverified_header(token).get('alg')],
            audience=AUDIENCE,
            issuer=ISSUER,
            leeway=30,
            options={
                'verify_at_hash': False
            }
        )
        g.current_user = payload
        return f(*args, **kwargs)
    return decorated


def get_m2m_access_token(clientid, clientsecret):
    token_endpoint = f"https://auth.dormitory.lingzc.com/oidc/token"
    
    response = requests.post(
        token_endpoint,
        data={
            'grant_type': 'client_credentials',
            'client_id': clientid,
            'client_secret': clientsecret,
            'resource': "https://default.logto.app/api",
            'scope': 'all'
        },
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    
    if response.status_code == 200:
        return response.json().get('access_token')
    else:
        raise Exception(f"Failed to get M2M token: {response.status_code}, {response.text}")
