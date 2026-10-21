from pathlib import Path

import pytest

from database import db

REQUIRED_MESSAGE = "Please enter your email and password."
INVALID_MESSAGE = "Invalid email or password."
SIGNED_OUT_MESSAGE = "You have been signed out."


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    # Import after patching DB_PATH so the app's startup init/seed
    # runs against the temp DB, never the real one.
    from app import app as flask_app

    flask_app.config.update(TESTING=True)
    return flask_app.test_client()


def make_user(name="Alice", email="alice@example.com", password="password123"):
    return db.create_user(name, email, password)


def post_login(client, email="alice@example.com", password="password123",
               **kwargs):
    return client.post(
        "/login", data={"email": email, "password": password}, **kwargs
    )


def session_user_id(client):
    with client.session_transaction() as sess:
        return sess.get("user_id")


# ------------------------------------------------------------------ #
# Signing in                                                          #
# ------------------------------------------------------------------ #

def test_get_login_renders_form(client):
    resp = client.get("/login")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert 'action="/login"' in html
    assert 'name="email"' in html
    assert 'name="password"' in html
    assert "Get started" in html
    assert "Sign out" not in html


def test_demo_user_can_sign_in(client):
    # The app's startup seed only runs once per test process, so seed here.
    db.seed_db()
    resp = post_login(client, email="demo@spendly.com", password="demo123")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")
    with client.session_transaction() as sess:
        assert sess["user_name"] == "Demo User"


def test_short_password_user_can_sign_in(client):
    make_user(password="abc")
    resp = post_login(client, password="abc")
    assert resp.status_code == 302


def test_session_holds_only_id_and_name(client):
    user_id = make_user()
    post_login(client)
    with client.session_transaction() as sess:
        assert set(sess.keys()) == {"user_id", "user_name"}
        assert sess["user_id"] == user_id
        assert sess["user_name"] == "Alice"


def test_login_clears_stale_session(client):
    make_user()
    with client.session_transaction() as sess:
        sess["stale"] = 1
    post_login(client)
    with client.session_transaction() as sess:
        assert "stale" not in sess
        assert "user_id" in sess


@pytest.mark.parametrize("email", [
    "  Alice@Example.COM ",
    "ALICE@EXAMPLE.COM",
])
def test_email_is_normalised(client, email):
    make_user()
    resp = post_login(client, email=email)
    assert resp.status_code == 302


def test_registered_user_can_sign_in(client):
    client.post("/register", data={
        "name": "Alice", "email": "alice@example.com",
        "password": "password123",
    })
    assert session_user_id(client) is None

    resp = post_login(client)
    assert resp.status_code == 302
    with client.session_transaction() as sess:
        assert sess["user_name"] == "Alice"


# ------------------------------------------------------------------ #
# Navbar                                                              #
# ------------------------------------------------------------------ #

def test_navbar_when_signed_in(client):
    make_user()
    resp = post_login(client, follow_redirects=True)
    html = resp.get_data(as_text=True)
    assert resp.request.path == "/"
    assert "Alice" in html
    assert "Sign out" in html
    assert 'href="/logout"' in html
    assert "Get started" not in html


def test_navbar_name_is_escaped(client):
    make_user(name="<b>x</b>")
    html = post_login(client, follow_redirects=True).get_data(as_text=True)
    assert "&lt;b&gt;x&lt;/b&gt;" in html
    assert "<b>x</b>" not in html


def test_base_html_has_no_hardcoded_urls():
    base = Path(__file__).resolve().parent.parent / "templates" / "base.html"
    assert 'href="/' not in base.read_text()


# ------------------------------------------------------------------ #
# Errors                                                              #
# ------------------------------------------------------------------ #

def test_wrong_password(client):
    make_user()
    resp = post_login(client, password="wrong-pass-123")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 401
    assert INVALID_MESSAGE in html
    assert 'value="alice@example.com"' in html
    assert "wrong-pass-123" not in html
    assert session_user_id(client) is None


def test_unknown_email_same_message(client):
    make_user()
    resp = post_login(client, email="nobody@example.com")
    assert resp.status_code == 401
    assert INVALID_MESSAGE in resp.get_data(as_text=True)
    assert session_user_id(client) is None


def test_password_is_not_trimmed(client):
    make_user()
    resp = post_login(client, password=" password123 ")
    assert resp.status_code == 401

    make_user(email="spaced@example.com", password=" spaced pw ")
    resp = post_login(client, email="spaced@example.com", password=" spaced pw ")
    assert resp.status_code == 302


@pytest.mark.parametrize("data", [
    {},
    {"email": "alice@example.com"},
    {"password": "password123"},
    {"email": "   ", "password": "password123"},
    {"email": "alice@example.com", "password": ""},
    {"email": "alice@example.com", "password": "   "},
])
def test_required_fields(client, data):
    make_user()
    resp = client.post("/login", data=data)
    assert resp.status_code == 400
    assert REQUIRED_MESSAGE in resp.get_data(as_text=True)
    assert session_user_id(client) is None


def test_error_repopulates_normalised_escaped_email(client):
    resp = post_login(client, email="Bob@Example.com", password="whatever1")
    assert 'value="bob@example.com"' in resp.get_data(as_text=True)

    resp = post_login(client, email='"><x>@a.com', password="whatever1")
    html = resp.get_data(as_text=True)
    assert "<x>" not in html
    assert "&lt;x&gt;" in html


# ------------------------------------------------------------------ #
# Redirects and logout                                                #
# ------------------------------------------------------------------ #

def test_get_login_while_signed_in_redirects(client):
    make_user()
    post_login(client)
    resp = client.get("/login")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")


def test_logout_clears_session_and_flashes(client):
    make_user()
    post_login(client)

    resp = client.get("/logout")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")
    assert session_user_id(client) is None

    html = client.get("/login").get_data(as_text=True)
    assert SIGNED_OUT_MESSAGE in html
    assert 'class="auth-success"' in html
    assert "Get started" in html
    assert "Sign out" not in html


def test_logout_when_signed_out(client):
    resp = client.get("/logout", follow_redirects=True)
    assert resp.status_code == 200
    assert resp.request.path == "/login"
    assert SIGNED_OUT_MESSAGE in resp.get_data(as_text=True)


def test_signed_out_message_shown_once(client):
    client.get("/logout", follow_redirects=True)
    again = client.get("/login").get_data(as_text=True)
    assert SIGNED_OUT_MESSAGE not in again
