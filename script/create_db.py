from sqlalchemy import text
from tomllib import load
from flask import Flask


import os


from common.db import db
from elec.db import *
from profile.db import *
from bill.db import *


# runtime configuration
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
with open("./config.toml", "rb") as file:
    config = load(file)
db_user = config['database']['username']
db_pass = config['database']['password']
db_host = config['database']['address']
db_name = config['database']['database']
db_url = f"postgresql://{db_user}:{db_pass}@{db_host}/{db_name}"


# app configuration
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
db.init_app(app)


with app.app_context():
    # create schema
    schemas = set()
    for table in db.metadata.tables.values():
        if table.schema:
            schemas.add(table.schema)
    with db.engine.connect() as conn:
        for schema in schemas:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        conn.commit()

    # create table
    db.create_all()
