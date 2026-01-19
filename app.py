from flask import Flask
from tomllib import load


import os


from common.db import db
from common.route import common
from profile.route import profile
from elec.route import elec
from bill.route import bill


# runtime configuration
os.chdir(os.path.dirname(__file__))
with open("./config.toml", "rb") as file:
    config = load(file)


# Init app
app = Flask(__name__)
app.register_blueprint(common)
app.register_blueprint(elec)
app.register_blueprint(profile)
app.register_blueprint(bill)

# db
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{config['database']['username']}:{config['database']['password']}@{config['database']['address']}/{config['database']['database']}"
db.init_app(app)

# logto
app.config['LOGTO'] = config['logto']

# used for debug
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001)
