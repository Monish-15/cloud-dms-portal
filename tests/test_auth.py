"""Authentication and session management test suite."""



def test_valid_login_succeeds(client, admin_user):
    """Test successful authentication with valid credentials."""
    response = client.post(
        "/login",
        data={"username": "admin_test", "password": "AdminPass123!"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Welcome back, admin_test" in response.data
    assert b"Operational Dashboard" in response.data


def test_invalid_password_fails(client, admin_user):
    """Test that incorrect password fails authentication."""
    response = client.post(
        "/login",
        data={"username": "admin_test", "password": "WrongPassword!"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


def test_nonexistent_user_fails(client):
    """Test that non-existent username fails gracefully without leaking existence."""
    response = client.post(
        "/login",
        data={"username": "ghost_user", "password": "AnyPassword123!"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


def test_deactivated_user_cannot_login(client, inactive_user):
    """Test that deactivated accounts are prevented from logging in."""
    response = client.post(
        "/login",
        data={"username": "inactive_test", "password": "InactivePass123!"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"deactivated" in response.data


def test_brute_force_lockout(client, app, admin_user):
    """Test account lockout triggers after 5 consecutive failed attempts."""
    for i in range(5):
        client.post(
            "/login",
            data={"username": "admin_test", "password": "BadPassword!"},
        )

    # 6th attempt should return lockout message
    response = client.post(
        "/login",
        data={"username": "admin_test", "password": "AdminPass123!"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Account is temporarily locked" in response.data or b"Too many failed login attempts" in response.data


def test_unauthenticated_protected_route_redirects(client):
    """Test that accessing protected endpoint unauthenticated redirects to login."""
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_logout_terminates_session(client, admin_user):
    """Test that logout terminates user session."""
    client.post(
        "/login",
        data={"username": "admin_test", "password": "AdminPass123!"},
    )
    logout_resp = client.get("/logout", follow_redirects=True)
    assert logout_resp.status_code == 200
    assert b"securely logged out" in logout_resp.data

    # Protected dashboard should now redirect
    dash_resp = client.get("/dashboard", follow_redirects=False)
    assert dash_resp.status_code == 302
