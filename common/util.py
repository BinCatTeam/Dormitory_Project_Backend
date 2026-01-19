from flask import g, current_app


import requests


def get_user_by_username(username):
    resp = requests.get(current_app.config.get("LOGTO")["endpoint"]["user"],
        headers={
            "Authorization": f"Bearer {g.logto_access_token}",
        },
        params={
            "search.username": username,
            "page": 1,
            "page_size": 10
        }
    )
    resp.raise_for_status()
    return resp.json()


def get_user_by_id(uid):
    resp = requests.get(f'{current_app.config.get("LOGTO")["endpoint"]["user"]}/{uid}',
        headers={
            "Authorization": f"Bearer {g.logto_access_token}",
        },
    )
    if resp.status_code == 404:
        return None
    
    resp.raise_for_status()
    return resp.json()


def get_organizations_by_uid(uid):
    resp = requests.get(f'{current_app.config.get("LOGTO")["endpoint"]["user"]}/{uid}/organizations',
        headers={
            "Authorization": f"Bearer {g.logto_access_token}",
        },
    )
    if resp.status_code == 404:
        return None
    
    resp.raise_for_status()
    return resp.json()


def get_organizations_member_by_id(oid):
    resp = requests.get(f'{current_app.config.get("LOGTO")["endpoint"]["organization"]}/{oid}/users',
        headers={
            "Authorization": f"Bearer {g.logto_access_token}",
        },
    )
    if resp.status_code == 404:
        return None
    
    resp.raise_for_status()
    return resp.json()
