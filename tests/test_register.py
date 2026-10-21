import pytest
from werkzeug.security import check_password_hash

from database import db

SUCCESS_MESSAGE = "Account created — please sign in."
DUPLICATE_MESSAGE = "An account with that email already exists."
REQUIRED_MESSAGE = "All fields are required."
EMAIL_MESSAGE = "Please enter a valid email address."
LENGTH_MESSAGE = "Password must be at least 8 characters."


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    # Import after patching DB_PATH so the app's startup init/seed
    # runs against the temp DB, never the real one.
    from app import app as flask_app

    flask_app.config.update(TESTING=True)
    return flask_app.test_client()


def post_register(client, name="Alice", email="alice@example.com",
                  password="password123", **kwargs):
    return client.post(
        "/register",
        data={"name": name, "email": email, "password": password},
        **kwargs,
    )


def count_users(email):
    conn = db.get_db()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM users WHERE email = ?", (email,)
        ).fetchone()[0]
    finally:
        conn.close()


def test_get_register_renders_form(client):
    resp = client.get("/register")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert 'action="/register"' in html
    assert 'minlength="8"' in html
    for field in ('name="name"', 'name="email"', 'name="password"'):
        assert field in html


def test_successful_registration_creates_user_and_redirects(client):
    resp = post_register(client)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")

    user = db.get_user_by_email("alice@example.com")
    assert user is not None
    assert user["name"] == "Alice"
    assert user["password_hash"] != "password123"
    assert check_password_hash(user["password_hash"], "password123")


def test_name_and_email_are_normalised(client):
    post_register(client, name="  Alice  ", email="  Alice@Example.COM ")
    user = db.get_user_by_email("alice@example.com")
    assert user is not None
    assert user["name"] == "Alice"
    assert user["email"] == "alice@example.com"


def test_success_flash_shown_on_login_once(client):
    resp = post_register(client, follow_redirects=True)
    html = resp.get_data(as_text=True)
    assert resp.request.path == "/login"
    assert SUCCESS_MESSAGE in html
    assert 'class="auth-success"' in html

    again = client.get("/login").get_data(as_text=True)
    assert SUCCESS_MESSAGE not in again


def test_password_length_boundary(client):
    ok = post_register(client, email="eight@example.com", password="12345678")
    assert ok.status_code == 302
    assert count_users("eight@example.com") == 1

    bad = post_register(client, email="seven@example.com", password="1234567")
    assert bad.status_code == 400
    assert LENGTH_MESSAGE in bad.get_data(as_text=True)
    assert count_users("seven@example.com") == 0


def test_duplicate_email_case_insensitive(client):
    post_register(client)
    resp = post_register(client, email="ALICE@Example.com")
    assert resp.status_code == 400
    assert DUPLICATE_MESSAGE in resp.get_data(as_text=True)
    assert count_users("alice@example.com") == 1


def test_duplicate_race_returns_400_not_500(client, monkeypatch):
    post_register(client)
    # Simulate a second signup slipping past the pre-check.
    monkeypatch.setattr("app.get_user_by_email", lambda email: None)
    resp = post_register(client)
    assert resp.status_code == 400
    assert DUPLICATE_MESSAGE in resp.get_data(as_text=True)
    assert count_users("alice@example.com") == 1


@pytest.mark.parametrize("data", [
    {"name": "", "email": "a@example.com", "password": "password123"},
    {"name": "Alice", "email": "", "password": "password123"},
    {"name": "Alice", "email": "a@example.com", "password": ""},
    {"name": "   ", "email": "a@example.com", "password": "password123"},
    {"name": "Alice", "email": "   ", "password": "password123"},
    {"name": "Alice", "email": "a@example.com", "password": "        "},
    {"email": "a@example.com", "password": "password123"},
    {},
])
def test_required_fields(client, data):
    resp = client.post("/register", data=data)
    assert resp.status_code == 400
    assert REQUIRED_MESSAGE in resp.get_data(as_text=True)
    assert count_users("a@example.com") == 0


@pytest.mark.parametrize("email", [
    "noatsign",
    "@example.com",
    "user@",
    "user@localhost",
    "a b@c.com",
])
def test_invalid_email(client, email):
    resp = post_register(client, email=email)
    assert resp.status_code == 400
    assert EMAIL_MESSAGE in resp.get_data(as_text=True)


def test_validation_order(client):
    resp = post_register(client, name="", password="short")
    assert REQUIRED_MESSAGE in resp.get_data(as_text=True)

    resp = post_register(client, email="bad", password="short")
    html = resp.get_data(as_text=True)
    assert EMAIL_MESSAGE in html
    assert LENGTH_MESSAGE not in html


def test_form_repopulated_without_password(client):
    resp = post_register(client, password="secret7")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 400
    assert 'value="Alice"' in html
    assert 'value="alice@example.com"' in html
    assert "secret7" not in html


def test_repopulated_name_is_escaped(client):
    resp = post_register(client, name="<b>x</b>", password="short")
    html = resp.get_data(as_text=True)
    assert "&lt;b&gt;x&lt;/b&gt;" in html
    assert "<b>x</b>" not in html


def test_registration_does_not_log_user_in(client):
    post_register(client)
    with client.session_transaction() as sess:
        assert "user_id" not in sess
