import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "app.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{DB_PATH}")

# Inventory API
API_PORT = int(os.getenv("API_PORT", "8000"))

# OpenEnv
OPENENV_PORT = int(os.getenv("OPENENV_PORT", "9000"))
INVENTORY_API_URL = os.getenv("INVENTORY_API_URL", f"http://localhost:{API_PORT}")
