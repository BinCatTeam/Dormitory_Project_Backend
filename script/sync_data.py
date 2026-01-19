from sqlalchemy import text, create_engine, MetaData
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

mig_db_user = config['database']['migrate']['username']
mig_db_pass = config['database']['migrate']['password']
mig_db_host = config['database']['migrate']['address']
mig_db_name = config['database']['migrate']['database']
mig_db_url = f"postgresql://{mig_db_user}:{mig_db_pass}@{mig_db_host}/{mig_db_name}"


# app configuration
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
db.init_app(app)


with app.app_context():
    mig_engine = create_engine(
        mig_db_url,
        execution_options={"postgresql_readonly": True}
    )
    mig_metadata = MetaData()
    schemas = set(table.schema for table in db.metadata.sorted_tables)
    for schema in schemas:
        mig_metadata.reflect(bind=mig_engine, schema=schema)

    for table in db.metadata.sorted_tables:
        table_label = f"{table.schema}.{table.name}"
        print(f"Sync {table_label}")
        db.session.execute(table.delete())
        with mig_engine.connect() as conn:
            if table_label in mig_metadata.tables:
                mig_table = mig_metadata.tables[table_label]
                rows = conn.execute(mig_table.select()).fetchall()
                if rows:
                    column_names = [c.name for c in table.columns]
                    filtered_rows = [
                        {k: v for k, v in dict(r._mapping).items() if k in column_names}
                        for r in rows
                    ]
                    db.session.execute(table.insert(), filtered_rows)
                else:
                    print(f"Table {table_label} has no rows in migrate db")
            else:
                print(f"Table {table_label} not found in migrate db, skipping")
        
        # Sync sequence if table has id column
        if 'id' in [c.name for c in table.columns]:
            max_id_result = db.session.execute(
                text(f"SELECT COALESCE(MAX(id), 0) FROM {table.schema}.{table.name}")
            ).fetchone()
            max_id = int(max_id_result[0]) if max_id_result is not None and max_id_result[0] is not None else 0
            sequence_name = f"{table.schema}.{table.name}_id_seq"
            db.session.execute(text(f"ALTER SEQUENCE {sequence_name} RESTART WITH {max_id + 1}"))
            print(f"Updated sequence {sequence_name} to {max_id + 1}")
    
    db.session.commit()