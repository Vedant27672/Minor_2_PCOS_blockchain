from flask import Flask
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from config import Config

from datetime import datetime
from flask import Flask

app = Flask(__name__, static_folder="static")
app.config.from_object(Config)

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M:%S'):
    """Convert a Unix timestamp to a formatted date string."""
    try:
        return datetime.fromtimestamp(value).strftime(format)
    except Exception:
        return value

# Initialize extensions
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# MongoDB setup
mongo = MongoClient(app.config['MONGO_URI'])
db = mongo.file_storage
users = db.users

model_mappings = db.model_mappings

public_files = db.public_files

from app import views
