# Latested verified effective at 10/27/2025

from buptmw import BUPT_Auth
from tomllib import load
from flask import Flask
from time import sleep
from random import random


import os


from elec.db import db, ElecBuilding


# runtime configuration
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
with open("./config.toml", "rb") as file:
    config = load(file)


# app configuration
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{config['database']['username']}:{config['database']['password']}@{config['database']['address']}/{config['database']['database']}"
db.init_app(app)


with app.app_context():
    account = {  # please fill it correctly
        "username": 1234121234,
        "password": 'pswd'
    }
    bupt = BUPT_Auth(config["bupt"]["account"])

    # elec
    elec = bupt.get_Electric()
    area = config["bupt"]["elec"]["area"]

    part = []
    for i in area:
        print(f"Getting part {i['name']}")
        rp = elec.post(
            "https://app.bupt.edu.cn/buptdf/wap/default/part",
            data={
                "areaid": i["id"]
            }
        )
        if rp.json()["e"] != 0:
            print(rp.json()["m"])
            continue
        for j in rp.json()["d"]["data"]:
            part.append({
                "area": i,
                "part": j
            })
        sleep(0.5 + random())
    
    floor = []
    for i in part:
        # apartment "学十一一楼" can't return valid info, skip
        if i["part"]["partmentId"] == "85a2e185790440e7978354838afb4f03":
            continue

        print(f"Getting apartment {i['part']['partmentName']}, in {i['area']['name']}")
        rp = elec.post(
            "https://app.bupt.edu.cn/buptdf/wap/default/floor",
            data={
                "areaid": i["area"]["id"],
                "partmentId": i["part"]["partmentId"]
            }
        )
        if rp.json()["e"] != 0:
            print(rp.json()["m"])
            continue
        for j in rp.json()["d"]["data"]:
            floor.append(i|{"floor": j})
        sleep(0.5 + random())

    drom = []
    for i in floor:
        print(f"Getting floor {i['floor']['floorName']}, in {i['part']['partmentName']}, {i['area']['name']}")
        rp = elec.post(
            "https://app.bupt.edu.cn/buptdf/wap/default/drom",
            data={
                "areaid": i["area"]["id"],
                "partmentId": i["part"]["partmentId"],
                "floorId": i["floor"]["floorId"]
            }
        )
        if rp.json()["e"] != 0:
            print(rp.json()["m"])
            continue
        for j in rp.json()["d"]["data"]:
            drom.append(i|{"drom": j})
        sleep(0.5 + random())
    
    print("Adding dormitory info into database.")
    for i in drom:
        line = ElecBuilding(
            area_id=i["area"]["id"],
            area_name=i["area"]["name"],
            apartment_id=i["part"]["partmentId"],
            apartment_name=i['part']['partmentName'],
            floor_id=i["floor"]["floorId"],
            floor_name=i['floor']['floorName'],
            dormitory_id=i['drom']['dromNum'],
            dormitory_name=i['drom']['dromName'],
        )
        db.session.add(line)
    db.session.commit()
    print("Adding completed.")
