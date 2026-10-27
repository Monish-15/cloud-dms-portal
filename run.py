"""Application entrypoint for local execution and WSGI deployment."""

import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from app import create_app, db

# Load environment variables from .env if present
load_dotenv()

app = create_app(os.environ.get("FLASK_ENV", "development"))

# Ensure database tables exist and initial users are seeded (works for both local & Azure production)
with app.app_context():
    db.create_all()
    try:
        from app.models.user import User
        if not User.query.first():
            from scripts.seed_dev_data import seed_data
            seed_data(app)
            print("Database initialized and demo data seeded.")
    except Exception as e:
        print(f"Database initialization note: {e}")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", False))
