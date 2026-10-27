"""Application factory module."""

import os
import click
from flask import Flask
from app.config import config_by_name
from app.extensions import db, login_manager, csrf
from app.models.user import User, UserRole
from app.storage import init_storage


def create_app(config_name=None):
    """Factory creating and configuring the Flask application instance."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development").lower()

    app = Flask(__name__)
    config_obj = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_obj)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Initialize storage backend
    init_storage(app)

    # User loader callback for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.documents import documents_bp
    from app.routes.admin import admin_bp
    from app.routes.profile import profile_bp
    from app.routes.errors import errors_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(documents_bp, url_prefix="/documents")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(profile_bp)
    app.register_blueprint(errors_bp)

    # Security headers middleware
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if app.config.get("ENV") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # CLI commands
    @app.cli.command("init-db")
    def init_db_command():
        """Initialize database tables."""
        db.create_all()
        click.echo("Database tables initialized successfully.")

    @app.cli.command("seed-admin")
    @click.option("--username", prompt=True, default=lambda: app.config.get("INITIAL_ADMIN_USERNAME", "admin"))
    @click.option("--email", prompt=True, default=lambda: app.config.get("INITIAL_ADMIN_EMAIL", "admin@portal.local"))
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def seed_admin_command(username, email, password):
        """Seed initial administrator account securely."""
        existing = User.query.filter_by(username=username).first()
        if existing:
            click.echo(f"User '{username}' already exists.")
            return

        user = User(
            username=username,
            email=email,
            role=UserRole.ADMIN,
            is_active_account=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Initial administrator '{username}' created successfully.")

    @app.cli.command("seed-demo")
    def seed_demo_command():
        """Seed demo users and synthetic records for development testing."""
        from scripts.seed_dev_data import seed_data
        seed_data(app)
        click.echo("Demo data seeded successfully.")

    return app
