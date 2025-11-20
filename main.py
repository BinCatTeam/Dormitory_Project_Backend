from flask import Flask
from tomllib import load


import os


from common.db import db
from elec.route import elec


# runtime configuration
os.chdir(os.path.dirname(__file__))
with open("./config.toml", "rb") as file:
    config = load(file)


# Init app
app = Flask(__name__)
app.config["bupt"] = config["bupt"]["account"]
app.register_blueprint(elec)

# db
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{config['database']['username']}:{config['database']['password']}@{config['database']['address']}/{config['database']['database']}"
db.init_app(app)

# used for debug
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
