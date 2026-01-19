from common.db import db, Base


class BaseElec(Base):
    __abstract__ = True
    __table_args__ = {'schema': 'elec'}


class ElecBuilding(BaseElec):
    area_id = db.Column(db.String(32))
    area_name = db.Column(db.String(32))
    apartment_id = db.Column(db.String(32))
    apartment_name = db.Column(db.String(32))
    floor_id = db.Column(db.String(32))
    floor_name = db.Column(db.String(32))
    dormitory_id = db.Column(db.String(32))
    dormitory_name = db.Column(db.String(32))


class ElecStat(BaseElec):
    building_id = db.Column(db.Integer)
    search_time = db.Column(db.DateTime)
    surplus = db.Column(db.Numeric(precision=10, scale=2))
