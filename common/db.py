from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class Base(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)


class BaseNoID(db.Model):
    __abstract__ = True
