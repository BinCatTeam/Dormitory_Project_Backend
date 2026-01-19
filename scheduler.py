from apscheduler.schedulers.background import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from requests.exceptions import RequestException
from buptmw.constants import ELEC
from datetime import datetime
from buptmw import BUPT_Auth
from requests import Timeout
from functools import wraps
from tomllib import load
from flask import Flask
from time import sleep
from datetime import timezone, timedelta


import random
import logging
import sys
import os


from common.db import db
from profile.db import Account
from elec.db import ElecBuilding, ElecStat


# runtime configuration
os.chdir(os.path.dirname(__file__))
with open("./config.toml", "rb") as file:
    config = load(file)

class ISO8601Formatter(logging.Formatter):
    def __init__(self, fmt="%(asctime)s %(levelname)s %(message)s"):
        super().__init__(fmt)
        self.tz = timezone(timedelta(hours=8))

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=self.tz)
        ms = dt.microsecond // 1000 * 1000
        dt_ms = dt.replace(microsecond=ms)
        return dt_ms.isoformat()

logger = logging.getLogger("Scheduler")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(ISO8601Formatter())
logger.addHandler(handler)

# Init app
app = Flask(__name__)

# db
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{config['database']['username']}:{config['database']['password']}@{config['database']['address']}/{config['database']['database']}"
db.init_app(app)


def app_context(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with app.app_context():
            return func(*args, **kwargs)
    return wrapper


@app_context
def fetch_and_store_elec_stats():
    logger.info("Fetch building elec stats.")

    account = Account.query.filter(
        Account.building_id != None,
        Account.bupt_id != None,
        Account.bupt_password != None
    ).all()
    building_ids = list(set(i.building_id for i in account))
    auth = {}
    for item in account:
        info = {
            "username": item.bupt_id,
            "password": item.bupt_password
        }
        if item.building_id not in auth:
            auth[item.building_id] = [info]
        else:
            auth[item.building_id].append(info)

    
    if not building_ids:
        logger.warning("There's no building pending to fetch.")
        return

    total_delay = 30.0
    interval = total_delay / len(building_ids)
    
    for i, bid in enumerate(building_ids):
        try:
            building: ElecBuilding | None = db.session.get(ElecBuilding, bid)
            if not building:
                logger.error(f"Invalid building id: {bid}")
                continue
            
            data = {
                'partmentId': building.apartment_id,
                'floorId': building.floor_id,
                'dromNumber': building.dormitory_id,
                'areaid': building.area_id
            }
            
            timeout = 90
            auth[bid] = random.sample(auth[bid], len(auth[bid]))
            session = None
            for auth_info in auth[bid]:
                try:
                    session = BUPT_Auth(auth_info).get_Electric()
                    break
                except RequestException:
                    continue

            if session is None:
                logger.error(f"All accounts failed for building: {building.id},"
                    f"{building.area_name}-{building.apartment_name}-{building.floor_name}-{building.dormitory_name}")
                continue
            try:
                resp = session.post(ELEC.SEARCH, data=data, timeout=timeout)
            except Timeout as e:
                logger.error(
                    f"Request timeout={timeout} for building: {building.id},"
                    f"{building.area_name}-{building.apartment_name}-{building.floor_name}-{building.dormitory_name}"
                )
                continue
            resp.raise_for_status()
            d_data = resp.json().get("d", {}).get("data", {})
            
            surplus = d_data.get("surplus")
            free_surplus = d_data.get("freeEnd")
            time_str = d_data.get("time")
            if not all([surplus, time_str]):
                logger.warning(f"empty surplus of time in response for building {bid}")
                continue
            
            surplus = float(surplus) + float(free_surplus)
            search_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            stat = ElecStat(
                building_id=str(bid),
                search_time=search_time,
                surplus=surplus
            )
            db.session.add(stat)
            db.session.commit()
            logger.info(f"Fetch stats for building {bid} successfully: surplus {surplus:.2f} @ {search_time}")
            
        except Exception as e:
            logger.error(f"Error when fetch building {bid}: {e}")
            db.session.rollback()
            continue

        if i < len(building_ids):
            sleep(max(0, interval + random.uniform(-0.5, 0.5)))
    logger.info(f"Successfully fetch {len(building_ids)} buildings.")


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    trigger = CronTrigger(minute="*/5")
    scheduler.add_job(fetch_and_store_elec_stats, trigger=trigger)
    logger.info("Start scheduler")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Receive Ctrl-C")
        scheduler.shutdown()
