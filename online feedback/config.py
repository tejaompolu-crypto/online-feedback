import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")
ADMIN_SECRET_KEY = os.environ.get("ADMIN_SECRET_KEY", "admin123")
DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "feedback.db"))
DEBUG = True
