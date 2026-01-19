from flask import Blueprint, g, make_response, request, jsonify, abort
from datetime import datetime


from common.auth import require_auth
from profile.db import Account
from elec.db import db, ElecBuilding, ElecStat


elec = Blueprint('elec', __name__, url_prefix="/elec")


@elec.route("/info/bind", methods=['GET'])
@require_auth
def info_bind():
    uid = g.current_user["sub"]
    user = Account.query.filter(Account.uid == uid).one()
    if user is None or user.building_id is None:
        return make_response('', 204)
    else:
        result = user.building_id
    return make_response(str(result))


@elec.route("/info/building", methods=['GET'])
@require_auth
def info_building():
    building_id = request.args.get("building_id")
    building = ElecBuilding.query.filter(ElecBuilding.id == building_id).with_entities(
        ElecBuilding.area_name,
        ElecBuilding.apartment_name,
        ElecBuilding.floor_name,
        ElecBuilding.dormitory_name
    ).one()
    if building_id is None:
        abort(400)

    result = {k: v for k, v in zip(["area_name", "apartment_name", "floor_name", "dormitory_name"], building)}
    return make_response(result)


@elec.route("/info/data", methods=['GET'])
@require_auth
def get_data():
    uid = g.current_user["sub"]
    user = Account.query.filter(
        Account.uid == uid
    ).one()
    if user is None or user.bupt_id is None or user.bupt_password is None:
        return abort(403)
    
    building_id = Account.query.filter(
        Account.uid == uid
    ).one().building_id
    start_time = request.args.get('start')
    end_time = request.args.get('end')

    start_dt = datetime.fromisoformat(start_time)
    end_dt = datetime.fromisoformat(end_time)

    data = ElecStat.query.filter(
        ElecStat.building_id == building_id,
        ElecStat.search_time.between(start_dt, end_dt)
    ).with_entities(
        ElecStat.search_time,
        ElecStat.surplus
    ).order_by(ElecStat.search_time).all()

    return jsonify([(item[0].isoformat(), float(item[1])) for item in data])


@elec.route("/select", methods=['POST'])
@require_auth
def select_building():
    data = request.get_json()
    valid = lambda key: key not in data or not isinstance(data[key], str) or len(data[key]) == 0
    
    if valid('area_id'):
        areas = ElecBuilding.query.with_entities(
            ElecBuilding.area_id,
            ElecBuilding.area_name
        ).distinct().all()
        return jsonify({
            "type": "area",
            "data": [{
                'area_id': i.area_id,
                'area_name': i.area_name
            } for i in areas]
        })
    
    if valid('apartment_id'):
        apartment = ElecBuilding.query.with_entities(
            ElecBuilding.apartment_id,
            ElecBuilding.apartment_name
        ).filter(
            ElecBuilding.area_id == data["area_id"]
        ).distinct().all()
        return jsonify({
            "type": "apartment",
            "data": [{
                'apartment_id': i.apartment_id,
                'apartment_name': i.apartment_name
            } for i in apartment]
        })
    
    if valid('floor_id'):
        floor = ElecBuilding.query.with_entities(
            ElecBuilding.floor_id,
            ElecBuilding.floor_name
        ).filter(
            ElecBuilding.area_id == data["area_id"],
            ElecBuilding.apartment_id == data["apartment_id"]
        ).distinct().all()
        return jsonify({
            "type": "floor",
            "data": [{
                'floor_id': i.floor_id,
                'floor_name': i.floor_name
            } for i in floor]
        })
    
    if valid('dormitory_id'):
        dormitory = ElecBuilding.query.with_entities(
            ElecBuilding.dormitory_id,
            ElecBuilding.dormitory_name
        ).filter(
            ElecBuilding.area_id == data["area_id"],
            ElecBuilding.apartment_id == data["apartment_id"],
            ElecBuilding.floor_id == data["floor_id"]
        ).distinct().all()
        return jsonify({
            "type": "dormitory",
            "data": [{
                'dormitory_id': i.dormitory_id,
                'dormitory_name': i.dormitory_name
            } for i in dormitory]
        })

    return abort(404)


@elec.route("/bind", methods=['POST'])
@require_auth
def bind():
    data = request.get_json()
    uid = g.current_user["sub"]

    building_id = ElecBuilding.query.with_entities(
        ElecBuilding.id
    ).filter(
        ElecBuilding.area_id == data["area_id"],
        ElecBuilding.apartment_id == data["apartment_id"],
        ElecBuilding.floor_id == data["floor_id"],
        ElecBuilding.dormitory_id == data["dormitory_id"]
    ).one()
    if building_id is None:
        abort(400)
    building_id = building_id[0]

    user = Account.query.filter(
        Account.uid == uid,
        Account.building_id == building_id
    ).one_or_none()
    if user is not None:
        return abort(403)

    user = Account.query.filter(Account.uid == uid).one_or_none()
    if user is None:
        user = Account(uid=uid)
    user.building_id=building_id
    db.session.add(user)
    db.session.commit()

    return make_response("SUCCESS")
