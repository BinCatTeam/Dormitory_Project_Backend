from common.db import db, Base


class BaseProfile(Base):
    __abstract__ = True
    __table_args__ = {'schema': 'profile'}


class Account(BaseProfile):
    uid = db.Column(db.String(32))
    building_id = db.Column(db.Integer)
    bupt_id = db.Column(db.Integer)
    bupt_password = db.Column(db.String(32))
