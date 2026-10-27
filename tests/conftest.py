"""Pytest test configuration and fixtures."""

import os
import shutil
import tempfile
import pytest
from app import create_app
from app.extensions import db as _db
from app.models.user import User, UserRole
from app.storage import init_storage


@pytest.fixture(scope="session")
def temp_upload_dir():
    """Create a temporary upload directory for tests."""
    temp_dir = tempfile.mkdtemp(prefix="test_portal_uploads_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def app(temp_upload_dir):
    """Application configured for testing."""
    os.environ["LOCAL_UPLOAD_FOLDER"] = temp_upload_dir
    os.environ["STORAGE_BACKEND"] = "local"
    app = create_app("testing")
    app.config["LOCAL_UPLOAD_FOLDER"] = temp_upload_dir

    with app.app_context():
        _db.create_all()
        init_storage(app)
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Flask CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def db(app):
    """Database session fixture."""
    return _db


@pytest.fixture
def admin_user(app, db):
    """Fixture providing an active Admin user."""
    user = User(
        username="admin_test",
        email="admin_test@portal.local",
        role=UserRole.ADMIN,
        is_active_account=True,
    )
    user.set_password("AdminPass123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def editor_user(app, db):
    """Fixture providing an active Editor user."""
    user = User(
        username="editor_test",
        email="editor_test@portal.local",
        role=UserRole.EDITOR,
        is_active_account=True,
    )
    user.set_password("EditorPass123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def viewer_user(app, db):
    """Fixture providing an active Viewer user."""
    user = User(
        username="viewer_test",
        email="viewer_test@portal.local",
        role=UserRole.VIEWER,
        is_active_account=True,
    )
    user.set_password("ViewerPass123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def inactive_user(app, db):
    """Fixture providing a deactivated user."""
    user = User(
        username="inactive_test",
        email="inactive_test@portal.local",
        role=UserRole.VIEWER,
        is_active_account=False,
    )
    user.set_password("InactivePass123!")
    db.session.add(user)
    db.session.commit()
    return user
