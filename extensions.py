# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Maak de objecten hier aan, maar koppel ze nog niet aan de app
db = SQLAlchemy()
migrate = Migrate()