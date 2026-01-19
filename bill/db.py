from enum import StrEnum


from common.db import db, Base


class BaseBill(Base):
    __abstract__ = True
    __table_args__ = {'schema': 'bill'}


class Bill(BaseBill):
    trade_time = db.Column(db.DateTime(timezone=True))
    title = db.Column(db.Text)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(precision=10, scale=2))
    party_id = db.Column(db.Integer)
    counterparty_id = db.Column(db.Integer)
    deleted = db.Column(db.Boolean, default=False)


class BillAmount(BaseBill):
    bill_id = db.Column(db.Integer)
    uid = db.Column(db.String(32))
    price = db.Column(db.Numeric(precision=10, scale=2))
    diff = db.Column(db.Numeric(precision=10, scale=2))
    completed = db.Column(db.Boolean)


class ApportionMethod(StrEnum):
    ratio = "ratio"
    price = "price"
    share = "share"


class Apportion(BaseBill):
    bill_id = db.Column(db.Integer)
    method = db.Column(db.Enum(ApportionMethod))


class ApportionDetail(BaseBill):
    apportion_id = db.Column(db.Integer)
    uid = db.Column(db.String(32))
    value = db.Column(db.Numeric(precision=10, scale=2))


class ApportionPreset(BaseBill):
    name = db.Column(db.Text)
    oid = db.Column(db.String(32))
    method = db.Column(db.Enum(ApportionMethod))


class ApportionPresetDetail(BaseBill):
    apportion_preset_id = db.Column(db.Integer)
    uid = db.Column(db.String(32))
    value = db.Column(db.Numeric(precision=10, scale=2))


class Party(BaseBill):
    pass


class PartyUser(BaseBill):
    party_id = db.Column(db.Integer)
    uid = db.Column(db.String(32))
