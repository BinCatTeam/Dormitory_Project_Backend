from flask import Blueprint, request, make_response, g, abort


from common.auth import require_auth, with_logto_token
from common.util import (
    get_user_by_username,
    get_organizations_by_uid,
    get_organizations_member_by_id
)


common = Blueprint('common', __name__, url_prefix="/common")


@common.route("/search/user", methods=['GET'])
@require_auth
@with_logto_token
def query_username():
    username = request.args.get("username")
    users = get_user_by_username(f"{username}%")

    if len(users) == 0:
        return make_response('', 204)
    
    return make_response([{
        "id": user["id"],
        "username": user["username"]
    } for user in users])


@common.route("/my/organization", methods=['GET'])
@require_auth
@with_logto_token
def query_organization():
    uid = g.current_user["sub"]
    orgs = get_organizations_by_uid(uid)
    if orgs is None:
        return make_response('', 204)
    
    return make_response([{
        "id": org["id"],
        "name": org["name"]
    } for org in orgs])


@common.route("/organization/user", methods=['GET'])
@require_auth
@with_logto_token
def query_organization_users():
    uid = g.current_user["sub"]
    oid = request.args.get("organization_id")
    org_member = get_organizations_member_by_id(oid)
    if org_member is None or uid not in [u["id"] for u in org_member]:
        abort(403)
    
    return make_response([{
        "id": user["id"],
        "username": user["username"]
    } for user in org_member])
