def test_register(client):
    res = client.post("/api/v1/auth/register", json={
        "email": "new@example.com",
        "username": "newuser",
        "password": "pass1234",
    })
    assert res.status_code == 201
    assert res.json()["email"] == "new@example.com"


def test_register_duplicate_email(client, registered_user):
    res = client.post("/api/v1/auth/register", json={
        "email": registered_user["email"],
        "username": "different",
        "password": "pass1234",
    })
    assert res.status_code == 400


def test_login_success(client, registered_user):
    res = client.post("/api/v1/auth/login", data={
        "username": registered_user["email"],
        "password": registered_user["password"],
    })
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_wrong_password(client, registered_user):
    res = client.post("/api/v1/auth/login", data={
        "username": registered_user["email"],
        "password": "wrongpass",
    })
    assert res.status_code == 401


def test_get_me(client, auth_headers):
    res = client.get("/api/v1/auth/me", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["email"] == "test@example.com"


def test_me_unauthenticated(client):
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
