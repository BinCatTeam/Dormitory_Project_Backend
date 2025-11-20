from common.db import db, Base


class ElecUser(Base):
    uid = db.Column(db.String(32))
    building_id = db.Column(db.Integer)


class ElecBuilding(Base):
    area_id = db.Column(db.String(32))
    area_name = db.Column(db.String(32))
    apartment_id = db.Column(db.String(32))
    apartment_name = db.Column(db.String(32))
    floor_id = db.Column(db.String(32))
    floor_name = db.Column(db.String(32))
    dormitory_id = db.Column(db.String(32))
    dormitory_name = db.Column(db.String(32))


class ElecStat(Base):
    building_id = db.Column(db.Integer)
    search_time = db.Column(db.DateTime)
    surplus = db.Column(db.Numeric(precision=10, scale=2))
