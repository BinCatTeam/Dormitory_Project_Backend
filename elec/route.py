from flask import Blueprint, g, make_response, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from buptmw import BUPT_Auth
from buptmw.constants import ELEC
from requests import Timeout
from datetime import datetime
from time import sleep


import random


from common.auth import require_auth
from .db import db, ElecUser, ElecBuilding, ElecStat


elec = Blueprint('elec', __name__, url_prefix="/elec")

@elec.route("/info/bind", methods=['GET'])
@require_auth
def info_bind():
    uid = g.current_user["sub"]
    user = ElecUser.query.filter(ElecUser.uid == uid).first()
    result = user.building_id if user is not None else ""
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
    ).first()
    result = {k: v for k, v in zip(["area_name", "apartment_name", "floor_name", "dormitory_name"], building)}
    return make_response(result)


@elec.route("/info/data", methods=['GET'])
@require_auth
def get_data():
    building_id = ElecUser.query.with_entities(
        ElecUser.building_id
    ).filter(
        ElecUser.uid == g.current_user["sub"]
    ).first()[0]
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

    return make_response(404)


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
    ).first()[0]

    user = ElecUser.query.filter_by(uid=uid).first()
    if user:
        user.building_id = building_id
    else:
        user = ElecUser(uid=uid, building_id=building_id)
        db.session.add(user)
    db.session.commit()

    return make_response(str(building_id))


@elec.record
def init(state):
    app = state.app
    def fetch_and_store_elec_stats():
        with app.app_context():
            session = BUPT_Auth(app.config["bupt"]).get_Elec()
            building_ids = ElecUser.query.with_entities(ElecUser.building_id).distinct().all()
            building_ids = [bid[0] for bid in building_ids if bid[0] is not None]
            print(f"fetch elec for buildings: {''.join(building_ids)}")
            
            if not building_ids:
                return

            total_delay = 30.0
            interval = total_delay / len(building_ids)
            
            for i, bid in enumerate(building_ids):
                try:
                    building = ElecBuilding.query.get(bid)
                    if not building:
                        continue
                    
                    data = {
                        'partmentId': building.apartment_id,
                        'floorId': building.floor_id,
                        'dromNumber': building.dormitory_id,
                        'areaid': building.area_id
                    }
                    
                    try:
                        resp = session.post(ELEC.SEARCH, data=data, timeout=90)
                    except Timeout as e:
                        print(
                            f"Request timeout=60 for building: {building.id},"
                            f"{building.area_name}-{building.apartment_name}-{building.floor_name}-{building.dormitory_name}"
                        )
                        continue
                    resp.raise_for_status()
                    d_data = resp.json().get("d", {}).get("data", {})
                    
                    surplus = d_data.get("surplus")
                    time_str = d_data.get("time")
                    if surplus is None or not time_str:
                        continue
                    
                    search_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    stat = ElecStat(
                        building_id=str(bid),
                        search_time=search_time,
                        surplus=surplus
                    )
                    db.session.add(stat)
                    db.session.commit()
                    
                except Exception as e:
                    print(e)
                    db.session.rollback()
                    continue

                if i < len(building_ids):
                    delay = interval + random.uniform(-0.5, 0.5)
                    sleep(max(0, delay))

    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_and_store_elec_stats, 'cron', minute="*/5")
    scheduler.start()
