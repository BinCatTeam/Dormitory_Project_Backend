from flask import Blueprint, g, make_response, request, jsonify, abort
from requests.exceptions import RequestException
from buptmw import BUPT_Auth


from common.auth import require_auth
from profile.db import db, Account


profile = Blueprint('profile', __name__, url_prefix="/profile")


@profile.route("/info/bind", methods=['GET'])
@require_auth
def info_bind():
    uid = g.current_user["sub"]
    user = Account.query.filter(Account.uid == uid).one()
    if user is None or user.bupt_id is None:
        return make_response('', 204)
    else:
        buptid = user.bupt_id
        passwd = True if user.bupt_password is not None else False
    return jsonify(buptid, passwd)


@profile.route("/create", methods=['POST'])
@require_auth
def create():
    uid = g.current_user["sub"]

    account = Account.query.filter_by(uid=uid).one()
    if account:
        abort(409)

    account = Account(uid=uid)
    db.session.add(account)

    try:
        db.session.commit()
        return '', 201
    except Exception as e:
        print(e)
        db.session.rollback()
        abort(500)


@profile.route("/bind", methods=['POST'])
@require_auth
def bind():
    data = request.get_json()
    uid = g.current_user["sub"]
    buptid = data["username"]
    password = data["password"]
    is_save = data["save_credentials"]

    user = Account.query.filter(
        Account.uid == uid,
        Account.bupt_id == buptid
    ).one_or_none()
    if user:
        return abort(403)
    
    try:
        BUPT_Auth(data)
    except RequestException:
        return abort(401)

    user = Account.query.filter(Account.uid == uid).one_or_none()
    if user is None:
        user = Account(uid=uid)
    user.bupt_id = buptid
    if is_save:
        user.bupt_password = password
    db.session.add(user)
    db.session.commit()

    return make_response("SUCCESS")


@profile.route("/password", methods=['DELETE'])
@require_auth
def del_pswd():
    uid = g.current_user["sub"]
    user = Account.query.filter(Account.uid == uid).one()
    if user is None or user.bupt_password is None:
        abort(400)
    
    user.bupt_password = None
    db.session.add(user)
    db.session.commit()
    
    return make_response("SUCCESS")


@profile.route("/password", methods=['PUT'])
@require_auth
def append_pswd():
    password = request.data.decode()
    uid = g.current_user["sub"]
    user = Account.query.filter(Account.uid == uid).one()
    if len(password) == 0 or user is None or user.bupt_id is None:
        abort(400)

    buptid = user.bupt_id
    try:
        BUPT_Auth({"username": buptid, "password": password})
    except RequestException:
        return abort(401)
    
    user.bupt_password = password
    db.session.add(user)
    db.session.commit()
    
    return make_response("SUCCESS")
